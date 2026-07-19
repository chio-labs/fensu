use std::collections::BTreeSet;
use std::env;
use std::fs;
use std::io::{self, IsTerminal};
use std::path::{Path, PathBuf};
use std::process::Command;

use walkdir::WalkDir;

use crate::helpers::process;
use crate::models::{CliOutput, InitOptions};

const FENSU_IGNORE: &str = "# Fensu\n.fensu/cache/\n";

pub(crate) fn run_init(arguments: &[String]) -> Result<CliOutput, String> {
    let options = parse_init(arguments)?;
    if options.help {
        return Ok(CliOutput::success("usage: fensu init [-h] [--yes] [--root ROOTS [ROOTS ...]] [--tests TESTS [TESTS ...]] [--tooling TOOLING [TOOLING ...]] [--skills | --no-skills] [--name NAME]\n\noptions:\n  -h, --help\n".to_owned()));
    }
    let repository = env::current_dir().map_err(|error| error.to_string())?;
    if let Some(path) = local_config(&repository) {
        return Ok(CliOutput::success(format!(
            "Fensu configuration already exists: {} (nothing to do)\n",
            path.display()
        )));
    }
    let python_files = repository_python_files(&repository);
    let package_roots = detected_roots(&repository);
    let empty = package_roots.is_empty() && python_files.is_empty();
    if !options.yes && !io::stdin().is_terminal() {
        return Err(
            "Interactive initialization requires a TTY; use --yes or explicit options.".to_owned(),
        );
    }
    if empty
        && (!options.roots.is_empty() || !options.tests.is_empty() || !options.tooling.is_empty())
    {
        return Err("--root, --tests, and --tooling options do not apply to an empty repository; use --name NAME.".to_owned());
    }
    if empty && options.yes && options.name.is_none() {
        return Err("Empty repository initialization with --yes requires --name NAME.\nExample: fensu init --yes --name my_package".to_owned());
    }
    if !options.yes {
        return Err(
            "Interactive initialization requires the Python fallback; rerun with --yes.".to_owned(),
        );
    }
    let (roots, tests, tooling, project_name) = if empty {
        let name =
            normalize_name(options.name.as_deref().ok_or_else(|| {
                "Empty repository initialization requires --name NAME.".to_owned()
            })?)?;
        let root = format!("src/{name}");
        fs::create_dir_all(repository.join(&root)).map_err(|error| error.to_string())?;
        fs::write(repository.join(&root).join("__init__.py"), b"")
            .map_err(|error| error.to_string())?;
        fs::create_dir_all(repository.join("tests")).map_err(|error| error.to_string())?;
        fs::write(repository.join("tests/.gitkeep"), b"").map_err(|error| error.to_string())?;
        (vec![root], vec!["tests".to_owned()], Vec::new(), Some(name))
    } else {
        let roots = if options.roots.is_empty() {
            package_roots
        } else {
            options.roots.clone()
        };
        let tests = if options.tests.is_empty() {
            vec!["tests".to_owned()]
        } else {
            options.tests.clone()
        };
        let tooling = options.tooling.clone();
        (roots, tests, tooling, None)
    };
    write_config(&repository, &roots, &tests, &tooling)?;
    write_gitignore(&repository, empty)?;
    let mut output = String::new();
    if let Some(name) = project_name {
        output.push_str(&format!("-> Empty repository\n    Created src/{name}/__init__.py\n    Created tests/\n    Wrote fensu.toml\n"));
    } else {
        let runtime_count = roots
            .iter()
            .map(|root| python_count(&repository.join(root)))
            .sum::<usize>();
        output.push_str(&format!("-> Existing codebase - {runtime_count} Python files\n\n    Enabling the full Fensu ruleset: FF\n    Wrote fensu.toml\n"));
    }
    let drift = native_drift(&repository)?;
    if drift.0 == 0 {
        output.push_str("\n-> Found 0 faults\n");
    } else {
        output.push_str("\n-> Measuring current drift\n");
        output.push_str(&format!(
            "\n    Found {} {} across {} {} against the starting ruleset.\n",
            drift.0,
            if drift.0 == 1 { "fault" } else { "faults" },
            drift.1,
            if drift.1 == 1 { "file" } else { "files" }
        ));
    }
    if options.skills == Some(true) {
        let args = vec!["skills".to_owned()];
        let code = process::run_python(&args)?;
        if code != 0 {
            return Ok(CliOutput {
                stdout: output,
                stderr: String::new(),
                exit_code: code,
            });
        }
    }
    output.push_str("\n-> Next\n\n    fensu check            run anytime\n    fensu rule FFA001      inspect any code in the output\n");
    Ok(CliOutput::success(output))
}

fn parse_init(arguments: &[String]) -> Result<InitOptions, String> {
    let mut options = InitOptions::default();
    let mut index = 0;
    while index < arguments.len() {
        match arguments[index].as_str() {
            "--yes" => options.yes = true,
            "--skills" => options.skills = Some(true),
            "--no-skills" => options.skills = Some(false),
            "--help" | "-h" => options.help = true,
            "--name" => {
                index += 1;
                options.name = Some(required_value(arguments, index, "--name")?);
            }
            "--root" | "--tests" | "--tooling" => {
                let option = arguments[index].clone();
                let mut values = Vec::new();
                while index + 1 < arguments.len() && !arguments[index + 1].starts_with('-') {
                    index += 1;
                    values.push(arguments[index].clone());
                }
                if values.is_empty() {
                    return Err(format!(
                        "fensu init: error: argument {option}: expected at least one argument"
                    ));
                }
                match option.as_str() {
                    "--root" => options.roots.extend(values),
                    "--tests" => options.tests.extend(values),
                    _ => options.tooling.extend(values),
                }
            }
            value => {
                return Err(format!(
                    "usage: fensu init ...\nfensu init: error: unrecognized arguments: {value}"
                ))
            }
        }
        index += 1;
    }
    Ok(options)
}

