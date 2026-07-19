//! File-local role policy over cached module declaration rows.

use fensu_facts::extension::models::ProgramHandle;
use fensu_facts::facts::models::{ModuleDeclarationRows, ModuleStatementRow};

use crate::rules::constants::{
    CONSTANTS_ONLY_CONSTANTS_CODE, CONSTANT_OUTSIDE_CONSTANTS_CODE,
    EXCEPTIONS_ONLY_EXCEPTIONS_CODE, EXCEPTION_DECLARATION_OUTSIDE_EXCEPTIONS_CODE,
    HELPERS_CLASSES_FILE_PRIVATE_CODE, MODELS_ONLY_MODELS_CODE,
    MODEL_DECLARATION_OUTSIDE_MODELS_CODE, NO_INTERNAL_HELPER_EXPORTS_CODE,
    PRIVATE_DEFINITION_ORDERING_CODE, RULES_ROLE_CONTENT_CODE, TYPES_ONLY_TYPES_CODE,
    TYPE_DECLARATION_OUTSIDE_TYPES_CODE,
};
use crate::rules::models::{NativeFaultRow, NativeRuleContext};

use crate::rules::helpers::roles::{location_fault, location_rows, path_name};

const CONSTANTS_ROLE: &str = "constants";
const EXCEPTIONS_ROLE: &str = "exceptions";
const HELPERS_ROLE: &str = "helpers";
const INIT_FILE_NAME: &str = "__init__.py";
const MODELS_ROLE: &str = "models";
const RULES_ROLE: &str = "rules";
const TOOLING_SCOPE: &str = "tooling";
const TYPES_ROLE: &str = "types";

pub(crate) fn declaration_faults(
    program: &ProgramHandle,
    code: &str,
    context: &NativeRuleContext,
) -> Option<Vec<NativeFaultRow>> {
    if !matches!(
        code,
        MODELS_ONLY_MODELS_CODE
            | TYPES_ONLY_TYPES_CODE
            | CONSTANTS_ONLY_CONSTANTS_CODE
            | EXCEPTIONS_ONLY_EXCEPTIONS_CODE
            | MODEL_DECLARATION_OUTSIDE_MODELS_CODE
            | TYPE_DECLARATION_OUTSIDE_TYPES_CODE
            | CONSTANT_OUTSIDE_CONSTANTS_CODE
            | EXCEPTION_DECLARATION_OUTSIDE_EXCEPTIONS_CODE
            | HELPERS_CLASSES_FILE_PRIVATE_CODE
            | NO_INTERNAL_HELPER_EXPORTS_CODE
            | PRIVATE_DEFINITION_ORDERING_CODE
            | RULES_ROLE_CONTENT_CODE
    ) {
        return None;
    }
    let declarations = program.declaration_rows();
    let faults = match code {
        MODELS_ONLY_MODELS_CODE => {
            role_content_faults(code, context, declarations, MODELS_ROLE, |row| {
                row.import_statement || row.model_class
            })
        }
        TYPES_ONLY_TYPES_CODE => {
            role_content_faults(code, context, declarations, TYPES_ROLE, |row| {
                row.import_statement
                    || row.assignment_statement
                    || row.explicit_type_alias
                    || row.type_checking_import_block
                    || row.type_class
            })
        }
        CONSTANTS_ONLY_CONSTANTS_CODE => {
            role_content_faults(code, context, declarations, CONSTANTS_ROLE, |row| {
                row.import_statement || row.assignment_statement
            })
        }
        EXCEPTIONS_ONLY_EXCEPTIONS_CODE => {
            role_content_faults(code, context, declarations, EXCEPTIONS_ROLE, |row| {
                row.import_statement || row.exception_class
            })
        }
        MODEL_DECLARATION_OUTSIDE_MODELS_CODE => {
            outside_role_locations(code, context, MODELS_ROLE, &declarations.model_locations)
        }
        TYPE_DECLARATION_OUTSIDE_TYPES_CODE => declarations
            .type_declarations
            .iter()
            .filter(|row| {
                context.role.as_deref() != Some(TYPES_ROLE)
                    && (!row.private || context.role.as_deref() != Some(HELPERS_ROLE))
            })
            .map(|row| location_fault(code, row.line, row.column, None))
            .collect(),
        CONSTANT_OUTSIDE_CONSTANTS_CODE => {
            constant_outside_role_faults(code, context, declarations)
        }
        EXCEPTION_DECLARATION_OUTSIDE_EXCEPTIONS_CODE => outside_role_locations(
            code,
            context,
            EXCEPTIONS_ROLE,
            &declarations.exception_locations,
        ),
        HELPERS_CLASSES_FILE_PRIVATE_CODE => helper_class_faults(code, context, declarations),
        NO_INTERNAL_HELPER_EXPORTS_CODE => {
            if context.role.as_deref() == Some(HELPERS_ROLE) {
                location_rows(code, &declarations.all_assignment_locations)
            } else {
                Vec::new()
            }
        }
        PRIVATE_DEFINITION_ORDERING_CODE => private_definition_faults(code, declarations),
        RULES_ROLE_CONTENT_CODE => rules_role_faults(code, context, declarations),
        _ => return None,
    };
    Some(faults)
}

