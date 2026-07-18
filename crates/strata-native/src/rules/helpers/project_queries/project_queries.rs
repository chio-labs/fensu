//! Plan dependency-recording observations required by native FILE rules.

use std::collections::HashSet;

use strata_facts::extension::models::ProgramHandle;
use strata_facts::facts::models::ImportRow;

use crate::rules::constants::{
    BANNED_GENERIC_PACKAGE_NAME_CODE, CUSTOM_RULE_TEST_COVERAGE_CODE,
    MAIN_ENTRY_NAME_COLLISION_CODE, MEANINGFUL_PROJECT_RESULT_DISCARDED_CODE,
    NO_CROSS_DOMAIN_PRIVATE_MAIN_IMPORTS_CODE, NO_CROSS_PACKAGE_INTERNALS_CODE,
    NO_SIBLING_PACKAGE_INTERNALS_CODE, TEST_CASE_ANNOTATION_CODE, TEST_LAYOUT_CODE,
    TEST_LOCAL_TEST_CASE_CONSTRUCTORS_CODE, TEST_LOCAL_TEST_TYPES_FILE_CODE,
    TEST_MIRRORED_ROOT_CODE, TEST_SCOPE_CODE, TEST_SCRIPTS_AREA_EXISTS_CODE,
    TEST_SCRIPTS_MIRROR_DEPTH_CODE, TEST_SRC_AREA_EXISTS_CODE, TEST_SRC_MIRROR_DEPTH_CODE,
    TEST_SRC_PACKAGE_EXISTS_CODE, TOOLING_PACKAGE_LAYOUT_CODE,
};
use crate::rules::models::{NativeProjectQuery, NativeRuleContext};

const INIT_FILE: &str = "__init__.py";
const TEST_TYPES_FILE: &str = "_test_types.py";
const ROOT_SCOPE: &str = "root";
const TOOLING_SCOPE: &str = "tooling";
const TEST_SCOPE: &str = "test";
const ROOT_TEST_AREA: &str = "__root__";
const MINIMUM_TEST_LAYOUT_PARTS: usize = 3;
const MINIMUM_TOOLING_PACKAGE_PARTS: usize = 3;
const MAIN_ROLE_NAME: &str = "main";
const NON_TEST_MODULES: &[&str] = &[
    "_test_helpers.py",
    TEST_TYPES_FILE,
    "helpers.py",
    "conftest.py",
    INIT_FILE,
];
const BANNED_PACKAGES: &[&str] = &[
    "base", "common", "helpers", "lib", "misc", "shared", "util", "utils",
];
const TEST_LAYOUT_CODES: &[&str] = &[
    TEST_LAYOUT_CODE,
    TEST_SCOPE_CODE,
    TEST_MIRRORED_ROOT_CODE,
    TEST_SRC_MIRROR_DEPTH_CODE,
    TEST_SRC_PACKAGE_EXISTS_CODE,
    TEST_SRC_AREA_EXISTS_CODE,
    TEST_SCRIPTS_MIRROR_DEPTH_CODE,
    TEST_SCRIPTS_AREA_EXISTS_CODE,
];

