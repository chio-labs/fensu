//! File-local role policy decided entirely from Python-owned position data.

use crate::rules::constants::{
    BANNED_GENERIC_FILENAME_CODE, BANNED_GENERIC_PACKAGE_NAME_CODE, CLASSES_MODULE_NAME_CODE,
    CUSTOM_RULE_TEST_COVERAGE_CODE, DESCRIPTIVE_RULE_MODULE_NAMES_CODE, HELPERS_MODULE_NAME_CODE,
    HELPERS_PACKAGE_SHAPE_CODE, HELPERS_RESERVED_ROLE_FILENAMES_CODE,
    MAIN_ENTRY_NAME_COLLISION_CODE, NESTED_DIRECT_MODULES_CODE, NESTED_DIRECT_SUBPACKAGES_CODE,
    TOOLING_PACKAGE_LAYOUT_CODE, TOP_LEVEL_DIRECT_MODULES_CODE,
};
use crate::rules::models::{NativeFaultRow, NativeProjectQuery, NativeRuleContext};

use crate::rules::_helpers::generated_policy::{
    FFR201_FORBIDDEN_MODULE_FILENAMES, FFR204_FORBIDDEN_PACKAGE_NAMES,
    FFR303_RESERVED_ROLE_FILENAMES, FFR304_RECOGNIZED_ROLE_DIRECTORIES,
    FFR304_RECOGNIZED_ROLE_FILENAMES, FFR305_RECOGNIZED_ROLE_DIRECTORIES,
    FFR307_RECOGNIZED_ROLE_FILENAMES, FFR705_ALLOWED_TOOLING_ROLE_DIRECTORIES,
    FFR705_ALLOWED_TOOLING_ROLE_FILES,
};
use crate::rules::_helpers::roles::{is_rule_code, path_fault, path_name};

const CLASSES_FILE_NAME: &str = "classes.py";
const HELPERS_DIRECTORY_NAME: &str = "_helpers";
const HELPERS_FILE_NAME: &str = "helpers.py";
const INIT_FILE_NAME: &str = "__init__.py";
const MAIN_DIRECTORY_NAME: &str = "main";
const MAIN_FILE_NAME: &str = "main.py";
const MINIMUM_NESTED_MODULE_PARTS: usize = 3;
const MINIMUM_NESTED_SUBPACKAGE_PARTS: usize = 4;
const PYTHON_SUFFIX: &str = ".py";
const RULES_ROLE: &str = "rules";
const ROOT_SCOPE: &str = "root";
const TEST_SCOPE: &str = "test";
const TOOLING_SCOPE: &str = "tooling";
const TOP_LEVEL_MODULE_PARTS: usize = 2;
const MIN_CUSTOM_RULE_TEST_CASES: &str = "min_custom_rule_test_cases";

pub(crate) fn path_faults(code: &str, context: &NativeRuleContext) -> Option<Vec<NativeFaultRow>> {
    let faults = match code {
        BANNED_GENERIC_FILENAME_CODE => forbidden_filename_faults(code, context),
        HELPERS_MODULE_NAME_CODE => {
            named_file_faults(code, context, HELPERS_FILE_NAME, "use an _helpers/ package")
        }
        CLASSES_MODULE_NAME_CODE => {
            named_file_faults(code, context, CLASSES_FILE_NAME, "use a classes/ package")
        }
        BANNED_GENERIC_PACKAGE_NAME_CODE => banned_package_faults(code, context),
        HELPERS_RESERVED_ROLE_FILENAMES_CODE => helpers_reserved_filename_faults(code, context),
        NESTED_DIRECT_MODULES_CODE => nested_direct_module_faults(code, context),
        NESTED_DIRECT_SUBPACKAGES_CODE => nested_direct_subpackage_faults(code, context),
        TOP_LEVEL_DIRECT_MODULES_CODE => top_level_direct_module_faults(code, context),
        HELPERS_PACKAGE_SHAPE_CODE => helpers_package_shape_faults(code, context),
        MAIN_ENTRY_NAME_COLLISION_CODE => main_entry_collision_faults(code, context),
        TOOLING_PACKAGE_LAYOUT_CODE => tooling_package_layout_faults(code, context),
        DESCRIPTIVE_RULE_MODULE_NAMES_CODE => descriptive_rule_name_faults(code, context),
        CUSTOM_RULE_TEST_COVERAGE_CODE => custom_rule_coverage_faults(code, context),
        _ => return None,
    };
    Some(faults)
}

