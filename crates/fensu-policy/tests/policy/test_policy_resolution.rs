//! Applicability-aware policy tier resolution through public contracts.

use crate::test_types::{
    SqlDialect, SqlPolicyTestCase, SqlRule, StreamMode, StreamPolicyTestCase, StreamRule,
};
use fensu_policy::policy::errors::PolicyError;
use fensu_policy::policy::main::resolve_policy::resolve_policy;
use fensu_policy::policy::models::{PolicySelectors, ProductRuleCodeGrammar};
use fensu_policy::policy::types::{PolicyRule, PolicyTier};

#[test]
fn given_sql_policy_cases_when_resolving_then_returns_expected_tiers_or_error() {
    let test_cases = [
        SqlPolicyTestCase {
            description: "default and exact selection preserve catalogue order",
            rules: vec![
                SqlRule {
                    code: "SQBKJ001",
                    enabled: true,
                    dialects: &[SqlDialect::Postgres],
                    implementation: None,
                },
                SqlRule {
                    code: "XSQBKD001",
                    enabled: true,
                    dialects: &[SqlDialect::Postgres],
                    implementation: None,
                },
                SqlRule {
                    code: "XSQBKD002",
                    enabled: false,
                    dialects: &[SqlDialect::Postgres],
                    implementation: None,
                },
                SqlRule {
                    code: "XSQBKD003",
                    enabled: true,
                    dialects: &[SqlDialect::Snowflake],
                    implementation: None,
                },
            ],
            dialect: SqlDialect::Postgres,
            selectors: PolicySelectors {
                select: vec![
                    "SQBK".to_owned(),
                    "XSQBKD".to_owned(),
                    "XSQBKD002".to_owned(),
                ],
                warn: Vec::new(),
                ignore: Vec::new(),
            },
            expected_catalogue: vec!["SQBKJ001", "XSQBKD001", "XSQBKD002"],
            expected_blocking: vec!["SQBKJ001", "XSQBKD001", "XSQBKD002"],
            expected_warnings: Vec::new(),
            expected_ignored: Vec::new(),
            expected_error: None,
        },
        SqlPolicyTestCase {
            description: "ignore removes blocking while warning remains independent",
            rules: vec![
                SqlRule {
                    code: "XSQBKD001",
                    enabled: true,
                    dialects: &[SqlDialect::Postgres],
                    implementation: None,
                },
                SqlRule {
                    code: "XSQBKD002",
                    enabled: true,
                    dialects: &[SqlDialect::Postgres],
                    implementation: None,
                },
            ],
            dialect: SqlDialect::Postgres,
            selectors: PolicySelectors {
                select: vec!["XSQBKD001".to_owned()],
                warn: vec!["XSQBKD002".to_owned()],
                ignore: vec!["XSQBKD001".to_owned()],
            },
            expected_catalogue: vec!["XSQBKD001", "XSQBKD002"],
            expected_blocking: Vec::new(),
            expected_warnings: vec!["XSQBKD002"],
            expected_ignored: vec!["XSQBKD001"],
            expected_error: None,
        },
        SqlPolicyTestCase {
            description: "blocking and warning overlap is rejected",
            rules: vec![SqlRule {
                code: "XSQBKD001",
                enabled: true,
                dialects: &[SqlDialect::Postgres],
                implementation: None,
            }],
            dialect: SqlDialect::Postgres,
            selectors: PolicySelectors {
                select: vec!["XSQBKD001".to_owned()],
                warn: vec!["XSQBKD001".to_owned()],
                ignore: Vec::new(),
            },
            expected_catalogue: Vec::new(),
            expected_blocking: Vec::new(),
            expected_warnings: Vec::new(),
            expected_ignored: Vec::new(),
            expected_error: Some(PolicyError::TierConflict {
                code: "XSQBKD001".to_owned(),
                first: PolicyTier::Blocking,
                second: PolicyTier::Warning,
            }),
        },
        SqlPolicyTestCase {
            description: "active aliases cannot execute one implementation twice",
            rules: vec![
                SqlRule {
                    code: "XSQBKD001",
                    enabled: true,
                    dialects: &[SqlDialect::Postgres],
                    implementation: Some("XSQBKD001"),
                },
                SqlRule {
                    code: "XSQBKD099",
                    enabled: true,
                    dialects: &[SqlDialect::Postgres],
                    implementation: Some("XSQBKD001"),
                },
            ],
            dialect: SqlDialect::Postgres,
            selectors: PolicySelectors {
                select: vec!["XSQBKD001".to_owned(), "XSQBKD099".to_owned()],
                warn: Vec::new(),
                ignore: Vec::new(),
            },
            expected_catalogue: Vec::new(),
            expected_blocking: Vec::new(),
            expected_warnings: Vec::new(),
            expected_ignored: Vec::new(),
            expected_error: Some(PolicyError::DuplicateImplementation {
                first_code: "XSQBKD001".to_owned(),
                second_code: "XSQBKD099".to_owned(),
                implementation_code: "XSQBKD001".to_owned(),
            }),
        },
    ];

    for test_case in test_cases {
        let catalogue = test_case.rules.iter().collect::<Vec<_>>();
        let grammar =
            ProductRuleCodeGrammar::new("SQBK", "XSQBK").expect("SQLBuild namespaces are valid");
        let result = resolve_policy(
            &catalogue,
            &test_case.dialect,
            &test_case.selectors,
            &grammar,
        );
        assert_eq!(
            result.as_ref().err(),
            test_case.expected_error.as_ref(),
            "case failed: {}",
            test_case.description
        );
        let Ok(selection) = result else {
            continue;
        };
        let actual_catalogue = selection
            .catalogue
            .iter()
            .map(|rule| rule.code())
            .collect::<Vec<_>>();
        let actual_blocking = selection
            .blocking
            .iter()
            .map(|rule| rule.code())
            .collect::<Vec<_>>();
        let actual_warnings = selection
            .warnings
            .iter()
            .map(|rule| rule.code())
            .collect::<Vec<_>>();
        let actual_ignored = selection
            .ignored
            .iter()
            .map(|rule| rule.code())
            .collect::<Vec<_>>();
        assert_eq!(
            actual_catalogue, test_case.expected_catalogue,
            "{}",
            test_case.description
        );
        assert_eq!(
            actual_blocking, test_case.expected_blocking,
            "{}",
            test_case.description
        );
        assert_eq!(
            actual_warnings, test_case.expected_warnings,
            "{}",
            test_case.description
        );
        assert_eq!(
            actual_ignored, test_case.expected_ignored,
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_stream_policy_cases_when_resolving_then_uses_consumer_applicability() {
    let test_cases = [StreamPolicyTestCase {
        description: "continuous stream rules require no Fensu analyzer type",
        rules: vec![
            StreamRule {
                code: "STBKT001",
                mode: StreamMode::Continuous,
            },
            StreamRule {
                code: "XSTBKT001",
                mode: StreamMode::Continuous,
            },
            StreamRule {
                code: "XSTBKT002",
                mode: StreamMode::Batch,
            },
        ],
        mode: StreamMode::Continuous,
        selectors: PolicySelectors {
            select: vec!["STBK".to_owned(), "XSTBK".to_owned()],
            warn: Vec::new(),
            ignore: Vec::new(),
        },
        expected_catalogue: vec!["STBKT001", "XSTBKT001"],
        expected_blocking: vec!["STBKT001", "XSTBKT001"],
    }];

    for test_case in test_cases {
        let catalogue = test_case.rules.iter().collect::<Vec<_>>();
        let grammar =
            ProductRuleCodeGrammar::new("STBK", "XSTBK").expect("StreamBuild namespaces are valid");
        let selection = resolve_policy(&catalogue, &test_case.mode, &test_case.selectors, &grammar)
            .expect("stream policy resolves");
        let actual_catalogue = selection
            .catalogue
            .iter()
            .map(|rule| rule.code())
            .collect::<Vec<_>>();
        let actual_blocking = selection
            .blocking
            .iter()
            .map(|rule| rule.code())
            .collect::<Vec<_>>();
        assert_eq!(
            actual_catalogue, test_case.expected_catalogue,
            "{}",
            test_case.description
        );
        assert_eq!(
            actual_blocking, test_case.expected_blocking,
            "{}",
            test_case.description
        );
    }
}
