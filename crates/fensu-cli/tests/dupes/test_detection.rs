use crate::helpers::{
    json_report, links, run_dupes, rust_original, seeded, summary, svelte_component, text,
    typescript_original, without_types, write, write_files, JAVASCRIPT_RENAMED, PYTHON_CALLS,
    PYTHON_CONFIG, PYTHON_EXTRA, PYTHON_OTHER_CALLS, PYTHON_RENAMED, PYTHON_SHORT, PYTHON_TEMPLATE,
    PYTHON_UNRELATED, RUST_CONFIG, RUST_EXTRA, RUST_RENAMED, RUST_SHORT, RUST_TEMPLATE,
    RUST_UNRELATED, SVELTE_CONFIG, TYPESCRIPT_CONFIG, TYPESCRIPT_EXTRA, TYPESCRIPT_SHORT,
    TYPESCRIPT_TEMPLATE, TYPESCRIPT_UNRELATED, WEB_CALLS, WEB_OTHER_CALLS,
};
use crate::test_types::DetectionTestCase;

#[test]
fn given_seeded_clones_per_language_when_running_dupes_then_categories_and_exclusions_hold() {
    let test_cases = [
        DetectionTestCase {
            description: "python exact, renamed, near-miss, and call-target variants",
            config: PYTHON_CONFIG,
            files: vec![
                ("src/shop/orders/summary.py", summary("")),
                ("src/shop/billing/summary.py", summary("")),
                ("src/shop/customers/summary.py", PYTHON_RENAMED.to_owned()),
                (
                    "src/shop/reports/summary.py",
                    seeded(
                        PYTHON_TEMPLATE,
                        "summarize_orders",
                        PYTHON_EXTRA,
                        PYTHON_CALLS,
                    ),
                ),
                (
                    "src/shop/exports/summary.py",
                    seeded(PYTHON_TEMPLATE, "summarize_orders", "", PYTHON_OTHER_CALLS),
                ),
                ("src/shop/inventory/restock.py", PYTHON_UNRELATED.to_owned()),
                ("src/shop/orders/shipping.py", PYTHON_SHORT.to_owned()),
                ("src/shop/billing/shipping.py", PYTHON_SHORT.to_owned()),
                ("tests/test_summary.py", summary("")),
            ],
            expected_links: &[
                (
                    "src/shop/billing/summary.py",
                    "src/shop/orders/summary.py",
                    "exact",
                ),
                (
                    "src/shop/customers/summary.py",
                    "src/shop/orders/summary.py",
                    "renamed",
                ),
                (
                    "src/shop/exports/summary.py",
                    "src/shop/orders/summary.py",
                    "near-miss",
                ),
                (
                    "src/shop/orders/summary.py",
                    "src/shop/reports/summary.py",
                    "near-miss",
                ),
            ],
            expected_absent: &[
                "src/shop/inventory/restock.py",
                "src/shop/orders/shipping.py",
                "src/shop/billing/shipping.py",
                "tests/test_summary.py",
            ],
        },
        DetectionTestCase {
            description: "rust exact, renamed, near-miss, and call-target variants",
            config: RUST_CONFIG,
            files: vec![
                ("crates/shop/src/orders.rs", rust_original()),
                ("crates/shop/src/billing.rs", rust_original()),
                ("crates/shop/src/customers.rs", RUST_RENAMED.to_owned()),
                (
                    "crates/shop/src/reports.rs",
                    seeded(RUST_TEMPLATE, "summarize_orders", RUST_EXTRA, PYTHON_CALLS),
                ),
                (
                    "crates/shop/src/exports.rs",
                    seeded(RUST_TEMPLATE, "summarize_orders", "", PYTHON_OTHER_CALLS),
                ),
                ("crates/shop/src/inventory.rs", RUST_UNRELATED.to_owned()),
                ("crates/shop/src/shipping.rs", RUST_SHORT.to_owned()),
                ("crates/shop/src/delivery.rs", RUST_SHORT.to_owned()),
                (
                    "crates/shop/src/audit.rs",
                    format!("#[cfg(test)]\nmod tests {{\n{}}}\n", rust_original()),
                ),
                (
                    "crates/shop/src/lib.rs",
                    "#[cfg(test)]\nmod checks;\n".to_owned(),
                ),
                ("crates/shop/src/checks.rs", rust_original()),
                ("crates/shop/tests/summary.rs", rust_original()),
            ],
            expected_links: &[
                (
                    "crates/shop/src/billing.rs",
                    "crates/shop/src/orders.rs",
                    "exact",
                ),
                (
                    "crates/shop/src/customers.rs",
                    "crates/shop/src/orders.rs",
                    "renamed",
                ),
                (
                    "crates/shop/src/exports.rs",
                    "crates/shop/src/orders.rs",
                    "near-miss",
                ),
                (
                    "crates/shop/src/orders.rs",
                    "crates/shop/src/reports.rs",
                    "near-miss",
                ),
            ],
            expected_absent: &[
                "crates/shop/src/inventory.rs",
                "crates/shop/src/shipping.rs",
                "crates/shop/src/delivery.rs",
                "crates/shop/src/audit.rs",
                "crates/shop/src/checks.rs",
                "crates/shop/tests/summary.rs",
            ],
        },
        DetectionTestCase {
            description: "typescript and javascript variants compare once types are dropped",
            config: TYPESCRIPT_CONFIG,
            files: vec![
                ("src/orders/summary.ts", typescript_original()),
                (
                    "src/billing/summary.js",
                    without_types(&typescript_original()),
                ),
                ("src/customers/summary.js", JAVASCRIPT_RENAMED.to_owned()),
                (
                    "src/reports/summary.ts",
                    seeded(
                        TYPESCRIPT_TEMPLATE,
                        "summarizeOrders",
                        TYPESCRIPT_EXTRA,
                        WEB_CALLS,
                    ),
                ),
                (
                    "src/exports/summary.ts",
                    seeded(TYPESCRIPT_TEMPLATE, "summarizeOrders", "", WEB_OTHER_CALLS),
                ),
                ("src/inventory/restock.ts", TYPESCRIPT_UNRELATED.to_owned()),
                ("src/orders/shipping.ts", TYPESCRIPT_SHORT.to_owned()),
                ("src/billing/shipping.ts", TYPESCRIPT_SHORT.to_owned()),
                ("tests/summary.test.ts", typescript_original()),
            ],
            expected_links: &[
                ("src/billing/summary.js", "src/orders/summary.ts", "exact"),
                (
                    "src/customers/summary.js",
                    "src/orders/summary.ts",
                    "renamed",
                ),
                (
                    "src/exports/summary.ts",
                    "src/orders/summary.ts",
                    "near-miss",
                ),
                (
                    "src/orders/summary.ts",
                    "src/reports/summary.ts",
                    "near-miss",
                ),
            ],
            expected_absent: &[
                "src/inventory/restock.ts",
                "src/orders/shipping.ts",
                "src/billing/shipping.ts",
                "tests/summary.test.ts",
            ],
        },
        DetectionTestCase {
            description: "svelte component scripts compare with modules and each other",
            config: SVELTE_CONFIG,
            files: vec![
                (
                    "src/lib/OrderSummary.svelte",
                    svelte_component(&typescript_original()),
                ),
                ("src/lib/summary.ts", typescript_original()),
                (
                    "src/lib/CustomerSummary.svelte",
                    svelte_component(JAVASCRIPT_RENAMED),
                ),
                (
                    "src/lib/ReportSummary.svelte",
                    svelte_component(&seeded(
                        TYPESCRIPT_TEMPLATE,
                        "summarizeOrders",
                        TYPESCRIPT_EXTRA,
                        WEB_CALLS,
                    )),
                ),
                (
                    "src/lib/ExportSummary.svelte",
                    svelte_component(&seeded(
                        TYPESCRIPT_TEMPLATE,
                        "summarizeOrders",
                        "",
                        WEB_OTHER_CALLS,
                    )),
                ),
                (
                    "src/lib/Restock.svelte",
                    svelte_component(TYPESCRIPT_UNRELATED),
                ),
                (
                    "src/lib/Shipping.svelte",
                    svelte_component(TYPESCRIPT_SHORT),
                ),
                (
                    "src/lib/Delivery.svelte",
                    svelte_component(TYPESCRIPT_SHORT),
                ),
            ],
            expected_links: &[
                (
                    "src/lib/CustomerSummary.svelte",
                    "src/lib/OrderSummary.svelte",
                    "renamed",
                ),
                (
                    "src/lib/ExportSummary.svelte",
                    "src/lib/OrderSummary.svelte",
                    "near-miss",
                ),
                (
                    "src/lib/OrderSummary.svelte",
                    "src/lib/ReportSummary.svelte",
                    "near-miss",
                ),
                ("src/lib/OrderSummary.svelte", "src/lib/summary.ts", "exact"),
            ],
            expected_absent: &[
                "src/lib/Restock.svelte",
                "src/lib/Shipping.svelte",
                "src/lib/Delivery.svelte",
            ],
        },
    ];
    for test_case in &test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        write(repository.path().join("fensu.toml"), test_case.config);
        write_files(repository.path(), &test_case.files);

        let output = run_dupes(repository.path(), &["--json", "--top", "100"]);
        let report = json_report(&output);
        let found = links(&report);
        let reported = found
            .iter()
            .flat_map(|(left, right, _)| [left.as_str(), right.as_str()])
            .collect::<Vec<_>>();

        assert_eq!(
            output.status.code(),
            Some(0),
            "{}: {}",
            test_case.description,
            text(&output.stderr)
        );
        assert!(
            test_case
                .expected_links
                .iter()
                .all(|(left, right, category)| found.contains(&(
                    (*left).to_owned(),
                    (*right).to_owned(),
                    (*category).to_owned()
                ))),
            "{}: {found:?}",
            test_case.description
        );
        assert!(
            test_case
                .expected_absent
                .iter()
                .all(|absent| !reported.contains(absent)),
            "{}: {found:?}",
            test_case.description
        );
    }
}
