//! Project import-graph policy for public main entries.

use std::collections::{BTreeMap, HashSet};

use strata_facts::facts::models::ImportRow;

use crate::rules::helpers::layers::{classify, normalized_targets, shares_domain, Ownership};
use crate::rules::models::{NativeFaultRow, NativeProjectPlane};

const INIT_FILE: &str = "__init__.py";
const MAIN_ROLE: &str = "main";
const PYTHON_SUFFIX: &str = ".py";
const ROOT_SCOPE: &str = "root";

pub(crate) fn public_entry_faults(code: &str, project: &NativeProjectPlane) -> Vec<NativeFaultRow> {
    let mut entries: BTreeMap<Vec<String>, (&str, Ownership)> = BTreeMap::new();
    for module in &project.modules {
        let initializer = module.path.ends_with(&format!("/{INIT_FILE}"));
        let ownership = classify(&module.module_parts, initializer);
        if module.scope == ROOT_SCOPE
            && module.path.ends_with(PYTHON_SUFFIX)
            && !initializer
            && ownership.domain.is_some()
            && public_main_entry(&ownership)
        {
            entries.insert(module.module_parts.clone(), (&module.path, ownership));
        }
    }
    let mut used: HashSet<Vec<String>> = project
        .entrypoint_modules
        .iter()
        .map(|name| name.split('.').map(str::to_owned).collect())
        .collect();
    for importer in &project.modules {
        let initializer = importer.path.ends_with(&format!("/{INIT_FILE}"));
        let importer_owner = classify(&importer.module_parts, initializer);
        for row in &importer.program.reference_rows().imports {
            for target in import_module_targets(row, &importer.module_parts, initializer) {
                let Some((_, target_owner)) = entries.get(&target) else {
                    continue;
                };
                if importer.scope != ROOT_SCOPE || !shares_domain(&importer_owner, target_owner) {
                    used.insert(target);
                }
            }
        }
    }
    entries
        .into_iter()
        .filter(|(parts, _)| !used.contains(parts))
        .map(|(_, (path, _))| NativeFaultRow {
            code: code.to_owned(),
            line: 0,
            column: 0,
            message: Some("public main entry has no importer outside its owning domain".to_owned()),
            remediation: None,
            path: Some(path.to_owned()),
        })
        .collect()
}

fn public_main_entry(ownership: &Ownership) -> bool {
    ownership.first_role.as_deref() == Some(MAIN_ROLE)
        && ownership
            .tail
            .last()
            .is_some_and(|name| !name.starts_with('_'))
}

fn import_module_targets(
    row: &ImportRow,
    current_parts: &[String],
    current_initializer: bool,
) -> Vec<Vec<String>> {
    let bases = normalized_targets(row, current_parts, current_initializer);
    let mut targets = bases.clone();
    if row.from_import {
        for base in bases {
            for alias in &row.aliases {
                let mut target = base.clone();
                target.extend(alias.imported_name.split('.').map(str::to_owned));
                if !targets.contains(&target) {
                    targets.push(target);
                }
            }
        }
    }
    targets
}
