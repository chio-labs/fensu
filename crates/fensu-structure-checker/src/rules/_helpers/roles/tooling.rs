//! Tooling-crate package layout and rule-module naming policy.

use crate::constants;
use crate::models;

const CODE_LENGTH: usize = 6;
const CODE_PREFIX: &[u8] = b"rs";

pub(crate) fn check(files: &[models::SourceFile]) -> Vec<models::Violation> {
    let mut violations: Vec<models::Violation> = Vec::new();
    for file in files {
        let Some(parts) = source_parts(file) else {
            continue;
        };
        violations.extend(rules_role_violations(file, &parts));
        violations.extend(package_layout_violations(file, &parts));
        violations.extend(rule_name_violations(file, &parts));
    }
    violations
}

fn source_parts(file: &models::SourceFile) -> Option<Vec<&str>> {
    Some(file.source_relative.split('/').collect())
}

fn rules_role_violations(file: &models::SourceFile, parts: &[&str]) -> Vec<models::Violation> {
    if parts.first() != Some(&constants::RULES_DIRECTORY) || rules_path_is_approved(parts) {
        return Vec::new();
    }
    vec![models::Violation::new(models::ViolationRequest {
        code: "RSR704",
        path: file.relative_path(),
        line: None,
        message: "tooling rules/ implementation bypasses an explicit role boundary",
        remediation:
            "keep orchestration under rules/main and supporting policy under rules/_helpers",
    })]
}

fn rules_path_is_approved(parts: &[&str]) -> bool {
    match parts {
        [_, file] => *file == constants::MOD_FILE || constants::ROLE_FILE_NAMES.contains(file),
        [_, role, ..] => constants::CONTAINER_DIRECTORY_NAMES.contains(role),
        _ => true,
    }
}

fn package_layout_violations(file: &models::SourceFile, parts: &[&str]) -> Vec<models::Violation> {
    if tooling_path_is_approved(parts) {
        return Vec::new();
    }
    vec![models::Violation::new(models::ViolationRequest {
        code: "RSR705",
        path: file.relative_path(),
        line: None,
        message: "tooling package contains source outside an explicit role",
        remediation: "use main/, _helpers/, or a reserved role file directly beneath the domain",
    })]
}

fn tooling_path_is_approved(parts: &[&str]) -> bool {
    match parts {
        [file] => {
            matches!(*file, constants::LIB_FILE | constants::MAIN_FILE)
                || constants::ROLE_FILE_NAMES.contains(file)
        }
        [constants::TESTS_DIRECTORY | constants::BIN_DIRECTORY, ..] => true,
        [_, file] => *file == constants::MOD_FILE || constants::ROLE_FILE_NAMES.contains(file),
        [_, role, ..] => constants::CONTAINER_DIRECTORY_NAMES.contains(role),
        _ => true,
    }
}

fn rule_name_violations(file: &models::SourceFile, parts: &[&str]) -> Vec<models::Violation> {
    if !parts.contains(&constants::RULES_DIRECTORY) || !is_rule_code(file.file_stem()) {
        return Vec::new();
    }
    vec![models::Violation::new(models::ViolationRequest {
        code: "RSR706",
        path: file.relative_path(),
        line: None,
        message: "rule module filename repeats one rule code instead of naming its policy",
        remediation: "rename the module after the policy or rule family it implements",
    })]
}

fn is_rule_code(stem: &str) -> bool {
    let lowered = stem.to_ascii_lowercase();
    let bytes = lowered.as_bytes();
    bytes.len() == CODE_LENGTH
        && bytes.starts_with(CODE_PREFIX)
        && bytes[2].is_ascii_alphabetic()
        && bytes[3..].iter().all(u8::is_ascii_digit)
}
