//! Extract, filter, and intern function-level units for every discovered source.

use std::collections::hash_map::DefaultHasher;
use std::collections::HashMap;
use std::hash::{Hash, Hasher};

use rayon::iter::{IntoParallelRefIterator, ParallelIterator};

use crate::dupes::_helpers::matching::fingerprints::token_identifier;
use crate::dupes::_helpers::units::python::extract_python_units;
use crate::dupes::_helpers::units::rust::extract_rust_units;
use crate::dupes::_helpers::units::web::{extract_script_units, extract_svelte_units};
use crate::dupes::constants::{LANGUAGE_PYTHON, LANGUAGE_RUST, LANGUAGE_SVELTE};
use crate::dupes::models::{CloneUnit, DupesSource, ExtractedUnit, RustFileUnits};

struct SourceUnits<'s> {
    source: &'s DupesSource,
    extracted: RustFileUnits,
}

/// Return units of at least `min_tokens` normalised tokens in deterministic path order.
pub(crate) fn collect_units(
    sources: &[DupesSource],
    include_tests: bool,
    min_tokens: usize,
) -> Vec<CloneUnit> {
    let extracted: Vec<SourceUnits<'_>> = sources
        .par_iter()
        .map(|source| SourceUnits {
            source,
            extracted: extract_source(source, include_tests),
        })
        .collect();
    let test_prefixes: Vec<&String> = extracted
        .iter()
        .flat_map(|file| &file.extracted.test_module_prefixes)
        .collect();
    let mut interner = Interner::default();
    let mut units: Vec<CloneUnit> = Vec::new();
    for file in &extracted {
        let path = &file.source.repository_path;
        if test_prefixes
            .iter()
            .any(|prefix| path.starts_with(prefix.as_str()))
        {
            continue;
        }
        for unit in &file.extracted.units {
            if unit.normalized.len() >= min_tokens {
                units.push(interner.unit(file.source, unit));
            }
        }
    }
    units
}

fn extract_source(source: &DupesSource, include_tests: bool) -> RustFileUnits {
    let text = String::from_utf8_lossy(&source.content);
    match source.language {
        LANGUAGE_PYTHON => RustFileUnits {
            units: extract_python_units(&text),
            test_module_prefixes: Vec::new(),
        },
        LANGUAGE_RUST => extract_rust_units(&source.repository_path, &text, include_tests),
        LANGUAGE_SVELTE => RustFileUnits {
            units: extract_svelte_units(&text),
            test_module_prefixes: Vec::new(),
        },
        _ => RustFileUnits {
            units: extract_script_units(&source.path, &text),
            test_module_prefixes: Vec::new(),
        },
    }
}

#[derive(Default)]
struct Interner {
    identifiers: HashMap<String, u32>,
}

impl Interner {
    fn unit(&mut self, source: &DupesSource, unit: &ExtractedUnit) -> CloneUnit {
        let tokens: Vec<u32> = unit
            .normalized
            .iter()
            .map(|text| self.identifier(text))
            .collect();
        let fingerprint_ids: Vec<u32> = unit
            .normalized
            .iter()
            .map(|text| token_identifier(text))
            .collect();
        let mut hasher = DefaultHasher::new();
        unit.concrete.hash(&mut hasher);
        CloneUnit {
            language: source.language,
            path: source.repository_path.clone(),
            name: unit.name.clone(),
            start_line: unit.start_line,
            end_line: unit.end_line,
            tokens,
            fingerprint_ids,
            concrete_key: hasher.finish(),
        }
    }

    fn identifier(&mut self, text: &str) -> u32 {
        if let Some(identifier) = self.identifiers.get(text) {
            return *identifier;
        }
        let identifier = u32::try_from(self.identifiers.len()).unwrap_or(u32::MAX);
        self.identifiers.insert(text.to_owned(), identifier);
        identifier
    }
}
