//! Project-owned reachability faults consumed by both check hosts.

use fensu_facts::dead_code::main::analyze::analyze;
use fensu_facts::dead_code::models::{Module, ProjectEntryPoint, Root};

use crate::rules::constants::{DEAD_DEFINITION_CODE, DEAD_MODULE_CODE, STALE_DEAD_CODE_ROOT_CODE};
use crate::rules::models::{NativeDeadCodeContext, NativeFaultRow, NativeProjectPlane};

const TEST_SCOPE: &str = "test";
const INIT_FILE: &str = "__init__.py";

pub(crate) fn faults(
    codes: &[String],
    context: &NativeDeadCodeContext,
    project: &NativeProjectPlane,
) -> Vec<NativeFaultRow> {
    if !context.enabled
        || !codes
            .iter()
            .any(|code| matches!(code.as_str(), "FFL106" | "FFL107" | "FFL108"))
    {
        return Vec::new();
    }
    let production = project
        .modules
        .iter()
        .filter(|module| module.scope != TEST_SCOPE && module.path.ends_with(".py"))
        .collect::<Vec<_>>();
    let modules = production
        .iter()
        .map(|module| {
            let initializer = module.path.ends_with("/__init__.py") || module.path == INIT_FILE;
            Module {
                name: module.module_parts.join("."),
                program: module.program.clone(),
                package: initializer && module.module_parts.len() == 1,
                initializer,
            }
        })
        .collect::<Vec<_>>();
    let roots = context
        .roots
        .iter()
        .map(|(modules, symbols)| Root {
            modules: modules.clone(),
            symbols: symbols.clone(),
        })
        .collect::<Vec<_>>();
    let entries = context
        .entrypoints
        .iter()
        .map(|(kind, reference)| ProjectEntryPoint {
            kind: kind.clone(),
            reference: reference.clone(),
        })
        .collect::<Vec<_>>();
    let analysis = analyze(&modules, &entries, &roots);
    let mut faults: Vec<NativeFaultRow> = Vec::new();
    if codes.iter().any(|code| code == STALE_DEAD_CODE_ROOT_CODE) {
        for index in analysis.stale_roots {
            faults.push(NativeFaultRow {
                code: STALE_DEAD_CODE_ROOT_CODE.to_owned(),
                line: 1,
                column: 0,
                message: Some(format!("dead_code.roots entry {} matches no existing production declaration", index + 1)),
                remediation: Some("Remove or correct the stale configured root; matching does not depend on current reachability.".to_owned()),
                path: Some(context.config_path.clone()),
            });
        }
    }
    for declaration in analysis.dead {
        let code = if declaration.name.is_empty() {
            DEAD_MODULE_CODE
        } else {
            DEAD_DEFINITION_CODE
        };
        if !codes.iter().any(|selected| selected == code) {
            continue;
        }
        let separator = if declaration.name.is_empty() { "" } else { "." };
        faults.push(NativeFaultRow {
            code: code.to_owned(),
            line: declaration.line,
            column: declaration.column,
            message: Some(format!("unreachable {} {}{separator}{}", declaration.kind, modules[declaration.module].name, declaration.name)),
            remediation: Some("Investigate the production entry mechanism before deleting code. Export an intentional public API or configure a reasoned root for dynamic dispatch.".to_owned()),
            path: Some(production[declaration.module].path.clone()),
        });
    }
    faults
}
