//! Winnowed k-gram fingerprints (MOSS style) with CRC-32 tokens and CPython tuple hashes.

use std::collections::BTreeSet;

use crate::dupes::constants::{KGRAM_SIZE, WINNOW_WINDOW};

const CRC_POLYNOMIAL: u32 = 0xedb8_8320;
const PRIME_1: u64 = 11_400_714_785_074_694_791;
const PRIME_2: u64 = 14_029_467_366_897_019_727;
const PRIME_5: u64 = 2_870_177_450_012_600_261;
const LENGTH_SALT: u64 = 3_527_539;
const RESERVED_HASH: i64 = -1;
const RESERVED_REPLACEMENT: i64 = 1_546_275_796;

/// Return the CRC-32 identifier of one normalised token's UTF-8 text.
pub(crate) fn token_identifier(text: &str) -> u32 {
    let mut crc = u32::MAX;
    for byte in text.bytes() {
        crc ^= u32::from(byte);
        for _ in 0..8 {
            let mask = (crc & 1).wrapping_neg();
            crc = (crc >> 1) ^ (CRC_POLYNOMIAL & mask);
        }
    }
    !crc
}

/// Select the minimum k-gram hash of every window of consecutive k-grams.
pub(crate) fn fingerprint_tokens(identifiers: &[u32]) -> BTreeSet<i64> {
    if identifiers.len() < KGRAM_SIZE {
        return BTreeSet::new();
    }
    let hashes: Vec<i64> = identifiers.windows(KGRAM_SIZE).map(hash_gram).collect();
    if hashes.len() <= WINNOW_WINDOW {
        return hashes.iter().min().copied().into_iter().collect();
    }
    hashes
        .windows(WINNOW_WINDOW)
        .filter_map(|window| window.iter().min().copied())
        .collect()
}

fn hash_gram(gram: &[u32]) -> i64 {
    let mut accumulator = PRIME_5;
    for identifier in gram {
        accumulator = accumulator.wrapping_add(u64::from(*identifier).wrapping_mul(PRIME_2));
        accumulator = accumulator.rotate_left(31).wrapping_mul(PRIME_1);
    }
    accumulator = accumulator.wrapping_add(gram.len() as u64 ^ (PRIME_5 ^ LENGTH_SALT));
    let signed = i64::from_ne_bytes(accumulator.to_ne_bytes());
    if signed == RESERVED_HASH {
        RESERVED_REPLACEMENT
    } else {
        signed
    }
}
