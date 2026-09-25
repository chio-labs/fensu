use fensu_facts::dead_code::models::Module;
use fensu_facts::extension::models::ProgramHandle;
use ruff_python_ast::PythonVersion;

pub(crate) fn module(name: &str, source: &str) -> Module {
    Module {
        name: name.to_owned(),
        program: ProgramHandle::parse_many(vec![source.to_owned()], PythonVersion::PY312)
            .pop()
            .expect("one fixture source was supplied")
            .expect("fixture source is valid Python"),
        package: !name.contains('.'),
        initializer: !name.contains('.'),
    }
}

pub(crate) fn package(name: &str, source: &str) -> Module {
    Module {
        initializer: true,
        ..module(name, source)
    }
}
