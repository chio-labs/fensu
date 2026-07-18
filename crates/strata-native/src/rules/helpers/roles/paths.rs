//! File-local role policy decided entirely from Python-owned position data.

use crate::rules::constants::{
    BANNED_GENERIC_FILENAME_CODE, CLASSES_MODULE_NAME_CODE, DESCRIPTIVE_RULE_MODULE_NAMES_CODE,
    HELPERS_MODULE_NAME_CODE, HELPERS_PACKAGE_SHAPE_CODE, HELPERS_RESERVED_ROLE_FILENAMES_CODE,
    NESTED_DIRECT_MODULES_CODE, NESTED_DIRECT_SUBPACKAGES_CODE, TOP_LEVEL_DIRECT_MODULES_CODE,
};
use crate::rules::models::{NativeFaultRow, NativeRuleContext};

use crate::rules::helpers::roles::{path_fault, path_name};

const CLASSES_FILE_NAME: &str = "classes.py";
const CORE_RULE_CODE_LENGTH: usize = 6;
const HELPERS_DIRECTORY_NAME: &str = "_helpers";
const HELPERS_FILE_NAME: &str = "helpers.py";
const INIT_FILE_NAME: &str = "__init__.py";
const MAIN_DIRECTORY_NAME: &str = "main";
const MAIN_FILE_NAME: &str = "main.py";
const MINIMUM_NESTED_MODULE_PARTS: usize = 3;
const MINIMUM_NESTED_SUBPACKAGE_PARTS: usize = 4;
const MISC_FILE_NAME: &str = "misc.py";
const PYTHON_SUFFIX: &str = ".py";
const RULES_ROLE: &str = "rules";
const TOOLING_SCOPE: &str = "tooling";
const TOP_LEVEL_MODULE_PARTS: usize = 2;
const ROLE_NAMES: &[&str] = &[
    MAIN_DIRECTORY_NAME,
    HELPERS_DIRECTORY_NAME,
    "classes",
    "models",
    "types",
    "constants",
    "exceptions",
];
const ROLE_FILE_NAMES: &[&str] = &[
    MAIN_FILE_NAME,
    HELPERS_FILE_NAME,
    CLASSES_FILE_NAME,
    "models.py",
    "types.py",
    "constants.py",
    "exceptions.py",
];
const RESERVED_ROLE_FILE_NAMES: &[&str] =
    &["models.py", "types.py", "constants.py", "exceptions.py"];

pub(crate) fn path_faults(code: &str, context: &NativeRuleContext) -> Option<Vec<NativeFaultRow>> {
    let faults = match code {
        BANNED_GENERIC_FILENAME_CODE => named_file_faults(
            code,
            context,
            MISC_FILE_NAME,
            "misc.py hides the module's purpose",
        ),
        HELPERS_MODULE_NAME_CODE => {
            named_file_faults(code, context, HELPERS_FILE_NAME, "use an _helpers/ package")
        }
        CLASSES_MODULE_NAME_CODE => {
            named_file_faults(code, context, CLASSES_FILE_NAME, "use a classes/ package")
        }
        HELPERS_RESERVED_ROLE_FILENAMES_CODE => helpers_reserved_filename_faults(code, context),
        NESTED_DIRECT_MODULES_CODE => nested_direct_module_faults(code, context),
        NESTED_DIRECT_SUBPACKAGES_CODE => nested_direct_subpackage_faults(code, context),
        TOP_LEVEL_DIRECT_MODULES_CODE => top_level_direct_module_faults(code, context),
        HELPERS_PACKAGE_SHAPE_CODE => helpers_package_shape_faults(code, context),
        DESCRIPTIVE_RULE_MODULE_NAMES_CODE => descriptive_rule_name_faults(code, context),
        _ => return None,
    };
    Some(faults)
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
        || !RESERVED_ROLE_FILE_NAMES.contains(&name)
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
            .any(|part| ROLE_NAMES.contains(&part.as_str()))
        || name == INIT_FILE_NAME
        || ROLE_FILE_NAMES.contains(&name)
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
        if ROLE_NAMES.contains(&parent) || ROLE_NAMES.contains(&child) {
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
        || ROLE_FILE_NAMES.contains(&name)
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

fn is_rule_code(value: &str) -> bool {
    let bytes = value.as_bytes();
    let core = bytes.len() == CORE_RULE_CODE_LENGTH
        && bytes.starts_with(b"SF")
        && bytes[2].is_ascii_uppercase()
        && bytes[3..].iter().all(u8::is_ascii_digit);
    let custom = bytes.first() == Some(&b'X')
        && bytes.len() >= TOP_LEVEL_MODULE_PARTS
        && bytes[1..]
            .iter()
            .all(|byte| byte.is_ascii_uppercase() || byte.is_ascii_digit())
        && bytes[1..].iter().any(u8::is_ascii_digit)
        && bytes[1..]
            .iter()
            .skip_while(|byte| byte.is_ascii_uppercase())
            .all(u8::is_ascii_digit);
    core || custom
}
