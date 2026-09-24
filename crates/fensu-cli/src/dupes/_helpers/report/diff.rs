//! Bounded line diffs showing where the first two visible cluster members diverge.

use std::collections::HashMap;

use crate::dupes::_helpers::matching::sequence::{matching_blocks, MatchingBlock};
use crate::dupes::constants::DIFF_MAX_LINES;
use crate::dupes::models::{CloneCluster, CloneMember, DiffLine, MemberDiff};

/// Diff the first two members; forced members sort last, so these are visible when possible.
pub(crate) fn member_diff(
    cluster: &CloneCluster,
    sources: &HashMap<&str, &[u8]>,
) -> Option<MemberDiff> {
    let [left, right] = [0, 1].map(|slot| cluster.members.get(slot));
    let (left, right) = (left?, right?);
    let left_lines = member_lines(left, sources)?;
    let right_lines = member_lines(right, sources)?;
    let (left_ids, right_ids) = line_ids(&left_lines, &right_lines);
    let mut differing: Vec<DiffLine> = Vec::new();
    let (mut left_cursor, mut right_cursor) = (0, 0);
    let mut blocks = matching_blocks(&left_ids, &right_ids);
    blocks.push(MatchingBlock {
        left_start: left_ids.len(),
        right_start: right_ids.len(),
        size: 0,
    });
    for block in blocks {
        differing.extend(diff_lines(0, &left_lines[left_cursor..block.left_start]));
        differing.extend(diff_lines(1, &right_lines[right_cursor..block.right_start]));
        left_cursor = block.left_start + block.size;
        right_cursor = block.right_start + block.size;
    }
    let omitted_lines = differing.len().saturating_sub(DIFF_MAX_LINES);
    differing.truncate(DIFF_MAX_LINES);
    Some(MemberDiff {
        left: 0,
        right: 1,
        identical: differing.is_empty(),
        lines: differing,
        omitted_lines,
    })
}

/// Number equal line texts identically across both members.
fn line_ids(left: &[(usize, String)], right: &[(usize, String)]) -> (Vec<u32>, Vec<u32>) {
    let mut interner: HashMap<&str, u32> = HashMap::new();
    let mut ids: Vec<u32> = Vec::with_capacity(left.len() + right.len());
    for (_, text) in left.iter().chain(right) {
        let next = u32::try_from(interner.len()).unwrap_or(u32::MAX);
        ids.push(*interner.entry(text.as_str()).or_insert(next));
    }
    let right_ids = ids.split_off(left.len());
    (ids, right_ids)
}

fn diff_lines(member: usize, lines: &[(usize, String)]) -> Vec<DiffLine> {
    lines
        .iter()
        .map(|(line, text)| DiffLine {
            member,
            line: *line,
            text: text.clone(),
        })
        .collect()
}

/// Return the member's non-blank lines, trimmed so indentation changes do not count.
fn member_lines(
    member: &CloneMember,
    sources: &HashMap<&str, &[u8]>,
) -> Option<Vec<(usize, String)>> {
    let content = String::from_utf8_lossy(sources.get(member.path.as_str())?);
    Some(
        content
            .lines()
            .enumerate()
            .map(|(index, text)| (index + 1, text.trim()))
            .filter(|(line, text)| {
                (member.start_line..=member.end_line).contains(line) && !text.is_empty()
            })
            .map(|(line, text)| (line, text.to_owned()))
            .collect(),
    )
}
