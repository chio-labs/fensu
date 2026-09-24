use crate::helpers::{
    cluster_members, direct, exemption_config, exporter, exporter_repository, function_body,
    json_report, method, run_dupes, text, write, write_files, BASE, CSV_EXPORTER, GENERIC_BASE,
    JSON_EXPORTER,
};
use crate::test_types::ClusterTestCase;

#[test]
fn given_contract_exemption_when_reporting_then_forced_overrides_follow_resolved_ancestry() {
    let test_cases = [
        ClusterTestCase {
            description: "overrides that would inherit from nowhere are forced and hidden",
            config: exemption_config(),
            files: exporter_repository(BASE, direct("CsvExporter"), direct("JsonExporter")),
            arguments: &["--json"],
            expected_clusters: vec![],
            expected_allowlisted_pairs: 0,
            expected_contract_exempt_members: 2,
        },
        ClusterTestCase {
            description: "a helper copy stays reported with forced members listed last",
            config: exemption_config(),
            files: [
                exporter_repository(BASE, direct("CsvExporter"), direct("JsonExporter")),
                vec![("src/shop/orders/export.py", function_body())],
            ]
            .concat(),
            arguments: &["--json"],
            expected_clusters: vec![vec!["src/shop/orders/export.py", "src/shop/exporters/csv.py [forced]", "src/shop/exporters/json.py [forced]"]],
            expected_allowlisted_pairs: 0,
            expected_contract_exempt_members: 0,
        },
        ClusterTestCase {
            description: "a forbidden owner's implementation does not make overrides optional",
            config: exemption_config(),
            files: exporter_repository(&format!("{BASE}\n{}", method()), direct("CsvExporter"), direct("JsonExporter")),
            arguments: &["--json"],
            expected_clusters: vec![vec!["src/shop/base.py", "src/shop/exporters/csv.py [forced]", "src/shop/exporters/json.py [forced]"]],
            expected_allowlisted_pairs: 0,
            expected_contract_exempt_members: 0,
        },
        ClusterTestCase {
            description: "an inheritable implementation outside the forbidden owners keeps overrides visible",
            config: exemption_config(),
            files: [
                exporter_repository(
                    BASE,
                    exporter("from shop.tabular import TabularExporter\n", "CsvExporter", "TabularExporter"),
                    exporter("from shop.tabular import TabularExporter\n", "JsonExporter", "TabularExporter"),
                ),
                vec![("src/shop/tabular.py", exporter("from shop.base import BaseExporter\n", "TabularExporter", "BaseExporter"))],
            ]
            .concat(),
            arguments: &["--json"],
            expected_clusters: vec![vec![CSV_EXPORTER, JSON_EXPORTER, "src/shop/tabular.py"]],
            expected_allowlisted_pairs: 0,
            expected_contract_exempt_members: 0,
        },
        ClusterTestCase {
            description: "a package re-export leaves ancestry unresolved",
            config: exemption_config(),
            files: [
                exporter_repository(
                    BASE,
                    exporter("from shop import BaseExporter\n", "CsvExporter", "BaseExporter"),
                    exporter("from shop import BaseExporter\n", "JsonExporter", "BaseExporter"),
                ),
                vec![("src/shop/__init__.py", "from shop.base import BaseExporter\n".to_owned())],
            ]
            .concat(),
            arguments: &["--json"],
            expected_clusters: vec![vec![CSV_EXPORTER, JSON_EXPORTER]],
            expected_allowlisted_pairs: 0,
            expected_contract_exempt_members: 0,
        },
        ClusterTestCase {
            description: "a module-qualified in-repository base leaves ancestry unresolved",
            config: exemption_config(),
            files: exporter_repository(
                BASE,
                exporter("from shop import base\n", "CsvExporter", "base.BaseExporter"),
                exporter("from shop import base\n", "JsonExporter", "base.BaseExporter"),
            ),
            arguments: &["--json"],
            expected_clusters: vec![vec![CSV_EXPORTER, JSON_EXPORTER]],
            expected_allowlisted_pairs: 0,
            expected_contract_exempt_members: 0,
        },
        ClusterTestCase {
            description: "a same-file class base leaves ancestry unresolved",
            config: exemption_config(),
            files: exporter_repository(
                BASE,
                exporter("from shop.base import BaseExporter\n\n\nclass Formats:\n    class Csv:\n        pass\n", "CsvExporter", "Formats.Csv, BaseExporter"),
                direct("JsonExporter"),
            ),
            arguments: &["--json"],
            expected_clusters: vec![vec![CSV_EXPORTER, "src/shop/exporters/json.py [forced]"]],
            expected_allowlisted_pairs: 0,
            expected_contract_exempt_members: 0,
        },
        ClusterTestCase {
            description: "a subscripted in-repository generic base resolves",
            config: exemption_config(),
            files: exporter_repository(
                GENERIC_BASE,
                exporter("from shop.base import BaseExporter\n", "CsvExporter", "BaseExporter[int]"),
                exporter("from shop.base import BaseExporter\n", "JsonExporter", "BaseExporter[str]"),
            ),
            arguments: &["--json"],
            expected_clusters: vec![],
            expected_allowlisted_pairs: 0,
            expected_contract_exempt_members: 2,
        },
        ClusterTestCase {
            description: "external and standard-library bases do not block the exemption",
            config: exemption_config(),
            files: exporter_repository(
                BASE,
                exporter("from typing import Generic, TypeVar\n\nfrom shop.base import BaseExporter\n\nT = TypeVar(\"T\")\n", "CsvExporter", "BaseExporter, Generic[T]"),
                exporter("import abc\n\nfrom shop.base import BaseExporter\n", "JsonExporter", "BaseExporter, abc.ABC"),
            ),
            arguments: &["--json"],
            expected_clusters: vec![],
            expected_allowlisted_pairs: 0,
            expected_contract_exempt_members: 2,
        },
        ClusterTestCase {
            description: "an absent contract file leaves the exemption inactive",
            config: exemption_config().replace("src/shop/contract.py:Exporter", "src/shop/retired.py:Exporter"),
            files: exporter_repository(BASE, direct("CsvExporter"), direct("JsonExporter")),
            arguments: &["--json"],
            expected_clusters: vec![vec![CSV_EXPORTER, JSON_EXPORTER]],
            expected_allowlisted_pairs: 0,
            expected_contract_exempt_members: 0,
        },
    ];
    for test_case in &test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        write(repository.path().join("fensu.toml"), &test_case.config);
        write_files(repository.path(), &test_case.files);

        let output = run_dupes(repository.path(), test_case.arguments);
        let report = json_report(&output);

        assert_eq!(
            output.status.code(),
            Some(0),
            "{}: {}",
            test_case.description,
            text(&output.stderr)
        );
        assert_eq!(
            cluster_members(&report),
            test_case.expected_clusters,
            "{}",
            test_case.description
        );
        assert_eq!(
            report["contract_exempt_members"],
            serde_json::json!(test_case.expected_contract_exempt_members),
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_forced_members_when_rendering_text_then_they_are_marked_and_excluded_from_estimates() {
    let test_cases = [crate::test_types::CommandOutputTestCase {
        description: "forced markers and single-copy token estimate",
        config: exemption_config(),
        files: [
            exporter_repository(BASE, direct("CsvExporter"), direct("JsonExporter")),
            vec![("src/shop/orders/export.py", function_body())],
        ]
        .concat(),
        arguments: &[],
        expected_exit_code: 0,
        expected_stdout: &[
            "  1. exact sim 1.00, ~",
            "     src/shop/orders/export.py:1-15 export_orders (",
            "     src/shop/exporters/csv.py:5-19 CsvExporter.export_orders (",
            " tokens) [forced]\n",
            "0 contract-exempt members hidden",
        ],
        expected_stderr: &[],
    }];
    for test_case in &test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        write(repository.path().join("fensu.toml"), &test_case.config);
        write_files(repository.path(), &test_case.files);

        let output = run_dupes(repository.path(), test_case.arguments);
        let stdout = text(&output.stdout);
        let json = json_report(&run_dupes(repository.path(), &["--json"]));
        let helper_tokens = json["clusters"][0]["members"][0]["tokens"].clone();

        assert_eq!(
            output.status.code(),
            Some(test_case.expected_exit_code),
            "{}",
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
        assert_eq!(
            json["clusters"][0]["duplicated_tokens"], helper_tokens,
            "{}",
            test_case.description
        );
    }
}
