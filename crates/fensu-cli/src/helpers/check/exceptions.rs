use std::collections::{HashMap, HashSet};

use crate::models::{Config, Fault, ScopedSource};

type ExceptionKey = (String, String, Option<String>);

pub(crate) fn apply_exceptions(
    faults: Vec<Fault>,
    sources: &[ScopedSource],
    config: &Config,
) -> Result<(Vec<Fault>, usize), String> {
    if config.exceptions.is_empty() {
        return Ok((faults, 0));
    }
    let source_by_path = sources
        .iter()
        .map(|source| (source.path.to_string_lossy().replace('\\', "/"), source))
        .collect::<HashMap<_, _>>();
    let mut applied: HashSet<ExceptionKey> = HashSet::new();
    let retained = faults
        .into_iter()
        .filter(|fault| {
            let path = fault.path.replace('\\', "/");
            let mut owner: Option<Option<String>> = None;
            let matching = config.exceptions.iter().find(|entry| {
                if entry.rule != fault.code || !path.ends_with(&entry.path) {
                    return false;
                }
                if entry.symbols.is_empty() {
                    return true;
                }
                let resolved = owner.get_or_insert_with(|| {
                    source_by_path
                        .get(&path)
                        .and_then(|source| fault_owner(fault, source))
                });
                resolved
                    .as_deref()
                    .is_some_and(|symbol| entry.symbols.iter().any(|item| item == symbol))
            });
            match matching {
                Some(entry) => {
                    let symbol = if entry.symbols.is_empty() {
                        None
                    } else {
                        owner.clone().flatten()
                    };
                    applied.insert((entry.rule.clone(), entry.path.clone(), symbol));
                    false
                }
                None => true,
            }
        })
        .collect::<Vec<_>>();
    if let Some(message) = stale_exception(config, &applied) {
        return Err(message);
    }
    Ok((retained, applied.len()))
}

fn stale_exception(config: &Config, applied: &HashSet<ExceptionKey>) -> Option<String> {
    for entry in &config.exceptions {
        for symbol in configured_symbols(entry) {
            let key = (entry.rule.clone(), entry.path.clone(), symbol.clone());
            if applied.contains(&key) {
                continue;
            }
            let suffix = symbol.map_or_else(String::new, |value| format!("::{value}"));
            return Some(format!(
                "Rule exception no longer matches a fault: {} {}{suffix}. Remove it or update its scope. Reason: {}",
                entry.rule, entry.path, entry.reason
            ));
        }
    }
    None
}

fn configured_symbols(entry: &crate::models::RuleException) -> Vec<Option<String>> {
    if entry.symbols.is_empty() {
        return vec![None];
    }
    entry
        .symbols
        .iter()
        .map(|symbol| Some(symbol.clone()))
        .collect()
}

fn fault_owner(fault: &Fault, source: &ScopedSource) -> Option<String> {
    source
        .program
        .as_ref()?
        .owner_symbol_at(fault.line?, fault.column.unwrap_or(0))
}