pub(crate) fn plan_project_queries(
    program: &ProgramHandle,
    codes: &[String],
    context: &NativeRuleContext,
) -> Vec<NativeProjectQuery> {
    let selected: HashSet<&str> = codes.iter().map(String::as_str).collect();
    let mut queries = Vec::new();
    if selected.contains(MEANINGFUL_PROJECT_RESULT_DISCARDED_CODE) && context.is_main_module {
        for call in &program.project_rows().1 {
            if let Some(module_name) = &call.module_name {
                queries.push(query("module_function", module_name, &call.function_name));
            }
        }
    }
    if selected.contains(NO_SIBLING_PACKAGE_INTERNALS_CODE)
        || selected.contains(NO_CROSS_PACKAGE_INTERNALS_CODE)
    {
        for target in normalized_targets(program, context) {
            if let Some(path) = module_init_path(context, &target) {
                queries.push(query("exists", &path, ""));
            }
        }
    }
    if selected.contains(NO_CROSS_DOMAIN_PRIVATE_MAIN_IMPORTS_CODE) {
        for target in module_targets(program, context) {
            if private_main_target(&target) {
                if let Some(path) = module_file_path(context, &target) {
                    queries.push(query("is_file", &path, ""));
                }
            }
        }
    }
    if TEST_LAYOUT_CODES
        .iter()
        .any(|code| selected.contains(*code))
    {
        if let Some(path) = test_layout_area_path(context) {
            queries.push(query("exists", &path, ""));
        }
    }
    if is_test_module(context) {
        if selected.contains(TEST_LOCAL_TEST_TYPES_FILE_CODE) {
            queries.push(query(
                "is_file",
                &sibling_path(context, TEST_TYPES_FILE),
                "",
            ));
        }
        if selected.contains(TEST_CASE_ANNOTATION_CODE)
            || selected.contains(TEST_LOCAL_TEST_CASE_CONSTRUCTORS_CODE)
        {
            queries.push(query(
                "dataclasses",
                &sibling_path(context, TEST_TYPES_FILE),
                "",
            ));
        }
    }
    if selected.contains(BANNED_GENERIC_PACKAGE_NAME_CODE) && context.scope != TOOLING_SCOPE {
        for (index, part) in context.relative_parts
            [..context.relative_parts.len().saturating_sub(1)]
            .iter()
            .enumerate()
        {
            if BANNED_PACKAGES.contains(&part.as_str()) {
                let package = scope_root(context)
                    .into_iter()
                    .chain(context.relative_parts[..=index].iter().cloned())
                    .collect::<Vec<_>>()
                    .join("/");
                queries.push(query("package_anchor", &package, &context.repository_path));
            }
        }
    }
    if selected.contains(MAIN_ENTRY_NAME_COLLISION_CODE) && context.is_entry_module {
        queries.push(query(
            "is_dir",
            context
                .repository_path
                .strip_suffix(".py")
                .unwrap_or(&context.repository_path),
            "",
        ));
    }
    if selected.contains(TOOLING_PACKAGE_LAYOUT_CODE) {
        if let Some(package) = invalid_tooling_package(context) {
            queries.push(query("package_anchor", &package, &context.repository_path));
        }
    }
    if selected.contains(CUSTOM_RULE_TEST_COVERAGE_CODE)
        && !context.custom_registrations.is_empty()
        && context
            .thresholds
            .get("min_custom_rule_test_cases")
            .copied()
            .unwrap_or_default()
            > 0
    {
        queries.push(query("custom_rule_coverage", "", ""));
    }
    let mut seen = HashSet::new();
    queries
        .into_iter()
        .filter(|item| seen.insert(item.clone()))
        .collect()
}

fn query(kind: &str, path: &str, argument: &str) -> NativeProjectQuery {
    NativeProjectQuery {
        kind: kind.to_owned(),
        path: path.to_owned(),
        argument: argument.to_owned(),
    }
}

fn file_name(context: &NativeRuleContext) -> &str {
    context.relative_parts.last().map_or("", String::as_str)
}

fn is_test_module(context: &NativeRuleContext) -> bool {
    context.scope == TEST_SCOPE && !NON_TEST_MODULES.contains(&file_name(context))
}

fn sibling_path(context: &NativeRuleContext, name: &str) -> String {
    let parent = context
        .repository_path
        .rsplit_once('/')
        .map_or("", |item| item.0);
    format!("{parent}/{name}")
}

fn scope_root(context: &NativeRuleContext) -> Vec<String> {
    let keep = context
        .repository_path
        .split('/')
        .count()
        .saturating_sub(context.relative_parts.len());
    context
        .repository_path
        .split('/')
        .take(keep)
        .map(str::to_owned)
        .collect()
}

fn configured_roots<'a>(context: &'a NativeRuleContext, scope: &str) -> Vec<&'a str> {
    context
        .scope_roots
        .iter()
        .filter_map(|(kind, path)| (kind == scope).then_some(path.as_str()))
        .collect()
}

fn test_layout_area_path(context: &NativeRuleContext) -> Option<String> {
    if context.scope != TEST_SCOPE
        || matches!(file_name(context), INIT_FILE | "conftest.py")
        || context.relative_parts.len() < MINIMUM_TEST_LAYOUT_PARTS
    {
        return None;
    }
    let mirrored = &context.relative_parts[1..context.relative_parts.len() - 1];
    let mut matched: Vec<(&str, &str, usize)> = Vec::new();
    for (scope, root) in &context.scope_roots {
        if scope != ROOT_SCOPE && scope != TOOLING_SCOPE {
            continue;
        }
        let parts: Vec<&str> = root.split('/').collect();
        if mirrored
            .iter()
            .map(String::as_str)
            .take(parts.len())
            .eq(parts.iter().copied())
        {
            matched.push((scope, root, parts.len()));
        }
    }
    matched.sort_by_key(|(_, _, length)| *length);
    let (scope, root, length) = matched.last().copied()?;
    if mirrored.len() <= length {
        return None;
    }
    let area = &mirrored[length];
    if scope == ROOT_SCOPE && area == ROOT_TEST_AREA {
        return None;
    }
    Some(format!("{root}/{area}"))
}

