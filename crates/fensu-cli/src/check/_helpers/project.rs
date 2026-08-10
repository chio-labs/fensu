//! Native project-plane identities are target-relative; reporting prefixes the target exactly once.

use std::collections::{HashMap, HashSet};
use std::fs;
use std::path::{Component, Path, PathBuf};

use fensu_facts::extension::models::ProgramHandle;
use fensu_native::rules::models::{NativeProjectModule, NativeProjectPlane};
use globset::GlobBuilder;
use serde_json::Value;
use walkdir::DirEntry;
use walkdir::WalkDir;

use crate::analyzer::AnalyzerId;
use crate::check::_helpers::policy::{bool_text, hex_digest, program, python_version, relative};
use crate::constants::{SCOPE_TEST, STEM_INIT, VALUE_TRUE};
use crate::models::{
    Config, ImportGraphFact, ParsedProgram, ProjectInput, ScopedSource, WebParseFailure,
};

const ENTRYPOINT_SECTIONS: [&str; 3] = ["scripts", "gui-scripts", "entry-points"];

include!("web.inc");

pub(crate) fn project_plane(
    root: &Path,
    config: &Config,
    sources: &[ScopedSource],
) -> Result<NativeProjectPlane, String> {
    let mut modules: Vec<NativeProjectModule> = Vec::new();
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
            source.target_path.clone(),
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
        if !scan_root.exists() {
            continue;
        }
        for result in WalkDir::new(&scan_root) {
            let entry = result.map_err(|error| {
                format!("Could not discover Python support files under {configured_root}: {error}")
            })?;
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
            let target_path = entry
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
                target_path,
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
    let Ok(value) = toml::from_str::<toml::Value>(&text) else {
        return Vec::new();
    };
    let Some(project) = value.get("project") else {
        return Vec::new();
    };
    let mut values: Vec<&str> = Vec::new();
    for section in ENTRYPOINT_SECTIONS {
        if let Some(value) = project.get(section) {
            values = collect_entrypoint_values(value, values);
        }
    }
    let mut modules = values
        .into_iter()
        .filter_map(|value| value.split(':').next())
        .map(str::trim)
        .filter(|value| !value.is_empty())
        .map(str::to_owned)
        .collect::<Vec<_>>();
    modules.sort();
    modules.dedup();
    modules
}

fn collect_entrypoint_values<'a>(value: &'a toml::Value, mut values: Vec<&'a str>) -> Vec<&'a str> {
    if let Some(value) = value.as_str() {
        values.push(value);
    } else if let Some(table) = value.as_table() {
        for value in table.values() {
            values = collect_entrypoint_values(value, values);
        }
    }
    values
}

pub(crate) fn observe(
    root: &Path,
    plans: &[fensu_native::rules::models::NativeProjectQuery],
    programs: &HashMap<&str, &ProgramHandle>,
    modules: &HashMap<String, &ProgramHandle>,
) -> Result<HashMap<String, Vec<String>>, String> {
    let mut answers: HashMap<String, Vec<String>> = HashMap::new();
    for query in plans {
        let path = root.join(&query.path);
        let value = match query.kind.as_str() {
            "exists" => vec![bool_text(path.exists())],
            "is_file" => vec![bool_text(path.is_file())],
            "is_dir" => vec![bool_text(path.is_dir())],
            "dataclasses" => match programs.get(query.path.as_str()) {
                Some(program) => program
                    .dataclass_rows()
                    .iter()
                    .map(|row| row.name.clone())
                    .collect(),
                None => Vec::new(),
            },
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
            )?)],
            "custom_rule_coverage" => Vec::new(),
            "directory_entries" => directory_entries(&path, root)?,
            "glob" => glob_answers(&path, root, &query.argument)?,
            "python_anchor" => python_anchor(&path, root)?.into_iter().collect(),
            _ => Vec::new(),
        };
        answers.insert(query.key(), value);
    }
    Ok(answers)
}

pub(crate) fn directory_entries(path: &Path, root: &Path) -> Result<Vec<String>, String> {
    let mut entries: Vec<String> = Vec::new();
    if !path.exists() {
        return Ok(entries);
    }
    let directory = path
        .read_dir()
        .map_err(|error| format!("Could not read directory {}: {error}", path.display()))?;
    for result in directory {
        let entry = result
            .map_err(|error| format!("Could not read directory {}: {error}", path.display()))?;
        if let Ok(relative) = entry.path().strip_prefix(root) {
            entries.push(relative.to_string_lossy().replace('\\', "/"));
        }
    }
    Ok(entries)
}

pub(crate) fn glob_answers(
    path: &Path,
    root: &Path,
    argument: &str,
) -> Result<Vec<String>, String> {
    let (pattern, recursive) = argument.split_once('\0').unwrap_or((argument, "false"));
    let depth = if recursive == VALUE_TRUE {
        usize::MAX
    } else {
        1
    };
    let Ok(glob) = GlobBuilder::new(pattern).literal_separator(true).build() else {
        return Ok(Vec::new());
    };
    let matcher = glob.compile_matcher();
    let mut answers: Vec<String> = Vec::new();
    if !path.exists() {
        return Ok(answers);
    }
    for result in WalkDir::new(path).min_depth(1).max_depth(depth).into_iter() {
        let entry = result.map_err(|error| {
            format!("Could not evaluate glob under {}: {error}", path.display())
        })?;
        if !matcher.is_match(entry.path().strip_prefix(path).unwrap_or(entry.path())) {
            continue;
        }
        if let Ok(relative) = entry.path().strip_prefix(root) {
            answers.push(relative.to_string_lossy().replace('\\', "/"));
        }
    }
    Ok(answers)
}

pub(crate) fn python_anchor(path: &Path, root: &Path) -> Result<Option<String>, String> {
    if !path.exists() {
        return Ok(None);
    }
    let init = path.join("__init__.py");
    if init.is_file() {
        return Ok(relative(&init, root));
    }
    let mut files: Vec<PathBuf> = Vec::new();
    for result in WalkDir::new(path) {
        let entry = result.map_err(|error| {
            format!(
                "Could not discover Python anchor under {}: {error}",
                path.display()
            )
        })?;
        if entry.file_type().is_file()
            && entry.path().extension().and_then(|value| value.to_str()) == Some("py")
        {
            files.push(entry.into_path());
        }
    }
    files.sort();
    Ok(files.first().and_then(|file| relative(file, root)))
}

pub(crate) fn package_anchor(package: &Path, reported: &Path) -> Result<bool, String> {
    if !package.exists() {
        return Ok(false);
    }
    let init = package.join("__init__.py");
    if init.exists() {
        return Ok(reported == init);
    }
    let mut files: Vec<PathBuf> = Vec::new();
    for result in WalkDir::new(package) {
        let entry = result.map_err(|error| {
            format!(
                "Could not discover package anchor under {}: {error}",
                package.display()
            )
        })?;
        if entry.file_type().is_file()
            && entry.path().extension().and_then(|value| value.to_str()) == Some("py")
        {
            files.push(entry.into_path());
        }
    }
    files.sort();
    Ok(files.first() == Some(&reported.to_path_buf()))
}
