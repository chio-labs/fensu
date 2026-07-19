use std::collections::HashMap;
use std::fs;
use std::path::Path;

use globset::GlobBuilder;
use strata_facts::extension::models::ProgramHandle;
use strata_native::rules::models::{NativeProjectModule, NativeProjectPlane};
use walkdir::WalkDir;

use crate::constants::{SCOPE_TEST, STEM_INIT, VALUE_TRUE};
use crate::helpers::check_policy::{bool_text, program, python_version, relative};
use crate::models::{Config, ScopedSource};

pub(crate) fn project_plane(
    root: &Path,
    config: &Config,
    sources: &[ScopedSource],
) -> Result<NativeProjectPlane, String> {
    let mut modules = Vec::new();
    for source in sources.iter().filter(|source| source.scope != SCOPE_TEST) {
        let mut parts = source
            .path
            .strip_prefix(source.root.parent().unwrap_or(root))
            .map_err(|error| error.to_string())?
            .components()
            .map(|part| part.as_os_str().to_string_lossy().into_owned())
            .collect::<Vec<_>>();
        if let Some(last) = parts.last_mut() {
            *last = last.trim_end_matches(".py").to_owned();
        }
        if parts.last().is_some_and(|part| part == STEM_INIT) {
            parts.pop();
        }
        modules.push(NativeProjectModule::new(
            source.repository_path.clone(),
            source.scope.clone(),
            parts,
            program(source).clone(),
        ));
    }
    for (scope, configured_root) in config
        .roots
        .iter()
        .map(|path| ("root", path))
        .chain(config.tooling.iter().map(|path| ("tooling", path)))
    {
        let scan_root = root.join(configured_root);
        for entry in WalkDir::new(&scan_root).into_iter().filter_map(Result::ok) {
            if !entry.file_type().is_file()
                || entry.path().extension().and_then(|value| value.to_str()) != Some("pyi")
            {
                continue;
            }
            let source = fs::read_to_string(entry.path()).map_err(|error| error.to_string())?;
            let Some(program) = ProgramHandle::parse_many(vec![source], python_version())
                .pop()
                .flatten()
            else {
                continue;
            };
            let repository_path = entry
                .path()
                .strip_prefix(root)
                .map_err(|error| error.to_string())?
                .to_string_lossy()
                .replace('\\', "/");
            let mut parts = entry
                .path()
                .strip_prefix(scan_root.parent().unwrap_or(root))
                .map_err(|error| error.to_string())?
                .components()
                .map(|part| part.as_os_str().to_string_lossy().into_owned())
                .collect::<Vec<_>>();
            if let Some(last) = parts.last_mut() {
                *last = last.trim_end_matches(".pyi").to_owned();
            }
            if parts.last().is_some_and(|part| part == STEM_INIT) {
                parts.pop();
            }
            modules.push(NativeProjectModule::new(
                repository_path,
                scope.to_owned(),
                parts,
                program,
            ));
        }
    }
    Ok(NativeProjectPlane::new(
        modules,
        entrypoint_modules(root, &config.raw),
    ))
}

pub(crate) fn entrypoint_modules(root: &Path, _config_raw: &[u8]) -> Vec<String> {
    let Ok(text) = fs::read_to_string(root.join("pyproject.toml")) else {
        return Vec::new();
    };
    let Ok(value) = text.parse::<toml::Value>() else {
        return Vec::new();
    };
    value
        .get("project")
        .and_then(|project| project.get("scripts"))
        .and_then(toml::Value::as_table)
        .into_iter()
        .flatten()
        .filter_map(|(_, value)| value.as_str())
        .filter_map(|value| value.split(':').next())
        .map(str::to_owned)
        .collect()
}

