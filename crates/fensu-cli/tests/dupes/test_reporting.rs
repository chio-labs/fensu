use crate::helpers::{
    audited_summary, cluster_members, git, json_report, ranked_files, remove_files, run_dupes,
    spaced_summaries, summary, text, write, write_files, PYTHON_CONFIG, PYTHON_EXTRA,
    PYTHON_UNRELATED,
};
use crate::test_types::{ChangedSinceTestCase, CommandOutputTestCase, JsonShapeTestCase};

#[test]
fn given_clone_findings_when_rendering_text_then_output_is_advisory_ranked_and_exits_zero() {
    let test_cases = [
        CommandOutputTestCase {
            description: "clusters rank by duplicated tokens and the heading is advisory",
            config: PYTHON_CONFIG.to_owned(),
            files: ranked_files(),
            arguments: &[],
            expected_exit_code: 0,
            expected_stdout: &[
                "fensu dupes: 2 duplicated-code clusters (advisory; duplicated-code findings to review, not fensu check failures)\n",
                "analysed python 5 units; 0 allowlisted pairs hidden; 0 contract-exempt members hidden\n",
                "  1. exact sim 1.00, ~",
                " duplicated tokens, 3 members\n     src/shop/billing/summary.py:1-15 summarize_orders (",
                "  2. exact sim 1.00, ~",
                "     src/shop/inventory/restock.py:1-12 restock_products (",
            ],
            expected_stderr: &["fensu dupes: found 2 duplicated-code clusters across 5 units in "],
        },
        CommandOutputTestCase {
            description: "top limits printed clusters and points at the remainder",
            config: PYTHON_CONFIG.to_owned(),
            files: ranked_files(),
            arguments: &["--top", "1"],
            expected_exit_code: 0,
            expected_stdout: &["  1. exact sim 1.00", "... 1 more clusters (use --top)\n"],
            expected_stderr: &["(advisory)"],
        },
        CommandOutputTestCase {
            description: "path filter keeps clusters with a matching member",
            config: PYTHON_CONFIG.to_owned(),
            files: ranked_files(),
            arguments: &["--path", "src/shop/warehouse/*"],
            expected_exit_code: 0,
            expected_stdout: &["fensu dupes: 1 duplicated-code cluster (", "restock_products"],
            expected_stderr: &[],
        },
        CommandOutputTestCase {
            description: "language filter excludes other languages",
            config: PYTHON_CONFIG.to_owned(),
            files: ranked_files(),
            arguments: &["--lang", "rust"],
            expected_exit_code: 0,
            expected_stdout: &["fensu dupes: 0 duplicated-code clusters (", "analysed no units;", "no duplicated code found\n"],
            expected_stderr: &[],
        },
        CommandOutputTestCase {
            description: "min tokens above every unit reports nothing",
            config: PYTHON_CONFIG.to_owned(),
            files: ranked_files(),
            arguments: &["--min-tokens", "500"],
            expected_exit_code: 0,
            expected_stdout: &["no duplicated code found\n"],
            expected_stderr: &[],
        },
        CommandOutputTestCase {
            description: "diff shows where near-miss copies diverge",
            config: PYTHON_CONFIG.to_owned(),
            files: vec![
                ("src/shop/orders/summary.py", summary("")),
                ("src/shop/reports/summary.py", summary(PYTHON_EXTRA)),
            ],
            arguments: &["--diff"],
            expected_exit_code: 0,
            expected_stdout: &[
                "  1. near-miss sim 0.9",
                "     diff src/shop/orders/summary.py:1-15 vs src/shop/reports/summary.py:1-16\n       + 9: log_progress(count)\n",
            ],
            expected_stderr: &[],
        },
        CommandOutputTestCase {
            description: "diff of exact copies reports no differing lines",
            config: PYTHON_CONFIG.to_owned(),
            files: ranked_files(),
            arguments: &["--diff", "--top", "1"],
            expected_exit_code: 0,
            expected_stdout: &["     diff src/shop/billing/summary.py:1-15 vs src/shop/orders/summary.py:1-15: no differing lines\n"],
            expected_stderr: &[],
        },
    ];
    for test_case in &test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        write(repository.path().join("fensu.toml"), &test_case.config);
        write_files(repository.path(), &test_case.files);

        let output = run_dupes(repository.path(), test_case.arguments);
        let stdout = text(&output.stdout);
        let stderr = text(&output.stderr);

        assert_eq!(
            output.status.code(),
            Some(test_case.expected_exit_code),
            "{}: {stderr}",
            test_case.description
        );
        assert!(
            test_case
                .expected_stdout
                .iter()
                .all(|fragment| stdout.contains(fragment)),
            "{}: {stdout}",
            test_case.description
        );
        assert!(
            test_case
                .expected_stderr
                .iter()
                .all(|fragment| stderr.contains(fragment)),
            "{}: {stderr}",
            test_case.description
        );
    }
}

