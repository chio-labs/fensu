//! A port of `difflib.SequenceMatcher` without junk heuristics (`autojunk=False`).

use std::collections::HashMap;

/// One maximal equal run: `left[left_start..left_start + size] == right[right_start..]`.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct MatchingBlock {
    pub(crate) left_start: usize,
    pub(crate) right_start: usize,
    pub(crate) size: usize,
}

/// Return `2 * matches / (len(left) + len(right))`, as `SequenceMatcher.ratio()` does.
pub(crate) fn ratio(left: &[u32], right: &[u32]) -> f64 {
    let total = left.len() + right.len();
    if total == 0 {
        return 1.0;
    }
    let matched: usize = matching_blocks(left, right)
        .iter()
        .map(|block| block.size)
        .sum();
    to_f64(2 * matched) / to_f64(total)
}

/// Return the non-overlapping matching blocks in increasing order, like `get_matching_blocks`.
pub(crate) fn matching_blocks(left: &[u32], right: &[u32]) -> Vec<MatchingBlock> {
    let mut positions: HashMap<u32, Vec<usize>> = HashMap::new();
    for (index, token) in right.iter().enumerate() {
        positions.entry(*token).or_default().push(index);
    }
    let mut finder = LongestMatch {
        left,
        positions: &positions,
        lengths: vec![0; right.len() + 1],
        next_lengths: vec![0; right.len() + 1],
        touched: Vec::new(),
        next_touched: Vec::new(),
    };
    let mut pending = vec![(0, left.len(), 0, right.len())];
    let mut blocks: Vec<MatchingBlock> = Vec::new();
    while let Some((left_low, left_high, right_low, right_high)) = pending.pop() {
        let block = finder.find(left_low, left_high, right_low, right_high);
        if block.size == 0 {
            continue;
        }
        if left_low < block.left_start && right_low < block.right_start {
            pending.push((left_low, block.left_start, right_low, block.right_start));
        }
        let left_end = block.left_start + block.size;
        let right_end = block.right_start + block.size;
        if left_end < left_high && right_end < right_high {
            pending.push((left_end, left_high, right_end, right_high));
        }
        blocks.push(block);
    }
    blocks.sort_by_key(|block| (block.left_start, block.right_start));
    merge_adjacent(blocks)
}

fn merge_adjacent(blocks: Vec<MatchingBlock>) -> Vec<MatchingBlock> {
    let mut merged: Vec<MatchingBlock> = Vec::with_capacity(blocks.len());
    for block in blocks {
        if let Some(last) = merged.last_mut() {
            if last.left_start + last.size == block.left_start
                && last.right_start + last.size == block.right_start
            {
                last.size += block.size;
                continue;
            }
        }
        merged.push(block);
    }
    merged
}

struct LongestMatch<'a> {
    left: &'a [u32],
    positions: &'a HashMap<u32, Vec<usize>>,
    lengths: Vec<usize>,
    next_lengths: Vec<usize>,
    touched: Vec<usize>,
    next_touched: Vec<usize>,
}

impl LongestMatch<'_> {
    /// Find the longest equal run, preferring the earliest start in `left`, then in `right`.
    fn find(
        &mut self,
        left_low: usize,
        left_high: usize,
        right_low: usize,
        right_high: usize,
    ) -> MatchingBlock {
        let mut best = MatchingBlock {
            left_start: left_low,
            right_start: right_low,
            size: 0,
        };
        for left_index in left_low..left_high {
            if let Some(indexes) = self.positions.get(&self.left[left_index]) {
                for &right_index in indexes {
                    if right_index < right_low {
                        continue;
                    }
                    if right_index >= right_high {
                        break;
                    }
                    let size = if right_index == 0 {
                        1
                    } else {
                        self.lengths[right_index] + 1
                    };
                    self.next_lengths[right_index + 1] = size;
                    self.next_touched.push(right_index + 1);
                    if size > best.size {
                        best = MatchingBlock {
                            left_start: left_index + 1 - size,
                            right_start: right_index + 1 - size,
                            size,
                        };
                    }
                }
            }
            for slot in self.touched.drain(..) {
                self.lengths[slot] = 0;
            }
            std::mem::swap(&mut self.lengths, &mut self.next_lengths);
            std::mem::swap(&mut self.touched, &mut self.next_touched);
        }
        for slot in self.touched.drain(..) {
            self.lengths[slot] = 0;
        }
        best
    }
}

pub(crate) const fn to_f64(value: usize) -> f64 {
    value as f64
}