fn banned_package_faults(code: &str, context: &NativeRuleContext) -> Vec<NativeFaultRow> {
    if context.scope != ROOT_SCOPE {
        return Vec::new();
    }
    let directories = directories(context);
    let root = scope_root_parts(context);
    let mut faults: Vec<NativeFaultRow> = Vec::new();
    for (index, name) in directories.iter().enumerate() {
        if !FFR204_FORBIDDEN_PACKAGE_NAMES.contains(&name.as_str()) {
            continue;
        }
        let package = root
            .iter()
            .chain(directories[..=index].iter())
            .cloned()
            .collect::<Vec<_>>()
            .join("/");
        if observed_bool(
            context,
            "package_anchor",
            &package,
            &context.repository_path,
        ) {
            faults.push(path_fault(
                code,
                Some(&format!(
                    "{name}/ does not identify an owner; name the business or technical capability"
                )),
            ));
        }
    }
    faults
}

fn forbidden_filename_faults(code: &str, context: &NativeRuleContext) -> Vec<NativeFaultRow> {
    let Some(name) = path_name(context) else {
        return Vec::new();
    };
    if context.scope == TEST_SCOPE || !FFR201_FORBIDDEN_MODULE_FILENAMES.contains(&name) {
        return Vec::new();
    }
    vec![path_fault(
        code,
        Some(&format!("{name} hides the module's purpose")),
    )]
}

fn main_entry_collision_faults(code: &str, context: &NativeRuleContext) -> Vec<NativeFaultRow> {
    let path = context
        .repository_path
        .strip_suffix(PYTHON_SUFFIX)
        .unwrap_or(&context.repository_path);
    if context.is_entry_module && observed_bool(context, "is_dir", path, "") {
        vec![path_fault(
            code,
            Some("main entry name collides with package"),
        )]
    } else {
        Vec::new()
    }
}

fn tooling_package_layout_faults(code: &str, context: &NativeRuleContext) -> Vec<NativeFaultRow> {
    if context.scope != TOOLING_SCOPE || context.relative_parts.len() < TOP_LEVEL_MODULE_PARTS {
        return Vec::new();
    }
    if context.relative_parts.len() == TOP_LEVEL_MODULE_PARTS {
        let name = path_name(context).unwrap_or_default();
        if name == INIT_FILE_NAME || FFR705_ALLOWED_TOOLING_ROLE_FILES.contains(&name) {
            return Vec::new();
        }
        return vec![path_fault(
            code,
            Some("tool packages may contain only role files and role directories"),
        )];
    }
    let role = &context.relative_parts[1];
    if FFR705_ALLOWED_TOOLING_ROLE_DIRECTORIES.contains(&role.as_str()) {
        return Vec::new();
    }
    let mut package_parts = scope_root_parts(context);
    package_parts.extend(context.relative_parts[..2].iter().cloned());
    let package = package_parts.join("/");
    if observed_bool(
        context,
        "package_anchor",
        &package,
        &context.repository_path,
    ) {
        vec![path_fault(
            code,
            Some(&format!(
                "tool package child '{role}/' is not an approved role"
            )),
        )]
    } else {
        Vec::new()
    }
}

fn custom_rule_coverage_faults(code: &str, context: &NativeRuleContext) -> Vec<NativeFaultRow> {
    let minimum = context
        .thresholds
        .get(MIN_CUSTOM_RULE_TEST_CASES)
        .copied()
        .unwrap_or_default();
    if minimum == 0 || context.custom_registrations.is_empty() {
        return Vec::new();
    }
    let query = NativeProjectQuery {
        kind: "custom_rule_coverage".to_owned(),
        path: String::new(),
        argument: String::new(),
    };
    let answers = context.observation(&query);
    let mut faults: Vec<NativeFaultRow> = Vec::new();
    for (rule_code, _, _, source_path, line, column) in &context.custom_registrations {
        let matching = answers.iter().find_map(|answer| {
            let mut parts = answer.split('\0');
            (parts.next()? == rule_code).then(|| {
                (
                    parts
                        .next()
                        .unwrap_or("0")
                        .parse::<u32>()
                        .map_or(0, |count| count),
                    parts.next() == Some("true"),
                )
            })
        });
        let (count, dynamic) = matching.unwrap_or_default();
        if count >= minimum {
            continue;
        }
        let message = if dynamic {
            format!(
                "custom rule {rule_code} has associated tests with dynamically determined case \
counts; the configured minimum of {minimum} cannot be statically proven"
            )
        } else {
            format!(
                "custom rule {rule_code} has {count} statically declared test cases; at least \
{minimum} is required"
            )
        };
        faults.push(NativeFaultRow {
            code: code.to_owned(),
            line: *line,
            column: *column,
            message: Some(message),
            remediation: None,
            path: Some(source_path.clone()),
        });
    }
    faults
}

fn observed_bool(context: &NativeRuleContext, kind: &str, path: &str, argument: &str) -> bool {
    context.observation(&NativeProjectQuery {
        kind: kind.to_owned(),
        path: path.to_owned(),
        argument: argument.to_owned(),
    }) == ["true"]
}

