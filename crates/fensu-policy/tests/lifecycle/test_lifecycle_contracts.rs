//! Focused invalidation, negotiation, suppression, and freshness contracts.

use std::path::Path;

use fensu_policy::lifecycle::constants::CUSTOM_HOST_PROTOCOL_VERSION;
use fensu_policy::lifecycle::errors::LifecycleError;
use fensu_policy::lifecycle::models::{
    ApplySuppressionsRequest, CacheRead, CustomHostRequest, ExactSuppression, SkillFreshness,
};
use fensu_policy::policy::models::ProductRuleCodeGrammar;
use fensu_policy::{
    apply_suppressions, evaluate_batch, invalidate_cache, read_cache, render_owned_skill,
    run_custom_host, serialize_findings, skill_freshness, write_cache,
};

use crate::helpers::{empty_request, finding, versioned_requests};
use crate::test_types::{
    CacheLifecycleTestCase, ErrorLifecycleTestCase, IdentityLifecycleTestCase,
    SerializationLifecycleTestCase, SkillLifecycleTestCase,
};

#[test]
fn given_identity_dimension_changes_when_reading_cache_then_entry_is_invalidated() {
    let test_cases = [CacheLifecycleTestCase {
        description: "identity mismatch and explicit invalidation",
        expected_invalidated: true,
        expected_removed: true,
    }];

    for test_case in test_cases {
        let directory = tempfile::tempdir().expect("cache directory");
        write_cache(directory.path(), "fixture", "identity-1", &vec![1_u8, 2])
            .expect("cache writes");
        let invalidated =
            read_cache::<Vec<u8>>(directory.path(), "fixture", "identity-2").expect("cache reads");
        let removed = invalidate_cache(directory.path(), "fixture").expect("cache invalidates");

        assert_eq!(
            invalidated == CacheRead::Invalidated,
            test_case.expected_invalidated,
            "{}",
            test_case.description
        );
        assert_eq!(
            removed, test_case.expected_removed,
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_missing_capability_when_evaluating_then_fails_before_evaluator_runs() {
    let test_cases = [ErrorLifecycleTestCase {
        description: "missing relation capability",
        expected_error: LifecycleError::MissingCapabilities {
            capabilities: vec!["relations".to_owned()],
        },
    }];

    for test_case in test_cases {
        let request = empty_request();
        let error = evaluate_batch(&request, &[], |_| panic!("evaluator must not run"))
            .expect_err("capability must be rejected");

        assert_eq!(error, test_case.expected_error, "{}", test_case.description);
    }
}

#[test]
fn given_each_runtime_version_changes_when_identifying_batch_then_cache_identity_changes() {
    let test_cases = [IdentityLifecycleTestCase {
        description: "all five required version dimensions",
        expected_unique_identities: 6,
    }];

    for test_case in test_cases {
        let identities = versioned_requests()
            .iter()
            .map(|request| {
                evaluate_batch(request, &["relations".to_owned()], |_| Ok(Vec::new()))
                    .expect("batch identifies")
                    .cache_identity
            })
            .collect::<std::collections::HashSet<_>>();

        assert_eq!(
            identities.len(),
            test_case.expected_unique_identities,
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_stale_exact_suppression_when_rule_was_evaluated_then_returns_actionable_error() {
    let test_cases = [ErrorLifecycleTestCase {
        description: "symbol-specific stale suppression",
        expected_error: LifecycleError::StaleSuppression {
            code: "STBKS001".to_owned(),
            path: "flows/orders.yaml".to_owned(),
            symbol: Some("orders".to_owned()),
            reason: "temporary migration".to_owned(),
        },
    }];

    for test_case in test_cases {
        let grammar = ProductRuleCodeGrammar::new("STBK", "XSTBK").expect("valid namespaces");
        let suppressions = [ExactSuppression {
            code: "STBKS001".to_owned(),
            path: "flows/orders.yaml".to_owned(),
            symbol: Some("orders".to_owned()),
            reason: "temporary migration".to_owned(),
        }];
        let evaluated_codes = ["STBKS001".to_owned()];
        let error = apply_suppressions(ApplySuppressionsRequest {
            findings: vec![finding("STBKS001", "flows/orders.yaml", Some("payments"))],
            evaluated_codes: &evaluated_codes,
            suppressions: &suppressions,
            scoped_ignores: &[],
            grammar: &grammar,
        })
        .expect_err("stale suppression must fail");

        assert_eq!(error, test_case.expected_error, "{}", test_case.description);
    }
}

#[test]
fn given_findings_in_different_orders_when_serializing_then_bytes_are_identical() {
    let test_cases = [SerializationLifecycleTestCase {
        description: "parallel evaluator order does not affect serialization",
        expected_equal: true,
    }];

    for test_case in test_cases {
        let first = finding("STBKS002", "flows/zeta.yaml", None);
        let second = finding("STBKS001", "flows/alpha.yaml", None);
        let forward = serialize_findings(&[first.clone(), second.clone()])
            .expect("forward findings serialize");
        let reverse = serialize_findings(&[second, first]).expect("reverse findings serialize");

        assert_eq!(
            forward == reverse,
            test_case.expected_equal,
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_unsupported_host_request_when_invoking_then_process_is_not_launched() {
    let test_cases = [ErrorLifecycleTestCase {
        description: "unsupported custom host request protocol",
        expected_error: LifecycleError::HostProtocol {
            actual: CUSTOM_HOST_PROTOCOL_VERSION + 1,
            expected: CUSTOM_HOST_PROTOCOL_VERSION,
        },
    }];

    for test_case in test_cases {
        let request = CustomHostRequest {
            protocol: CUSTOM_HOST_PROTOCOL_VERSION + 1,
            runtime_version: "runtime-1".to_owned(),
            payload: (),
        };
        let error = run_custom_host::<_, ()>(Path::new("not-a-real-host"), &[], &request)
            .expect_err("unsupported protocol fails before launch");

        assert_eq!(error, test_case.expected_error, "{}", test_case.description);
    }
}

#[test]
fn given_skill_input_or_content_changes_when_checking_then_reports_exact_freshness_state() {
    let test_cases = [SkillLifecycleTestCase {
        description: "owned generated skill",
        expected_stale: SkillFreshness::Stale,
        expected_divergent: SkillFreshness::Divergent,
        expected_missing: SkillFreshness::Missing,
    }];

    for test_case in test_cases {
        let content = render_owned_skill("streambuild-kata", "input-1", b"# StreamBuild Kata\n")
            .expect("skill renders");
        let mut divergent = content.clone();
        divergent[0] = b'!';

        assert_eq!(
            skill_freshness(Some(&content), "streambuild-kata", "input-2"),
            test_case.expected_stale,
            "{}",
            test_case.description
        );
        assert_eq!(
            skill_freshness(Some(&divergent), "streambuild-kata", "input-1"),
            test_case.expected_divergent,
            "{}",
            test_case.description
        );
        assert_eq!(
            skill_freshness(None, "streambuild-kata", "input-1"),
            test_case.expected_missing,
            "{}",
            test_case.description
        );
    }
}
