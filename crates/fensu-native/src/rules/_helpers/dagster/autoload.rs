use std::collections::HashSet;

use fensu_facts::extension::models::ProgramHandle;
use fensu_facts::facts::models::{ImportRow, RuleNamedCallRow};

use crate::rules::_helpers::dagster::{
    fault, file_name, has_decorator, module_name, top_level_functions,
};
use crate::rules::constants::DAGSTER_AUTOLOAD_EXTERNAL_DISCOVERY_CODE;
use crate::rules::models::{
    NativeFaultRow, NativeProjectModule, NativeProjectPlane, NativeRuleContext,
};

const DEFINITIONS_ROLE: &str = "defs";
const SCRIPT_FILE: &str = "_script.py";

fn approved_boundaries(context: &NativeRuleContext) -> Result<HashSet<String>, String> {
    let Some(raw) = context.option(
        DAGSTER_AUTOLOAD_EXTERNAL_DISCOVERY_CODE,
        "approved_loader_boundaries",
    ) else {
        return Ok(HashSet::new());
    };
    serde_json::from_str::<Vec<String>>(raw)
        .map(|values| values.into_iter().collect())
        .map_err(|error| format!("Invalid approved_loader_boundaries option: {error}"))
}

fn definitions_providers(program: &ProgramHandle) -> Vec<(String, u32)> {
    top_level_functions(program)
        .into_iter()
        .filter(|row| has_decorator(program, row.line, &["definitions"]))
        .map(|row| (row.name.clone(), row.line))
        .collect()
}

fn absolute_call_parts(call: &RuleNamedCallRow, imports: &[ImportRow]) -> Vec<String> {
    let parts = &call.reference.parts;
    let Some(first) = parts.first() else {
        return Vec::new();
    };
    for row in imports {
        for alias in &row.aliases {
            if &alias.bound_name != first {
                continue;
            }
            let mut resolved: Vec<String> = if row.from_import {
                row.module_parts.clone()
            } else {
                Vec::new()
            };
            resolved.extend(alias.imported_name.split('.').map(str::to_owned));
            resolved.extend(parts.iter().skip(1).cloned());
            return resolved;
        }
    }
    parts.clone()
}

fn external_sink(parts: &[String]) -> bool {
    let joined = parts.join(".");
    [
        "subprocess.",
        "requests.",
        "httpx.",
        "aiohttp.",
        "urllib.request.",
        "boto3.",
        "paramiko.",
        "fabric.",
        "redis.",
        "pymongo.",
        "sqlalchemy.create_engine",
        "sqlalchemy.ext.asyncio.create_async_engine",
        "os.system",
        "os.popen",
        "socket.",
    ]
    .iter()
    .any(|prefix| joined.starts_with(prefix))
        || (matches!(
            parts.last().map(String::as_str),
            Some("connect" | "create_pool")
        ) && !parts.is_empty()
            && matches!(
                parts[0].as_str(),
                "asyncpg"
                    | "duckdb"
                    | "ibis"
                    | "oracledb"
                    | "psycopg"
                    | "psycopg2"
                    | "pyodbc"
                    | "pymssql"
                    | "pymysql"
                    | "redshift_connector"
                    | "snowflake"
                    | "sqlite3"
            ))
}

fn module_by_name<'a>(
    project: &'a NativeProjectPlane,
    name: &str,
) -> Option<&'a NativeProjectModule> {
    project
        .modules
        .iter()
        .find(|module| module.module_parts.join(".") == name)
}

struct DiscoveryWalk<'a> {
    code: &'a str,
    package: &'a str,
    approved: &'a HashSet<String>,
    project: &'a NativeProjectPlane,
}

struct DiscoveryState {
    visited: HashSet<String>,
    faults: Vec<NativeFaultRow>,
}

fn walk_calls(
    walk: &DiscoveryWalk<'_>,
    module: &NativeProjectModule,
    calls: Vec<&RuleNamedCallRow>,
    mut state: DiscoveryState,
) -> DiscoveryState {
    let current_module = module.module_parts.join(".");
    for call in calls {
        let parts = absolute_call_parts(call, &module.program.reference_rows().imports);
        if external_sink(&parts) {
            let mut row = fault(walk.code, call.line, call.column);
            row.path = Some(module.path.clone());
            state.faults.push(row);
            continue;
        }
        let (target_module_name, function_name) = match parts.as_slice() {
            [] => continue,
            [function_name] => (current_module.clone(), function_name.clone()),
            _ => (
                parts[..parts.len() - 1].join("."),
                parts.last().cloned().unwrap_or_default(),
            ),
        };
        if !target_module_name.starts_with(walk.package) {
            continue;
        }
        let identity = format!("{target_module_name}.{function_name}");
        if walk.approved.contains(&identity) || !state.visited.insert(identity) {
            continue;
        }
        let Some(target_module) = module_by_name(walk.project, &target_module_name) else {
            continue;
        };
        let target_calls: Vec<&RuleNamedCallRow> = target_module
            .program
            .named_call_rows()
            .iter()
            .filter(|candidate| {
                candidate
                    .owning_function
                    .as_ref()
                    .is_some_and(|owner| owner.name == function_name)
            })
            .collect();
        state = walk_calls(walk, target_module, target_calls, state);
    }
    state
}

pub(super) fn autoload_external_discovery(
    program: &ProgramHandle,
    code: &str,
    context: &NativeRuleContext,
    project: &NativeProjectPlane,
) -> Result<Vec<NativeFaultRow>, String> {
    if !context
        .relative_parts
        .starts_with(&[DEFINITIONS_ROLE.to_owned()])
        || file_name(context) == SCRIPT_FILE
    {
        return Ok(Vec::new());
    }
    let approved = approved_boundaries(context)?;
    let current_name = module_name(context);
    let Some(current) = module_by_name(project, &current_name).or_else(|| {
        project
            .modules
            .iter()
            .find(|module| module.path == context.repository_path)
    }) else {
        let mut faults: Vec<NativeFaultRow> = program
            .named_call_rows()
            .iter()
            .filter(|call| call.owning_function.is_none())
            .filter(|call| {
                external_sink(&absolute_call_parts(
                    call,
                    &program.reference_rows().imports,
                ))
            })
            .map(|call| fault(code, call.line, call.column))
            .collect();
        faults.sort_by_key(|item| (item.line, item.column));
        return Ok(faults);
    };
    let mut calls: Vec<&RuleNamedCallRow> = program
        .named_call_rows()
        .iter()
        .filter(|call| call.owning_function.is_none())
        .collect();
    let providers = definitions_providers(program);
    calls.extend(
        program
            .named_call_rows()
            .iter()
            .filter(|call| owned_by_provider(call, &providers)),
    );
    let walk = DiscoveryWalk {
        code,
        package: &context.package_name,
        approved: &approved,
        project,
    };
    let state = DiscoveryState {
        visited: providers
            .into_iter()
            .map(|(name, _)| format!("{current_name}.{name}"))
            .collect(),
        faults: Vec::new(),
    };
    let mut faults = walk_calls(&walk, current, calls, state).faults;
    faults.sort_by(|left, right| {
        (&left.path, left.line, left.column).cmp(&(&right.path, right.line, right.column))
    });
    faults.dedup_by(|left, right| {
        left.path == right.path && left.line == right.line && left.column == right.column
    });
    Ok(faults)
}

fn owned_by_provider(call: &RuleNamedCallRow, providers: &[(String, u32)]) -> bool {
    let Some(owner) = &call.owning_function else {
        return false;
    };
    providers
        .iter()
        .any(|(name, line)| name == &owner.name && *line == owner.line)
}
