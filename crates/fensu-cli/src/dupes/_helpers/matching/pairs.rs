//! Find similar unit pairs from identical streams and shared fingerprints.

use std::collections::{BTreeMap, BTreeSet, HashMap};

use rayon::iter::{IntoParallelRefIterator, ParallelIterator};

use crate::dupes::_helpers::matching::fingerprints::fingerprint_tokens;
use crate::dupes::_helpers::matching::sequence::{ratio, to_f64};
use crate::dupes::constants::{
    CANDIDATE_MIN_JACCARD, LANGUAGE_PYTHON, LANGUAGE_RUST, MAX_FINGERPRINT_UNITS, MIN_FINGERPRINTS,
    SIMILARITY_DECIMALS, SMALL_NEAR_MISS_MIN_SIMILARITY, SMALL_NEAR_MISS_TOKENS,
};
use crate::dupes::models::{Category, ClonePair, CloneUnit};

const MIN_POSTING_UNITS: usize = 2;

/// Return identical-stream pairs plus near-miss pairs at or above the similarity threshold.
pub(crate) fn find_clone_pairs(units: &[CloneUnit], min_similarity: f64) -> Vec<ClonePair> {
    let mut pairs: BTreeMap<(usize, usize), ClonePair> = BTreeMap::new();
    for (left, right) in identical_stream_pairs(units) {
        let category = if units[left].concrete_key == units[right].concrete_key {
            Category::Exact
        } else {
            Category::Renamed
        };
        pairs.insert(
            (left, right),
            ClonePair {
                left,
                right,
                similarity: 1.0,
                category,
            },
        );
    }
    let candidates: Vec<(usize, usize)> = candidate_pairs(units)
        .into_iter()
        .filter(|key| !pairs.contains_key(key))
        .collect();
    let near_misses: Vec<ClonePair> = candidates
        .par_iter()
        .filter_map(|&(left, right)| near_miss(units, left, right, min_similarity))
        .collect();
    for pair in near_misses {
        pairs.insert((pair.left, pair.right), pair);
    }
    pairs.into_values().collect()
}

/// Group languages that can share copied code: all web languages compare with each other.
pub(crate) fn language_family(language: &str) -> &'static str {
    match language {
        LANGUAGE_PYTHON => LANGUAGE_PYTHON,
        LANGUAGE_RUST => LANGUAGE_RUST,
        _ => "web",
    }
}

fn near_miss(
    units: &[CloneUnit],
    left: usize,
    right: usize,
    min_similarity: f64,
) -> Option<ClonePair> {
    let (left_tokens, right_tokens) = (&units[left].tokens, &units[right].tokens);
    let smaller = left_tokens.len().min(right_tokens.len());
    let larger = left_tokens.len().max(right_tokens.len());
    let required = if smaller < SMALL_NEAR_MISS_TOKENS {
        min_similarity.max(SMALL_NEAR_MISS_MIN_SIMILARITY)
    } else {
        min_similarity
    };
    if to_f64(2 * smaller) / to_f64(smaller + larger) < required {
        return None;
    }
    let similarity = ratio(left_tokens, right_tokens);
    (similarity >= required).then(|| ClonePair {
        left,
        right,
        similarity: (similarity * SIMILARITY_DECIMALS).round() / SIMILARITY_DECIMALS,
        category: Category::NearMiss,
    })
}

fn identical_stream_pairs(units: &[CloneUnit]) -> Vec<(usize, usize)> {
    let mut groups: HashMap<(&str, &[u32]), Vec<usize>> = HashMap::new();
    for (index, unit) in units.iter().enumerate() {
        groups
            .entry((language_family(unit.language), unit.tokens.as_slice()))
            .or_default()
            .push(index);
    }
    let mut identical: Vec<(usize, usize)> = Vec::new();
    for members in groups.values() {
        for (position, left) in members.iter().enumerate() {
            identical.extend(members[position + 1..].iter().map(|right| (*left, *right)));
        }
    }
    identical
}

fn candidate_pairs(units: &[CloneUnit]) -> Vec<(usize, usize)> {
    let fingerprints: Vec<BTreeSet<i64>> = units
        .par_iter()
        .map(|unit| fingerprint_tokens(&unit.fingerprint_ids))
        .collect();
    let mut postings: HashMap<i64, Vec<usize>> = HashMap::new();
    for (index, unit_fingerprints) in fingerprints.iter().enumerate() {
        for fingerprint in unit_fingerprints {
            postings.entry(*fingerprint).or_default().push(index);
        }
    }
    let distinctive: Vec<usize> = fingerprints
        .iter()
        .map(|unit_fingerprints| distinctive_count(unit_fingerprints, &postings))
        .collect();
    let mut shared: HashMap<(usize, usize), usize> = HashMap::new();
    for members in postings.values() {
        if members.len() < MIN_POSTING_UNITS || members.len() > MAX_FINGERPRINT_UNITS {
            continue;
        }
        for (position, left) in members.iter().enumerate() {
            for right in &members[position + 1..] {
                *shared.entry((*left, *right)).or_default() += 1;
            }
        }
    }
    let mut candidates: Vec<(usize, usize)> = shared
        .into_iter()
        .filter(|&((left, right), count)| {
            let (left_size, right_size) = (distinctive[left], distinctive[right]);
            language_family(units[left].language) == language_family(units[right].language)
                && left_size.min(right_size) >= MIN_FINGERPRINTS
                && to_f64(count) / to_f64(left_size + right_size - count) >= CANDIDATE_MIN_JACCARD
        })
        .map(|(key, _)| key)
        .collect();
    candidates.sort_unstable();
    candidates
}

/// Count fingerprints shared by few enough units to be distinctive rather than boilerplate.
fn distinctive_count(fingerprints: &BTreeSet<i64>, postings: &HashMap<i64, Vec<usize>>) -> usize {
    fingerprints
        .iter()
        .filter(|fingerprint| postings[fingerprint].len() <= MAX_FINGERPRINT_UNITS)
        .count()
}