fn normalized_targets(program: &ProgramHandle, context: &NativeRuleContext) -> Vec<Vec<String>> {
    program
        .reference_rows()
        .imports
        .iter()
        .flat_map(|row| normalized_import_targets(row, context))
        .collect()
}

fn module_targets(program: &ProgramHandle, context: &NativeRuleContext) -> Vec<Vec<String>> {
    let mut targets = Vec::new();
    for row in &program.reference_rows().imports {
        for base in normalized_import_targets(row, context) {
            targets.push(base.clone());
            if row.from_import {
                for alias in &row.aliases {
                    let mut target = base.clone();
                    target.extend(alias.imported_name.split('.').map(str::to_owned));
                    targets.push(target);
                }
            }
        }
    }
    targets
}

fn normalized_import_targets(row: &ImportRow, context: &NativeRuleContext) -> Vec<Vec<String>> {
    if !row.from_import {
        return row
            .aliases
            .iter()
            .map(|alias| alias.imported_name.split('.').map(str::to_owned).collect())
            .collect();
    }
    if row.relative_level == 0 {
        return (!row.module_parts.is_empty())
            .then(|| row.module_parts.clone())
            .into_iter()
            .collect();
    }
    if row.module_parts.is_empty() {
        return Vec::new();
    }
    let mut current = module_parts(context);
    if file_name(context) != INIT_FILE {
        let _ = current.pop();
    }
    let parents = row.relative_level.saturating_sub(1) as usize;
    if parents > current.len() {
        return Vec::new();
    }
    current.truncate(current.len() - parents);
    current.extend(row.module_parts.clone());
    vec![current]
}

fn module_parts(context: &NativeRuleContext) -> Vec<String> {
    let mut parts = vec![context.package_name.clone()];
    parts.extend(context.relative_parts.iter().cloned());
    if let Some(last) = parts.last_mut() {
        *last = last.strip_suffix(".py").unwrap_or(last).to_owned();
    }
    if parts
        .last()
        .is_some_and(|part| part == INIT_FILE.trim_end_matches(".py"))
    {
        let _ = parts.pop();
    }
    parts
}

fn runtime_root<'a>(context: &'a NativeRuleContext, package: &str) -> Option<&'a str> {
    configured_roots(context, "root")
        .into_iter()
        .find(|root| root.rsplit('/').next() == Some(package))
}

fn module_init_path(context: &NativeRuleContext, parts: &[String]) -> Option<String> {
    let package = parts.first()?;
    let root = runtime_root(context, package)?;
    let parent = root.rsplit_once('/').map_or("", |item| item.0);
    Some(format!("{parent}/{}/{INIT_FILE}", parts.join("/")))
}

fn module_file_path(context: &NativeRuleContext, parts: &[String]) -> Option<String> {
    let package = parts.first()?;
    let root = runtime_root(context, package)?;
    let parent = root.rsplit_once('/').map_or("", |item| item.0);
    Some(format!("{parent}/{}.py", parts.join("/")))
}

fn private_main_target(parts: &[String]) -> bool {
    let structural = [
        "main",
        "_helpers",
        "classes",
        "models",
        "types",
        "constants",
        "exceptions",
    ];
    let Some(role_index) = parts
        .iter()
        .enumerate()
        .skip(1)
        .find_map(|(index, part)| structural.contains(&part.as_str()).then_some(index))
    else {
        return false;
    };
    parts[role_index] == MAIN_ROLE_NAME
        && parts[role_index + 1..]
            .last()
            .is_some_and(|name| name.starts_with('_') && !name.starts_with("__"))
}

fn invalid_tooling_package(context: &NativeRuleContext) -> Option<String> {
    if context.scope != TOOLING_SCOPE
        || context.relative_parts.len() < MINIMUM_TOOLING_PACKAGE_PARTS
    {
        return None;
    }
    let approved = [
        "main",
        "_helpers",
        "classes",
        "rules",
        "models.py",
        "types.py",
        "constants.py",
        "exceptions.py",
    ];
    if approved.contains(&context.relative_parts[1].as_str()) {
        return None;
    }
    let mut parts = scope_root(context);
    parts.push(context.relative_parts[0].clone());
    parts.push(context.relative_parts[1].clone());
    Some(parts.join("/"))
}