fn scope_root_parts(context: &NativeRuleContext) -> Vec<String> {
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

fn named_file_faults(
    code: &str,
    context: &NativeRuleContext,
    file_name: &str,
    message: &str,
) -> Vec<NativeFaultRow> {
    if path_name(context) == Some(file_name) {
        vec![path_fault(code, Some(message))]
    } else {
        Vec::new()
    }
}

fn helpers_reserved_filename_faults(
    code: &str,
    context: &NativeRuleContext,
) -> Vec<NativeFaultRow> {
    let Some(name) = path_name(context) else {
        return Vec::new();
    };
    if !directories(context)
        .iter()
        .any(|part| part == HELPERS_DIRECTORY_NAME)
        || !FFR303_RESERVED_ROLE_FILENAMES.contains(&name)
    {
        return Vec::new();
    }
    vec![path_fault(
        code,
        Some(&format!(
            "reserved role filename '{name}' cannot be nested beneath {HELPERS_DIRECTORY_NAME}/"
        )),
    )]
}

fn nested_direct_module_faults(code: &str, context: &NativeRuleContext) -> Vec<NativeFaultRow> {
    let parts = &context.relative_parts;
    let Some(name) = path_name(context) else {
        return Vec::new();
    };
    if context.scope == TOOLING_SCOPE
        || parts.len() < MINIMUM_NESTED_MODULE_PARTS
        || directories(context)
            .iter()
            .any(|part| part == MAIN_DIRECTORY_NAME)
        || directories(context)
            .iter()
            .any(|part| FFR304_RECOGNIZED_ROLE_DIRECTORIES.contains(&part.as_str()))
        || name == INIT_FILE_NAME
        || FFR304_RECOGNIZED_ROLE_FILENAMES.contains(&name)
    {
        return Vec::new();
    }
    vec![path_fault(
        code,
        Some("nested packages must move support code under _helpers/"),
    )]
}

fn nested_direct_subpackage_faults(code: &str, context: &NativeRuleContext) -> Vec<NativeFaultRow> {
    let parts = &context.relative_parts;
    let package_parts = directories(context);
    if context.scope == TOOLING_SCOPE
        || parts.len() < MINIMUM_NESTED_SUBPACKAGE_PARTS
        || package_parts
            .iter()
            .any(|part| part == MAIN_DIRECTORY_NAME || part == HELPERS_DIRECTORY_NAME)
    {
        return Vec::new();
    }
    for index in TOP_LEVEL_MODULE_PARTS..package_parts.len() {
        let parent = package_parts[index - 1].as_str();
        let child = package_parts[index].as_str();
        if FFR305_RECOGNIZED_ROLE_DIRECTORIES.contains(&parent)
            || FFR305_RECOGNIZED_ROLE_DIRECTORIES.contains(&child)
        {
            continue;
        }
        return vec![path_fault(
            code,
            Some("nested packages must use explicit role boundaries"),
        )];
    }
    Vec::new()
}

fn top_level_direct_module_faults(code: &str, context: &NativeRuleContext) -> Vec<NativeFaultRow> {
    let Some(name) = path_name(context) else {
        return Vec::new();
    };
    if context.scope == TOOLING_SCOPE
        || context.relative_parts.len() != TOP_LEVEL_MODULE_PARTS
        || name == INIT_FILE_NAME
        || FFR307_RECOGNIZED_ROLE_FILENAMES.contains(&name)
    {
        return Vec::new();
    }
    vec![path_fault(
        code,
        Some("top-level domains must not contain ad hoc direct modules"),
    )]
}

fn helpers_package_shape_faults(code: &str, context: &NativeRuleContext) -> Vec<NativeFaultRow> {
    if !directories(context)
        .iter()
        .any(|part| part == HELPERS_DIRECTORY_NAME)
        || path_name(context) != Some(MAIN_FILE_NAME)
    {
        return Vec::new();
    }
    vec![path_fault(
        code,
        Some("_helpers/ packages must not contain main.py orchestration"),
    )]
}

fn descriptive_rule_name_faults(code: &str, context: &NativeRuleContext) -> Vec<NativeFaultRow> {
    let Some(name) = path_name(context) else {
        return Vec::new();
    };
    let stem = name
        .strip_suffix(PYTHON_SUFFIX)
        .unwrap_or(name)
        .to_uppercase();
    if context.role.as_deref() != Some(RULES_ROLE) || !is_rule_code(&stem) {
        return Vec::new();
    }
    vec![path_fault(
        code,
        Some("rule module filenames must describe their policy, not repeat a rule code"),
    )]
}

fn directories(context: &NativeRuleContext) -> &[String] {
    &context.relative_parts[..context.relative_parts.len().saturating_sub(1)]
}
