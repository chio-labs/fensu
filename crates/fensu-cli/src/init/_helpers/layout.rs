//! Decide the package, test, and tooling layout initialisation will write.

use std::fs;
use std::path::Path;

use crate::init::_helpers::arguments::normalize_name;
use crate::init::models::{InitPlan, RepositorySurvey};
use crate::models::InitOptions;

pub(crate) fn plan_layout(
    repository: &Path,
    options: &InitOptions,
    survey: &RepositorySurvey,
) -> Result<InitPlan, String> {
    if survey.empty {
        return empty_repository_plan(repository, options);
    }
    let roots = if options.roots.is_empty() {
        survey.package_roots.clone()
    } else {
        options.roots.clone()
    };
    let tests = if options.tests.is_empty() {
        vec!["tests".to_owned()]
    } else {
        options.tests.clone()
    };
    Ok(InitPlan {
        roots,
        tests,
        tooling: options.tooling.clone(),
        project_name: None,
    })
}

fn empty_repository_plan(repository: &Path, options: &InitOptions) -> Result<InitPlan, String> {
    let name = normalize_name(
        options
            .name
            .as_deref()
            .ok_or_else(|| "Empty repository initialization requires --name NAME.".to_owned())?,
    )?;
    let root = format!("src/{name}");
    fs::create_dir_all(repository.join(&root)).map_err(|error| error.to_string())?;
    fs::write(repository.join(&root).join("__init__.py"), b"")
        .map_err(|error| error.to_string())?;
    fs::create_dir_all(repository.join("tests")).map_err(|error| error.to_string())?;
    fs::write(repository.join("tests/.gitkeep"), b"").map_err(|error| error.to_string())?;
    Ok(InitPlan {
        roots: vec![root],
        tests: vec!["tests".to_owned()],
        tooling: Vec::new(),
        project_name: Some(name),
    })
}
