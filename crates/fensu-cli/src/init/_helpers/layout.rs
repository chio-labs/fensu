//! Decide the package, test, and tooling layout initialisation will write.

use std::fs;
use std::path::Path;

use crate::analyzer::AnalyzerId;
use crate::init::_helpers::arguments::normalize_name;
use crate::init::constants::{
    DEFAULT_TARGET_ROOT, PYTHON_TARGET_NAME, SVELTEKIT_PRESET, TESTS_ROOT, WEB_TARGET_NAME,
};
use crate::init::models::{InitPlan, RepositorySurvey};
use crate::models::{DetectedTarget, InitOptions};

pub(crate) fn plan_layout(
    repository: &Path,
    options: &InitOptions,
    survey: &RepositorySurvey,
) -> Result<InitPlan, String> {
    if options.preset.as_deref() == Some(SVELTEKIT_PRESET) {
        fs::create_dir_all(repository.join("src")).map_err(|error| error.to_string())?;
        return Ok(InitPlan {
            roots: Vec::new(),
            tests: Vec::new(),
            tooling: Vec::new(),
            project_name: None,
            targets: vec![sveltekit_target(WEB_TARGET_NAME, DEFAULT_TARGET_ROOT)],
        });
    }
    let selected_svelte = survey
        .targets
        .iter()
        .filter(|target| !options.excluded_targets.contains(&target.name))
        .cloned()
        .collect::<Vec<_>>();
    if !selected_svelte.is_empty() {
        let mut targets: Vec<DetectedTarget> = Vec::new();
        let python_roots = survey
            .package_roots
            .iter()
            .filter(|root| root.as_str() != TESTS_ROOT)
            .cloned()
            .collect::<Vec<_>>();
        if !python_roots.is_empty() {
            targets.push(DetectedTarget {
                name: PYTHON_TARGET_NAME.to_owned(),
                analyzer: AnalyzerId::Python,
                root: DEFAULT_TARGET_ROOT.to_owned(),
                roots: python_roots,
                tests: vec![TESTS_ROOT.to_owned()],
                tooling: Vec::new(),
                framework: None,
                rule_packs: Vec::new(),
                select: vec!["FF".to_owned()],
            });
        }
        targets.extend(selected_svelte);
        return Ok(InitPlan {
            roots: Vec::new(),
            tests: Vec::new(),
            tooling: Vec::new(),
            project_name: None,
            targets,
        });
    }
    if survey.empty {
        return empty_repository_plan(repository, options);
    }
    let tests = if options.tests.is_empty() {
        vec!["tests".to_owned()]
    } else {
        options.tests.clone()
    };
    let roots = if options.roots.is_empty() {
        survey
            .package_roots
            .iter()
            .filter(|root| !tests.contains(root))
            .cloned()
            .collect()
    } else {
        options.roots.clone()
    };
    Ok(InitPlan {
        roots,
        tests,
        tooling: options.tooling.clone(),
        project_name: None,
        targets: Vec::new(),
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
        targets: Vec::new(),
    })
}

fn sveltekit_target(name: &str, root: &str) -> DetectedTarget {
    DetectedTarget {
        name: name.to_owned(),
        analyzer: AnalyzerId::Svelte,
        root: root.to_owned(),
        roots: vec!["src".to_owned()],
        tests: Vec::new(),
        tooling: Vec::new(),
        framework: Some("sveltekit".to_owned()),
        rule_packs: Vec::new(),
        select: vec!["FW".to_owned()],
    }
}