#[test]
fn given_json_output_when_reporting_then_shape_is_stable() {
    let test_cases = [JsonShapeTestCase {
        description: "report, cluster, member, and diff fields",
        arguments: &["--json", "--diff"],
        expected_report_keys: &[
            "command",
            "advisory",
            "since",
            "unit_counts",
            "allowlisted_pairs",
            "contract_exempt_members",
            "total_clusters",
            "clusters",
        ],
        expected_cluster_keys: &[
            "rank",
            "category",
            "similarity_min",
            "similarity_max",
            "duplicated_tokens",
            "members",
            "links",
            "diff",
        ],
        expected_member_keys: &[
            "language",
            "path",
            "name",
            "start_line",
            "end_line",
            "tokens",
            "changed",
            "forced",
        ],
        expected_diff_lines: &[(1, 9, "log_progress(count)")],
    }];
    for test_case in &test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        write(repository.path().join("fensu.toml"), PYTHON_CONFIG);
        write_files(
            repository.path(),
            &[
                ("src/shop/orders/summary.py", summary("")),
                ("src/shop/reports/summary.py", summary(PYTHON_EXTRA)),
            ],
        );

        let output = run_dupes(repository.path(), test_case.arguments);
        let report = json_report(&output);
        let keys = |value: &serde_json::Value| {
            value
                .as_object()
                .expect("JSON object")
                .keys()
                .cloned()
                .collect::<Vec<_>>()
        };
        let cluster = &report["clusters"][0];
        let diff_lines = cluster["diff"]["lines"]
            .as_array()
            .expect("diff lines")
            .iter()
            .map(|line| {
                (
                    line["member"].as_u64().expect("member"),
                    line["line"].as_u64().expect("line"),
                    line["text"].as_str().expect("text").to_owned(),
                )
            })
            .collect::<Vec<_>>();
        let expected_diff_lines = test_case
            .expected_diff_lines
            .iter()
            .map(|(member, line, text)| (*member, *line, (*text).to_owned()))
            .collect::<Vec<_>>();

        assert_eq!(output.status.code(), Some(0), "{}", test_case.description);
        assert_eq!(
            keys(&report),
            test_case.expected_report_keys,
            "{}",
            test_case.description
        );
        assert_eq!(
            keys(cluster),
            test_case.expected_cluster_keys,
            "{}",
            test_case.description
        );
        assert_eq!(
            keys(&cluster["members"][0]),
            test_case.expected_member_keys,
            "{}",
            test_case.description
        );
        assert_eq!(
            report["advisory"],
            serde_json::Value::Bool(true),
            "{}",
            test_case.description
        );
        assert_eq!(
            report["unit_counts"]["python"],
            serde_json::json!(2),
            "{}",
            test_case.description
        );
        assert_eq!(diff_lines, expected_diff_lines, "{}", test_case.description);
    }
}

