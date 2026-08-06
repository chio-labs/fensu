//! Colored diagnostic rendering contracts for native check output.

use std::fs;

use tempfile::tempdir;

use crate::models::Fault;
use crate::reporting::main::report::report;
use crate::reporting::models::ReportRequest;
use crate::tests::test_types::RenderColorTestCase;

#[test]
fn given_colored_faults_when_rendering_then_uses_historical_orange_styles() {
    let test_cases = [RenderColorTestCase {
        description: "fault code, caret, and unhealthy summary use bold orange",
        source: "alpha = 1\nbeta = 2\n",
        line: 2,
        column: 4,
        expected_output: "\x1b[1;38;5;208mXRP001\x1b[0m  first\n\x1b[2m --> src/pkg/a.py:2:4\x1b[0m\n\x1b[2m  |\x1b[0m\n\x1b[2m2 |\x1b[0m beta = 2\n\x1b[2m  |\x1b[0m     \x1b[1;38;5;208m^\x1b[0m\n\x1b[2m  |\x1b[0m\n\n\x1b[1;38;5;208mFound 1 fault\x1b[0m\n",
    }];

    for test_case in &test_cases {
        let directory = tempdir().expect("temporary repository");
        let source_path = directory.path().join("src/pkg/a.py");
        fs::create_dir_all(source_path.parent().expect("source parent")).expect("source directory");
        fs::write(&source_path, test_case.source).expect("source file");
        let faults = [Fault {
            code: "XRP001".to_owned(),
            alias_of: None,
            path: source_path.to_string_lossy().into_owned(),
            line: Some(test_case.line),
            column: Some(test_case.column),
            message: "first".to_owned(),
            remediation: None,
            warning: false,
        }];

        let rendered = report(ReportRequest {
            faults: &faults,
            warnings: &[],
            root: directory.path(),
            color: true,
            show_warnings: false,
            evaluation_summary: None,
            applied_exceptions: 0,
            threshold_uses: &[],
        });

        assert_eq!(
            rendered, test_case.expected_output,
            "{}",
            test_case.description
        );
    }
}
