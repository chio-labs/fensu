//! Focused invalidation, negotiation, suppression, and freshness contracts.

use std::time::Duration;

use fensu_policy::lifecycle::constants::CUSTOM_HOST_PROTOCOL_VERSION;
use fensu_policy::lifecycle::errors::LifecycleError;
use fensu_policy::lifecycle::models::{
    ApplySuppressionsRequest, CacheRead, CustomHostInvocation, CustomHostRequest, ExactSuppression,
    ScopedIgnore, SkillFreshness,
};
use fensu_policy::policy::models::ProductRuleCodeGrammar;
use fensu_policy::{
    apply_suppressions, evaluate_batch, invalidate_cache, read_cache, render_owned_skill,
    run_custom_host, serialize_findings, skill_freshness, write_cache,
};

use crate::helpers::{
    early_failure_host_command, empty_request, finding, hanging_host_command, process_stops,
    process_tree_host_command, versioned_requests,
};
use crate::test_types::{
    CacheLifecycleTestCase, ErrorLifecycleTestCase, IdentityLifecycleTestCase,
    ProcessTreeLifecycleTestCase, SerializationLifecycleTestCase, SkillLifecycleTestCase,
};

#[cfg(unix)]
use crate::helpers::backpressure_host_command;
#[cfg(unix)]
use crate::test_types::HostLifecycleTestCase;

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
fn given_noncanonical_exact_path_when_applying_suppressions_then_configuration_is_rejected() {
    let test_cases = [ErrorLifecycleTestCase {
        description: "drive-shaped exact suppression path",
        expected_error: LifecycleError::InvalidRepositoryPath {
            path: "C:/flows/orders.yaml".to_owned(),
        },
    }];

    for test_case in test_cases {
        let grammar = ProductRuleCodeGrammar::new("STBK", "XSTBK").expect("valid namespaces");
        let suppressions = [ExactSuppression {
            code: "STBKS001".to_owned(),
            path: "C:/flows/orders.yaml".to_owned(),
            symbol: None,
            reason: "temporary migration".to_owned(),
        }];
        let error = apply_suppressions(ApplySuppressionsRequest {
            findings: Vec::new(),
            evaluated_codes: &[],
            suppressions: &suppressions,
            scoped_ignores: &[],
            grammar: &grammar,
        })
        .expect_err("noncanonical exact path must fail");

        assert_eq!(error, test_case.expected_error, "{}", test_case.description);
    }
}

#[test]
fn given_parent_relative_scoped_pattern_when_applying_then_configuration_is_rejected() {
    let test_cases = [ErrorLifecycleTestCase {
        description: "parent-relative scoped ignore pattern",
        expected_error: LifecycleError::InvalidPathPattern {
            pattern: "../**".to_owned(),
        },
    }];

    for test_case in test_cases {
        let grammar = ProductRuleCodeGrammar::new("STBK", "XSTBK").expect("valid namespaces");
        let scoped_ignores = [ScopedIgnore {
            selectors: vec!["STBK".to_owned()],
            paths: vec!["../**".to_owned()],
            reason: "invalid fixture scope".to_owned(),
        }];
        let error = apply_suppressions(ApplySuppressionsRequest {
            findings: Vec::new(),
            evaluated_codes: &[],
            suppressions: &[],
            scoped_ignores: &scoped_ignores,
            grammar: &grammar,
        })
        .expect_err("parent-relative scoped pattern must fail");

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
        let mut first = finding("STBKS001", "flows/orders.yaml", None);
        first.column = None;
        let mut second = first.clone();
        second.column = Some(0);
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
        let error = run_custom_host::<_, ()>(CustomHostInvocation {
            program: std::path::Path::new("not-a-real-host"),
            arguments: &[],
            timeout: Duration::from_secs(1),
            request: &request,
        })
        .expect_err("unsupported protocol fails before launch");

        assert_eq!(error, test_case.expected_error, "{}", test_case.description);
    }
}

#[test]
fn given_unresponsive_host_when_timeout_expires_then_process_is_terminated() {
    let timeout = Duration::from_millis(100);
    let test_cases = [ErrorLifecycleTestCase {
        description: "unresponsive custom host",
        expected_error: LifecycleError::HostTimeout {
            timeout_millis: 100,
        },
    }];

    for test_case in test_cases {
        let request = CustomHostRequest {
            protocol: CUSTOM_HOST_PROTOCOL_VERSION,
            runtime_version: "runtime-1".to_owned(),
            payload: (),
        };
        let (program, arguments) = hanging_host_command();
        let error = run_custom_host::<_, ()>(CustomHostInvocation {
            program: &program,
            arguments: &arguments,
            timeout,
            request: &request,
        })
        .expect_err("unresponsive host must time out");

        assert_eq!(error, test_case.expected_error, "{}", test_case.description);
    }
}

