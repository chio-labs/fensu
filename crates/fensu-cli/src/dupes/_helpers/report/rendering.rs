//! Render duplicated-code reports as concise text or deterministic JSON.

use serde_json::{json, Map, Value};

use crate::dupes::constants::TEXT_MAX_MEMBERS;
use crate::dupes::models::{CloneCluster, CloneMember, DupesReport, MemberDiff};

const INDENT: &str = "     ";
const DIFF_INDENT: &str = "       ";
const ADVISORY: &str = "advisory; duplicated-code findings to review, not fensu check failures";

pub(crate) fn render_text(report: &DupesReport, top: usize) -> String {
    let scope = report
        .since
        .as_ref()
        .map_or_else(String::new, |revision| format!(" changed since {revision}"));
    let mut lines = vec![
        format!(
            "fensu dupes: {} duplicated-code cluster{}{scope} ({ADVISORY})",
            report.clusters.len(),
            if report.clusters.len() == 1 { "" } else { "s" },
        ),
        summary_line(report),
    ];
    for (position, cluster) in report.clusters.iter().take(top).enumerate() {
        lines.push(format!("{:3}. {}", position + 1, cluster_heading(cluster)));
        let shown = cluster.members.len().min(TEXT_MAX_MEMBERS);
        lines.extend(
            cluster.members[..shown]
                .iter()
                .map(|member| format!("{INDENT}{}", member_line(member))),
        );
        if cluster.members.len() > shown {
            lines.push(format!(
                "{INDENT}... {} more members (see --json)",
                cluster.members.len() - shown
            ));
        }
        if let Some(diff) = &cluster.diff {
            lines.extend(diff_text(cluster, diff));
        }
    }
    if report.clusters.is_empty() {
        lines.push("no duplicated code found".to_owned());
    } else if report.clusters.len() > top {
        lines.push(format!(
            "... {} more clusters (use --top)",
            report.clusters.len() - top
        ));
    }
    let mut text = lines.join("\n");
    text.push('\n');
    text
}

pub(crate) fn render_json(report: &DupesReport, top: usize) -> Result<String, String> {
    let clusters = report
        .clusters
        .iter()
        .take(top)
        .enumerate()
        .map(|(position, cluster)| {
            let mut entry = Map::new();
            entry.insert("rank".to_owned(), json!(position + 1));
            if let Value::Object(fields) =
                serde_json::to_value(cluster).map_err(|error| error.to_string())?
            {
                entry.extend(fields);
            }
            Ok(Value::Object(entry))
        })
        .collect::<Result<Vec<_>, String>>()?;
    let payload = json!({
        "command": "dupes",
        "advisory": true,
        "since": report.since,
        "unit_counts": report.unit_counts,
        "allowlisted_pairs": report.allowlisted_pairs,
        "contract_exempt_members": report.contract_exempt_members,
        "total_clusters": report.clusters.len(),
        "clusters": clusters,
    });
    let mut text = serde_json::to_string_pretty(&payload).map_err(|error| error.to_string())?;
    text.push('\n');
    Ok(text)
}

fn summary_line(report: &DupesReport) -> String {
    let counts: Vec<String> = report
        .unit_counts
        .iter()
        .filter(|(_, count)| **count > 0)
        .map(|(language, count)| format!("{language} {count} units"))
        .collect();
    format!(
        "analysed {}; {} allowlisted pairs hidden; {} contract-exempt members hidden",
        if counts.is_empty() {
            "no units".to_owned()
        } else {
            counts.join(", ")
        },
        report.allowlisted_pairs,
        report.contract_exempt_members,
    )
}

fn cluster_heading(cluster: &CloneCluster) -> String {
    let lowest = format!("{:.2}", cluster.similarity_min);
    let highest = format!("{:.2}", cluster.similarity_max);
    let similarity = if lowest == highest {
        highest
    } else {
        format!("{lowest}-{highest}")
    };
    format!(
        "{} sim {similarity}, ~{} duplicated tokens, {} members",
        cluster.category,
        cluster.duplicated_tokens,
        cluster.members.len()
    )
}

fn member_line(member: &CloneMember) -> String {
    format!(
        "{}:{}-{} {} ({} tokens){}{}",
        member.path,
        member.start_line,
        member.end_line,
        member.name,
        member.tokens,
        if member.forced { " [forced]" } else { "" },
        if member.changed { " [changed]" } else { "" },
    )
}

fn member_location(member: &CloneMember) -> String {
    format!("{}:{}-{}", member.path, member.start_line, member.end_line)
}

fn diff_text(cluster: &CloneCluster, diff: &MemberDiff) -> Vec<String> {
    let (left, right) = (&cluster.members[diff.left], &cluster.members[diff.right]);
    let mut lines = vec![format!(
        "{INDENT}diff {} vs {}{}",
        member_location(left),
        member_location(right),
        if diff.identical {
            ": no differing lines"
        } else {
            ""
        }
    )];
    lines.extend(diff.lines.iter().map(|line| {
        let marker = if line.member == diff.left { '-' } else { '+' };
        format!("{DIFF_INDENT}{marker} {}: {}", line.line, line.text)
    }));
    if diff.omitted_lines > 0 {
        lines.push(format!(
            "{DIFF_INDENT}... {} more differing lines",
            diff.omitted_lines
        ));
    }
    lines
}
