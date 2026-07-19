//! Test-root and runtime/tooling mirror layout policy.

use crate::rules::constants::{
    TEST_LAYOUT_CODE, TEST_MIRRORED_ROOT_CODE, TEST_SCOPE_CODE, TEST_SCRIPTS_AREA_EXISTS_CODE,
    TEST_SCRIPTS_MIRROR_DEPTH_CODE, TEST_SRC_AREA_EXISTS_CODE, TEST_SRC_MIRROR_DEPTH_CODE,
    TEST_SRC_PACKAGE_EXISTS_CODE,
};
use crate::rules::models::{NativeFaultRow, NativeProjectQuery, NativeRuleContext};

const INIT_MODULE_NAME: &str = "__init__.py";
const CONFTEST_MODULE_NAME: &str = "conftest.py";
const ROOT_SCOPE: &str = "root";
const TOOLING_SCOPE: &str = "tooling";
const ROOT_TEST_AREA: &str = "__root__";
const MINIMUM_LAYOUT_DIRECTORIES: usize = 2;
const LAYOUT_CODES: &[&str] = &[
    TEST_LAYOUT_CODE,
    TEST_SCOPE_CODE,
    TEST_MIRRORED_ROOT_CODE,
    TEST_SRC_MIRROR_DEPTH_CODE,
    TEST_SRC_PACKAGE_EXISTS_CODE,
    TEST_SRC_AREA_EXISTS_CODE,
    TEST_SCRIPTS_MIRROR_DEPTH_CODE,
    TEST_SCRIPTS_AREA_EXISTS_CODE,
];

pub(crate) fn is_layout_code(code: &str) -> bool {
    LAYOUT_CODES.contains(&code)
}

pub(crate) fn layout_faults(
    code: &str,
    context: &NativeRuleContext,
    file_name: &str,
) -> Vec<NativeFaultRow> {
    if matches!(file_name, INIT_MODULE_NAME | CONFTEST_MODULE_NAME) {
        return Vec::new();
    }
    let Some((actual, message)) = layout_issue(context) else {
        return Vec::new();
    };
    (code == actual)
        .then(|| path_fault(code, message))
        .into_iter()
        .collect()
}

fn layout_issue(context: &NativeRuleContext) -> Option<(&'static str, &'static str)> {
    let directories = &context.relative_parts[..context.relative_parts.len().saturating_sub(1)];
    if directories.len() < MINIMUM_LAYOUT_DIRECTORIES {
        return Some((
            TEST_LAYOUT_CODE,
            "test directories must live under <configured-tests>/<scope>/...",
        ));
    }
    if !matches!(directories[0].as_str(), "unit" | "integration" | "e2e") {
        return Some((
            TEST_SCOPE_CODE,
            "test scope must be unit, integration, or e2e",
        ));
    }
    let mirrored = &directories[1..];
    let mut matches: Vec<(&str, &str, usize)> = context
        .scope_roots
        .iter()
        .filter(|(scope, _)| scope == ROOT_SCOPE || scope == TOOLING_SCOPE)
        .filter_map(|(scope, root)| {
            let parts: Vec<&str> = root.split('/').collect();
            mirrored
                .iter()
                .map(String::as_str)
                .take(parts.len())
                .eq(parts.iter().copied())
                .then_some((scope.as_str(), root.as_str(), parts.len()))
        })
        .collect();
    matches.sort_by_key(|(_, _, length)| *length);
    if let Some((scope, root, length)) = matches.last().copied() {
        if mirrored.len() <= length {
            return Some(if scope == ROOT_SCOPE {
                (
                    TEST_SRC_MIRROR_DEPTH_CODE,
                    "runtime tests must include an area beneath the configured source root",
                )
            } else {
                (
                    TEST_SCRIPTS_MIRROR_DEPTH_CODE,
                    "tooling tests must include an area beneath the configured tooling root",
                )
            });
        }
        let area = &mirrored[length];
        if scope == ROOT_SCOPE && area == ROOT_TEST_AREA {
            return None;
        }
        let path = format!("{root}/{area}");
        if !observed_bool(context, "exists", &path) {
            return Some(if scope == ROOT_SCOPE {
                (
                    TEST_SRC_AREA_EXISTS_CODE,
                    "runtime tests must mirror a real configured source package area",
                )
            } else {
                (
                    TEST_SCRIPTS_AREA_EXISTS_CODE,
                    "tooling tests must mirror a real configured tooling area",
                )
            });
        }
        return None;
    }
    for (_, root) in context
        .scope_roots
        .iter()
        .filter(|(scope, _)| scope == ROOT_SCOPE)
    {
        let parts: Vec<&str> = root.split('/').collect();
        let containers = &parts[..parts.len().saturating_sub(1)];
        if mirrored
            .iter()
            .map(String::as_str)
            .take(containers.len())
            .eq(containers.iter().copied())
        {
            return Some(if mirrored.len() <= containers.len() {
                (
                    TEST_SRC_MIRROR_DEPTH_CODE,
                    "runtime tests must mirror a configured package and area",
                )
            } else {
                (
                    TEST_SRC_PACKAGE_EXISTS_CODE,
                    "runtime tests must mirror a configured source package",
                )
            });
        }
    }
    Some((
        TEST_MIRRORED_ROOT_CODE,
        "test directories must mirror a configured runtime or tooling root",
    ))
}

fn observed_bool(context: &NativeRuleContext, kind: &str, path: &str) -> bool {
    context.observation(&NativeProjectQuery {
        kind: kind.to_owned(),
        path: path.to_owned(),
        argument: String::new(),
    }) == ["true"]
}

fn path_fault(code: &str, message: &str) -> NativeFaultRow {
    NativeFaultRow {
        code: code.to_owned(),
        line: 0,
        column: 0,
        message: Some(message.to_owned()),
        remediation: None,
        path: None,
    }
}