pub(crate) fn observe(
    root: &Path,
    plans: &[strata_native::rules::models::NativeProjectQuery],
    programs: &HashMap<&str, &ProgramHandle>,
    modules: &HashMap<String, &ProgramHandle>,
) -> HashMap<String, Vec<String>> {
    let mut answers = HashMap::new();
    for query in plans {
        let path = root.join(&query.path);
        let value = match query.kind.as_str() {
            "exists" => vec![bool_text(path.exists())],
            "is_file" => vec![bool_text(path.is_file())],
            "is_dir" => vec![bool_text(path.is_dir())],
            "dataclasses" => programs
                .get(query.path.as_str())
                .map(|program| {
                    program
                        .dataclass_rows()
                        .iter()
                        .map(|row| row.name.clone())
                        .collect()
                })
                .unwrap_or_default(),
            "module_function" => modules
                .get(&query.path)
                .and_then(|program| {
                    program
                        .project_rows()
                        .0
                        .iter()
                        .find(|row| row.name == query.argument)
                })
                .map(|row| {
                    vec![if row.meaningful_result {
                        "meaningful".to_owned()
                    } else {
                        "empty".to_owned()
                    }]
                })
                .unwrap_or_default(),
            "package_anchor" => vec![bool_text(package_anchor(
                &path,
                &root.join(&query.argument),
            ))],
            "custom_rule_coverage" => Vec::new(),
            "directory_entries" => directory_entries(&path, root),
            "glob" => glob_answers(&path, root, &query.argument),
            "python_anchor" => python_anchor(&path, root).into_iter().collect(),
            _ => Vec::new(),
        };
        answers.insert(query.key(), value);
    }
    answers
}

pub(crate) fn directory_entries(path: &Path, root: &Path) -> Vec<String> {
    path.read_dir()
        .ok()
        .into_iter()
        .flatten()
        .filter_map(Result::ok)
        .filter_map(|entry| {
            entry
                .path()
                .strip_prefix(root)
                .ok()
                .map(|path| path.to_string_lossy().replace('\\', "/"))
        })
        .collect()
}

pub(crate) fn glob_answers(path: &Path, root: &Path, argument: &str) -> Vec<String> {
    let (pattern, recursive) = argument.split_once('\0').unwrap_or((argument, "false"));
    let depth = if recursive == VALUE_TRUE {
        usize::MAX
    } else {
        1
    };
    let matcher = GlobBuilder::new(pattern)
        .literal_separator(true)
        .build()
        .ok()
        .map(|glob| glob.compile_matcher());
    let Some(matcher) = matcher else {
        return Vec::new();
    };
    WalkDir::new(path)
        .min_depth(1)
        .max_depth(depth)
        .into_iter()
        .filter_map(Result::ok)
        .filter(|entry| matcher.is_match(entry.path().strip_prefix(path).unwrap_or(entry.path())))
        .filter_map(|entry| {
            entry
                .path()
                .strip_prefix(root)
                .ok()
                .map(|path| path.to_string_lossy().replace('\\', "/"))
        })
        .collect()
}

pub(crate) fn python_anchor(path: &Path, root: &Path) -> Option<String> {
    let init = path.join("__init__.py");
    if init.is_file() {
        return relative(&init, root);
    }
    let mut files = WalkDir::new(path)
        .into_iter()
        .filter_map(Result::ok)
        .filter(|entry| {
            entry.file_type().is_file()
                && entry.path().extension().and_then(|value| value.to_str()) == Some("py")
        })
        .map(|entry| entry.into_path())
        .collect::<Vec<_>>();
    files.sort();
    files.first().and_then(|file| relative(file, root))
}

pub(crate) fn package_anchor(package: &Path, reported: &Path) -> bool {
    let init = package.join("__init__.py");
    if init.exists() {
        return reported == init;
    }
    let mut files = WalkDir::new(package)
        .into_iter()
        .filter_map(Result::ok)
        .filter(|entry| {
            entry.file_type().is_file()
                && entry.path().extension().and_then(|value| value.to_str()) == Some("py")
        })
        .map(|entry| entry.into_path())
        .collect::<Vec<_>>();
    files.sort();
    files.first() == Some(&reported.to_path_buf())
}