fn required_value(arguments: &[String], index: usize, option: &str) -> Result<String, String> {
    arguments
        .get(index)
        .filter(|value| !value.starts_with('-'))
        .cloned()
        .ok_or_else(|| format!("fensu init: error: argument {option}: expected one argument"))
}

fn local_config(repository: &Path) -> Option<PathBuf> {
    let fensu = repository.join("fensu.toml");
    if fensu.is_file() {
        return Some(fensu);
    }
    let pyproject = repository.join("pyproject.toml");
    fs::read_to_string(&pyproject)
        .ok()
        .filter(|text| text.contains("[tool.fensu]"))
        .map(|_| pyproject)
}

fn repository_python_files(repository: &Path) -> Vec<PathBuf> {
    WalkDir::new(repository)
        .into_iter()
        .filter_entry(|entry| {
            !matches!(
                entry.file_name().to_str(),
                Some(".git" | ".venv" | "venv" | "target" | "dist" | "build" | "__pycache__")
            )
        })
        .filter_map(Result::ok)
        .filter(|entry| {
            entry.file_type().is_file()
                && entry.path().extension().and_then(|value| value.to_str()) == Some("py")
        })
        .map(|entry| entry.into_path())
        .collect()
}

fn detected_roots(repository: &Path) -> Vec<String> {
    let mut roots = BTreeSet::new();
    for path in repository_python_files(repository) {
        if path.file_name().and_then(|value| value.to_str()) != Some("__init__.py") {
            continue;
        }
        let Some(parent) = path.parent() else {
            continue;
        };
        let parent_parent_is_package = parent
            .parent()
            .is_some_and(|candidate| candidate.join("__init__.py").is_file());
        if !parent_parent_is_package {
            if let Ok(relative) = parent.strip_prefix(repository) {
                roots.insert(relative.to_string_lossy().replace('\\', "/"));
            }
        }
    }
    roots.into_iter().collect()
}

fn normalize_name(value: &str) -> Result<String, String> {
    let mut result = String::new();
    for character in value.trim().chars() {
        if character.is_ascii_alphanumeric() || character == '_' {
            result.push(character.to_ascii_lowercase());
        } else if !result.ends_with('_') {
            result.push('_');
        }
    }
    let result = result.trim_matches('_').to_owned();
    if result.is_empty() {
        return Err(format!(
            "Project name cannot be normalized to a Python identifier: {value:?}."
        ));
    }
    Ok(
        if result.starts_with(|character: char| character.is_ascii_digit()) {
            format!("_{result}")
        } else {
            result
        },
    )
}

fn write_config(
    repository: &Path,
    roots: &[String],
    tests: &[String],
    tooling: &[String],
) -> Result<(), String> {
    let mut text = format!(
        "roots = {}\ntests = {}\n",
        serde_json::to_string(roots).map_err(|error| error.to_string())?,
        serde_json::to_string(tests).map_err(|error| error.to_string())?
    );
    if !tooling.is_empty() {
        text.push_str(&format!(
            "tooling = {}\n",
            serde_json::to_string(tooling).map_err(|error| error.to_string())?
        ));
    }
    text.push_str("select = [\"FF\"]\n");
    fs::write(repository.join("fensu.toml"), text).map_err(|error| error.to_string())
}

fn write_gitignore(repository: &Path, empty: bool) -> Result<(), String> {
    let path = repository.join(".gitignore");
    let mut value = if path.is_file() {
        fs::read(&path).map_err(|error| error.to_string())?
    } else if empty {
        include_bytes!(concat!(env!("OUT_DIR"), "/python.gitignore")).to_vec()
    } else {
        Vec::new()
    };
    if !value.ends_with(b"\n") && !value.is_empty() {
        value.push(b'\n');
    }
    if !String::from_utf8_lossy(&value).contains(".fensu/cache/") {
        value.extend_from_slice(FENSU_IGNORE.as_bytes());
    }
    fs::write(path, value).map_err(|error| error.to_string())
}

fn python_count(path: &Path) -> usize {
    WalkDir::new(path)
        .into_iter()
        .filter_map(Result::ok)
        .filter(|entry| {
            entry.file_type().is_file()
                && entry.path().extension().and_then(|value| value.to_str()) == Some("py")
        })
        .count()
}

fn native_drift(repository: &Path) -> Result<(usize, usize), String> {
    let executable = env::current_exe().map_err(|error| error.to_string())?;
    let output = Command::new(executable)
        .args(["check", "--no-color", "--cache"])
        .current_dir(repository)
        .output()
        .map_err(|error| error.to_string())?;
    let stdout = String::from_utf8_lossy(&output.stdout);
    let faults = stdout.matches(" --> ").count();
    let files = stdout
        .lines()
        .filter_map(|line| line.strip_prefix(" --> "))
        .filter_map(|location| location.rsplitn(3, ':').last())
        .collect::<BTreeSet<_>>()
        .len();
    Ok((faults, files))
}