#[test]
fn given_host_process_tree_when_timeout_expires_then_descendants_are_terminated() {
    let test_cases = [ProcessTreeLifecycleTestCase {
        description: "custom host descendant inherits process group",
        expected_stopped: true,
    }];

    for test_case in test_cases {
        let directory = tempfile::tempdir().expect("process tree directory");
        let pid_file = directory.path().join("descendant.pid");
        let (program, arguments) = process_tree_host_command(&pid_file);
        let request = CustomHostRequest {
            protocol: CUSTOM_HOST_PROTOCOL_VERSION,
            runtime_version: "runtime-1".to_owned(),
            payload: (),
        };
        let error = run_custom_host::<_, ()>(CustomHostInvocation {
            program: &program,
            arguments: &arguments,
            timeout: Duration::from_secs(2),
            request: &request,
        })
        .expect_err("host process tree must time out");
        let pids = std::fs::read_to_string(&pid_file)
            .expect("host wrote descendant pid")
            .split_whitespace()
            .map(|pid| pid.parse::<u32>().expect("host pid is numeric"))
            .collect::<Vec<_>>();

        assert_eq!(
            error,
            LifecycleError::HostTimeout {
                timeout_millis: 2_000,
            },
            "{}",
            test_case.description
        );
        assert_eq!(
            pids.into_iter().all(process_stops),
            test_case.expected_stopped,
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_host_early_exit_when_invoking_with_large_request_then_stderr_is_preserved() {
    let test_cases = [ErrorLifecycleTestCase {
        description: "early host exit with broken stdin pipe",
        expected_error: LifecycleError::HostFailure {
            message: "actionable failure".to_owned(),
        },
    }];

    for test_case in test_cases {
        let (program, arguments) = early_failure_host_command();
        let request = CustomHostRequest {
            protocol: CUSTOM_HOST_PROTOCOL_VERSION,
            runtime_version: "runtime-1".to_owned(),
            payload: vec![0_u8; 262_144],
        };
        let error = run_custom_host::<_, ()>(CustomHostInvocation {
            program: &program,
            arguments: &arguments,
            timeout: Duration::from_secs(5),
            request: &request,
        })
        .expect_err("early host failure must preserve stderr");

        assert_eq!(error, test_case.expected_error, "{}", test_case.description);
    }
}

#[cfg(unix)]
#[test]
fn given_host_output_exceeds_pipe_capacity_when_invoking_then_exchange_does_not_deadlock() {
    let test_cases = [HostLifecycleTestCase {
        description: "host writes stderr before consuming stdin",
        expected_payload: true,
    }];

    for test_case in test_cases {
        let request = CustomHostRequest {
            protocol: CUSTOM_HOST_PROTOCOL_VERSION,
            runtime_version: "runtime-1".to_owned(),
            payload: vec![0_u8; 262_144],
        };
        let (program, arguments) = backpressure_host_command();
        let response = run_custom_host::<_, serde_json::Value>(CustomHostInvocation {
            program: &program,
            arguments: &arguments,
            timeout: Duration::from_secs(5),
            request: &request,
        })
        .expect("concurrent pipe exchange must complete");

        assert_eq!(
            response.payload.is_some(),
            test_case.expected_payload,
            "{}",
            test_case.description
        );
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
        assert!(
            render_owned_skill("streambuild-kata", "input-1", &content).is_err(),
            "owned content must not acquire a second marker: {}",
            test_case.description
        );
        assert!(
            render_owned_skill("streambuild-kata", "input-1", &content).is_err(),
            "owned content must not acquire a second marker: {}",
            test_case.description
        );
        let inline_marker = b"> <!-- fensu-policy-skill-owner: {\"content_fingerprint\":\"\",\"identity\":\"streambuild-kata\",\"input_fingerprint\":\"input-1\",\"schema\":1} -->\n";
        let quoted = render_owned_skill("streambuild-kata", "input-1", inline_marker)
            .expect("quoted marker text is not ownership");
        assert_eq!(
            skill_freshness(Some(&quoted), "streambuild-kata", "input-1"),
            SkillFreshness::Fresh,
            "appended marker must be replaced instead of quoted text: {}",
            test_case.description
        );
    }
}
