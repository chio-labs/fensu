use std::fs;
use std::path::Path;
use std::process::{Command, Output};

pub(crate) fn run(root: &Path, arguments: &[&str]) -> Output {
    Command::new(env!("CARGO_BIN_EXE_fensu"))
        .arg("map")
        .args(arguments)
        .current_dir(root)
        .env("FENSU_PYTHON", root.join("missing-python"))
        .env("NO_COLOR", "1")
        .output()
        .expect("native map process")
}

pub(crate) fn run_colored(root: &Path, arguments: &[&str]) -> Output {
    Command::new(env!("CARGO_BIN_EXE_fensu"))
        .arg("map")
        .args(arguments)
        .current_dir(root)
        .env("FENSU_PYTHON", root.join("missing-python"))
        .env_remove("NO_COLOR")
        .output()
        .expect("native colored map process")
}

pub(crate) fn write(path: impl AsRef<Path>, contents: &str) {
    write_bytes(path, contents.as_bytes());
}

pub(crate) fn write_bytes(path: impl AsRef<Path>, contents: &[u8]) {
    let path = path.as_ref();
    fs::create_dir_all(path.parent().expect("fixture parent")).expect("fixture directory");
    fs::write(path, contents).expect("fixture file");
}

pub(crate) fn basic_project(root: &Path) {
    write(root.join("fensu.toml"), "roots = [\"src/pkg\"]\n");
    write(
        root.join("src/pkg/entry.py"),
        "from pkg.steps import step\n\ndef run(callback=None) -> None:\n    step()\n    callback()\n",
    );
    write(
        root.join("src/pkg/steps.py"),
        "from pkg.finish import finish\n\ndef step() -> None:\n    finish()\n",
    );
    write(
        root.join("src/pkg/finish.py"),
        "from pkg.entry import run\n\ndef finish() -> None:\n    run()\n",
    );
    write(
        root.join("src/pkg/other.py"),
        "def run() -> None:\n    return None\n",
    );
}

pub(crate) fn method_project(root: &Path) {
    write(root.join("fensu.toml"), "roots = [\"src/methods\"]\n");
    write(
        root.join("src/methods/contracts.py"),
        "from typing import Protocol\n\nclass Runner(Protocol):\n    def execute(self) -> None:\n        ...\n",
    );
    write(
        root.join("src/methods/workers.py"),
        "from methods.contracts import Runner\n\nclass Base:\n    def run(self) -> None:\n        self.hook()\n\nclass Worker(Base, Runner):\n    def execute(self) -> None:\n        self.run()\n\n    def hook(self) -> None:\n        return None\n\ndef make() -> Worker:\n    return Worker()\n",
    );
    write(
        root.join("src/methods/entry.py"),
        "from methods.contracts import Runner\nfrom methods.workers import Worker, make\n\ndef run(runner: Runner, dynamic) -> None:\n    worker = Worker()\n    worker.execute()\n    make().execute()\n    runner.execute()\n    dynamic.execute()\n\ndef run_protocol(runner: Runner) -> None:\n    runner.execute()\n",
    );
}

pub(crate) fn sibling_method_project(root: &Path) {
    write(root.join("fensu.toml"), "roots = [\"src/siblings\"]\n");
    write(
        root.join("src/siblings/workers.py"),
        "class Base:\n    def run(self) -> None:\n        self.hook()\n\nclass ChildA(Base):\n    def hook(self) -> None:\n        return None\n\nclass ChildB(Base):\n    def hook(self) -> None:\n        return None\n",
    );
    write(
        root.join("src/siblings/entry.py"),
        "from siblings.workers import ChildA, ChildB\n\ndef call_a() -> None:\n    ChildA().run()\n\ndef call_b() -> None:\n    ChildB().run()\n",
    );
}

pub(crate) fn ambiguous_protocol_project(root: &Path) {
    write(root.join("fensu.toml"), "roots = [\"src/protocols\"]\n");
    write(
        root.join("src/protocols/contracts.py"),
        "from typing import Protocol\n\nclass Runner(Protocol):\n    def execute(self) -> None:\n        ...\n",
    );
    write(
        root.join("src/protocols/workers.py"),
        "from protocols.contracts import Runner\n\nclass First(Runner):\n    def execute(self) -> None:\n        return None\n\nclass Second(Runner):\n    def execute(self) -> None:\n        return None\n",
    );
    write(
        root.join("src/protocols/entry.py"),
        "from protocols.contracts import Runner\n\ndef run(runner: Runner) -> None:\n    runner.execute()\n",
    );
}

pub(crate) fn text(output: &[u8]) -> String {
    String::from_utf8(output.to_vec()).expect("UTF-8 process output")
}