fn role_content_faults<Allowed>(
    code: &str,
    context: &NativeRuleContext,
    declarations: &ModuleDeclarationRows,
    role: &str,
    allowed: Allowed,
) -> Vec<NativeFaultRow>
where
    Allowed: Fn(&ModuleStatementRow) -> bool,
{
    if context.role.as_deref() != Some(role) {
        return Vec::new();
    }
    declarations
        .statements
        .iter()
        .filter(|row| !allowed(row))
        .map(|row| location_fault(code, row.line, row.column, None))
        .collect()
}

fn outside_role_locations(
    code: &str,
    context: &NativeRuleContext,
    role: &str,
    locations: &[(u32, u32)],
) -> Vec<NativeFaultRow> {
    if context.role.as_deref() == Some(role) {
        Vec::new()
    } else {
        location_rows(code, locations)
    }
}

fn constant_outside_role_faults(
    code: &str,
    context: &NativeRuleContext,
    declarations: &ModuleDeclarationRows,
) -> Vec<NativeFaultRow> {
    if context.role.as_deref() == Some(CONSTANTS_ROLE) {
        return Vec::new();
    }
    declarations
        .statements
        .iter()
        .flat_map(|row| {
            row.assignment_target_names
                .iter()
                .filter(|name| !name.starts_with('_') && uppercase_constant(name))
                .map(|_| location_fault(code, row.line, row.column, None))
        })
        .collect()
}

fn helper_class_faults(
    code: &str,
    context: &NativeRuleContext,
    declarations: &ModuleDeclarationRows,
) -> Vec<NativeFaultRow> {
    if context.role.as_deref() != Some(HELPERS_ROLE) {
        return Vec::new();
    }
    declarations
        .statements
        .iter()
        .filter(|row| {
            row.class_name
                .as_ref()
                .is_some_and(|name| !name.starts_with('_'))
                && !row.model_class
                && !row.type_class
        })
        .map(|row| location_fault(code, row.line, row.column, None))
        .collect()
}

fn private_definition_faults(
    code: &str,
    declarations: &ModuleDeclarationRows,
) -> Vec<NativeFaultRow> {
    let mut faults = Vec::new();
    let mut saw_function = false;
    for row in &declarations.statements {
        if row.function_name.is_some() {
            saw_function = true;
            continue;
        }
        if !saw_function {
            continue;
        }
        let message = if row
            .class_name
            .as_ref()
            .is_some_and(|name| name.starts_with('_'))
            && row.dataclass_class
        {
            Some("private dataclasses must appear before top-level functions")
        } else if row
            .assignment_target_names
            .iter()
            .any(|name| name.starts_with('_'))
        {
            Some("private constants must appear before top-level functions")
        } else {
            None
        };
        if let Some(message) = message {
            faults.push(location_fault(code, row.line, row.column, Some(message)));
        }
    }
    faults
}

fn rules_role_faults(
    code: &str,
    context: &NativeRuleContext,
    declarations: &ModuleDeclarationRows,
) -> Vec<NativeFaultRow> {
    if context.scope != TOOLING_SCOPE
        || context.role.as_deref() != Some(RULES_ROLE)
        || path_name(context) == Some(INIT_FILE_NAME)
    {
        return Vec::new();
    }
    declarations
        .statements
        .iter()
        .filter(|row| {
            !row.import_statement && !row.type_checking_import_block && !row.rule_decorated_function
        })
        .map(|row| {
            location_fault(
                code,
                row.line,
                row.column,
                Some("rules/ modules may contain only imports and @rule functions"),
            )
        })
        .collect()
}

fn uppercase_constant(name: &str) -> bool {
    let mut saw_cased = false;
    for character in name.chars() {
        if character.is_lowercase() {
            return false;
        }
        saw_cased |= character.is_uppercase();
    }
    saw_cased
}
