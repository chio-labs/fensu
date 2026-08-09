use std::collections::{HashMap, HashSet};
use std::path::Path;

use crate::models::{Config, Fault, RuleException, ScopedSource};

type ExceptionKey = (String, String, Option<String>);

pub(crate) struct ApplyExceptionsRequest<'a> {
    pub(crate) faults: Vec<Fault>,
    pub(crate) sources: &'a [ScopedSource],
    pub(crate) project_root: &'a Path,
    pub(crate) evaluated_codes: &'a HashSet<&'a str>,
    pub(crate) config: &'a Config,
}

pub(crate) fn apply_exceptions(
    request: ApplyExceptionsRequest<'_>,
) -> Result<(Vec<Fault>, usize), String> {
    let ApplyExceptionsRequest {
        faults,
        sources,
        project_root,
        evaluated_codes,
        config,
    } = request;
    if config.exceptions.is_empty() {
        return Ok((faults, 0));
    }
    let source_by_path = sources
        .iter()
        .map(|source| (source.target_path.as_str(), source))
        .collect::<HashMap<_, _>>();
    let mut applied: HashSet<ExceptionKey> = HashSet::new();
    let mut retained: Vec<Fault> = Vec::new();
    for fault in faults {
        let reported = repository_path(&fault.path, project_root);
        let mut owner: Option<String> = None;
        let mut matching = None;
        for entry in &config.exceptions {
            if entry.rule != fault.code || entry.path != reported {
                continue;
            }
            if entry.symbols.is_empty() {
                matching = Some(entry);
                break;
            }
            if owner.is_none() {
                owner = source_by_path
                    .get(reported.as_str())
                    .and_then(|source| fault_owner(&fault, source));
            }
            if owner
                .as_ref()
                .is_some_and(|symbol| entry.symbols.iter().any(|item| item == symbol))
            {
                matching = Some(entry);
                break;
            }
        }
        if let Some(entry) = matching {
            let symbol = (!entry.symbols.is_empty()).then(|| owner.clone()).flatten();
            applied.insert((entry.rule.clone(), entry.path.clone(), symbol));
        } else {
            retained.push(fault);
        }
    }
    if let Some(message) = stale_exception(config, evaluated_codes, &applied) {
        return Err(message);
    }
    Ok((retained, applied.len()))
}

fn repository_path(reported: &str, root: &Path) -> String {
    let candidate = Path::new(reported);
    candidate
        .strip_prefix(root)
        .unwrap_or(candidate)
        .to_string_lossy()
        .replace('\\', "/")
        .trim_start_matches('/')
        .to_owned()
}

fn stale_exception(
    config: &Config,
    evaluated_codes: &HashSet<&str>,
    applied: &HashSet<ExceptionKey>,
) -> Option<String> {
    for entry in &config.exceptions {
        if !evaluated_codes.contains(entry.rule.as_str()) {
            continue;
        }
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

fn configured_symbols(entry: &RuleException) -> Vec<Option<String>> {
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
