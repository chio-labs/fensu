use std::collections::{HashMap, HashSet};
use std::path::Path;

use crate::models::{Config, Fault, RuleException, ScopedSource};

type ExceptionKey = (String, String, Option<String>);

struct FaultOwner {
    identities: Vec<String>,
}

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
        let mut owner: Option<FaultOwner> = None;
        let mut matched_symbol: Option<String> = None;
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
            matched_symbol = owner.as_ref().and_then(|owner| {
                entry
                    .symbols
                    .iter()
                    .find(|symbol| owner.identities.contains(symbol))
                    .cloned()
            });
            if matched_symbol.is_some() {
                matching = Some(entry);
                break;
            }
        }
        if let Some(entry) = matching {
            let symbol = (!entry.symbols.is_empty())
                .then(|| matched_symbol.clone())
                .flatten();
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

fn fault_owner(fault: &Fault, source: &ScopedSource) -> Option<FaultOwner> {
    let program = source.program.as_ref()?;
    if let Some(program) = program.as_python() {
        return program
            .owner_symbol_at(fault.line?, fault.column.unwrap_or(0))
            .map(|symbol| FaultOwner {
                identities: vec![symbol],
            });
    }
    web_fault_owner(
        source,
        fault.line? as usize,
        fault.column.unwrap_or(0) as usize,
    )
}

fn web_fault_owner(source: &ScopedSource, line: usize, column: usize) -> Option<FaultOwner> {
    let offset = source_offset(&source.content, line, column)?;
    let mut candidates: Vec<(usize, Vec<String>)> = Vec::new();
    let facts = match source.program.as_ref()? {
        crate::models::ParsedProgram::TypeScript(facts) => vec![facts.as_ref()],
        crate::models::ParsedProgram::Svelte(facts) => {
            facts.scripts.iter().map(|script| &script.facts).collect()
        }
        crate::models::ParsedProgram::Python(_) | crate::models::ParsedProgram::Malformed(_) => {
            Vec::new()
        }
    };
    for facts in facts {
        for item in &facts.functions {
            if let Some(length) = span_owner(&item.span, offset) {
                let mut identities = vec![item.qualified_name.clone()];
                if item.qualified_name != item.name {
                    identities.push(item.name.clone());
                }
                candidates.push((length, identities));
            }
        }
        for item in &facts.classes {
            if let Some(length) = span_owner(&item.span, offset) {
                candidates.push((length, vec![item.name.clone()]));
            }
        }
        for item in &facts.models {
            if let Some(length) = span_owner(&item.span, offset) {
                candidates.push((length, vec![item.name.clone()]));
            }
        }
    }
    candidates.sort();
    let (length, identities) = candidates.first()?.clone();
    let ambiguous = candidates
        .iter()
        .skip(1)
        .take_while(|(candidate_length, _)| *candidate_length == length)
        .any(|(_, candidate)| candidate != &identities);
    (!ambiguous).then_some(FaultOwner { identities })
}

fn span_owner(span: &fensu_typescript::SourceSpan, offset: usize) -> Option<usize> {
    (span.start <= offset && offset < span.end).then_some(span.end.saturating_sub(span.start))
}

fn source_offset(source: &[u8], line: usize, column: usize) -> Option<usize> {
    if line == 0 {
        return None;
    }
    let mut current_line = 1;
    let mut line_start = 0;
    for (index, byte) in source.iter().enumerate() {
        if current_line == line {
            return Some((line_start + column).min(source.len()));
        }
        if *byte == b'\n' {
            current_line += 1;
            line_start = index + 1;
        }
    }
    (current_line == line).then_some((line_start + column).min(source.len()))
}