#[test]
fn given_git_changes_when_filtering_since_revision_then_only_touched_clusters_remain() {
    let test_cases = [
        ChangedSinceTestCase {
            description: "no changes report no clusters",
            committed: ranked_files(),
            removed: &[],
            staged: vec![],
            worktree: vec![],
            expected_clusters: vec![],
        },
        ChangedSinceTestCase {
            description: "an uncommitted edit inside one member marks that cluster",
            committed: ranked_files(),
            removed: &[],
            staged: vec![],
            worktree: vec![(
                "src/shop/warehouse/restock.py",
                PYTHON_UNRELATED.replace(
                    "        pending = [",
                    "        # audited\n        pending = [",
                ),
            )],
            expected_clusters: vec![vec![
                "src/shop/inventory/restock.py",
                "src/shop/warehouse/restock.py [changed]",
            ]],
        },
        ChangedSinceTestCase {
            description: "an untracked copy marks the cluster it joins",
            committed: ranked_files(),
            removed: &[],
            staged: vec![],
            worktree: vec![("src/shop/exports/summary.py", summary(""))],
            expected_clusters: vec![vec![
                "src/shop/billing/summary.py",
                "src/shop/exports/summary.py [changed]",
                "src/shop/orders/summary.py",
                "src/shop/reports/summary.py",
            ]],
        },
        ChangedSinceTestCase {
            description: "a tracked edit in a path with a space marks that member",
            committed: spaced_summaries(),
            removed: &[],
            staged: vec![],
            worktree: vec![("src/shop/order copies/summary.py", audited_summary())],
            expected_clusters: vec![vec![
                "src/shop/order copies/summary.py [changed]",
                "src/shop/orders/summary.py",
            ]],
        },
        ChangedSinceTestCase {
            description: "a renamed and edited copy between spaced paths is marked",
            committed: vec![
                ("src/shop/orders/summary.py", summary("")),
                ("src/shop/old name/summary.py", summary("")),
            ],
            removed: &["src/shop/old name/summary.py"],
            staged: vec![("src/shop/new name/summary.py", audited_summary())],
            worktree: vec![],
            expected_clusters: vec![vec![
                "src/shop/new name/summary.py [changed]",
                "src/shop/orders/summary.py",
            ]],
        },
        ChangedSinceTestCase {
            description: "a tracked edit in a non-ASCII path marks that member",
            committed: vec![
                ("src/shop/orders/summary.py", summary("")),
                ("src/shop/bücher/summary.py", summary("")),
            ],
            removed: &[],
            staged: vec![],
            worktree: vec![("src/shop/bücher/summary.py", audited_summary())],
            expected_clusters: vec![vec![
                "src/shop/bücher/summary.py [changed]",
                "src/shop/orders/summary.py",
            ]],
        },
        ChangedSinceTestCase {
            description: "an untracked copy in a path with a space is marked",
            committed: vec![("src/shop/orders/summary.py", summary(""))],
            removed: &[],
            staged: vec![],
            worktree: vec![("src/shop/new copy/summary.py", summary(""))],
            expected_clusters: vec![vec![
                "src/shop/new copy/summary.py [changed]",
                "src/shop/orders/summary.py",
            ]],
        },
    ];
    for test_case in &test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        write(repository.path().join("fensu.toml"), PYTHON_CONFIG);
        write_files(repository.path(), &test_case.committed);
        git(repository.path(), &["init", "--quiet"]);
        git(repository.path(), &["add", "."]);
        git(
            repository.path(),
            &["commit", "--quiet", "-m", "seed orders"],
        );
        remove_files(repository.path(), test_case.removed);
        write_files(repository.path(), &test_case.staged);
        git(repository.path(), &["add", "--all"]);
        write_files(repository.path(), &test_case.worktree);

        let output = run_dupes(repository.path(), &["--json", "--since", "HEAD"]);
        let report = json_report(&output);

        assert_eq!(
            output.status.code(),
            Some(0),
            "{}: {}",
            test_case.description,
            text(&output.stderr)
        );
        assert_eq!(
            report["since"],
            serde_json::json!("HEAD"),
            "{}",
            test_case.description
        );
        assert_eq!(
            cluster_members(&report),
            test_case.expected_clusters,
            "{}",
            test_case.description
        );
    }
}
