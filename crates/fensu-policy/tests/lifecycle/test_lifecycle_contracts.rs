//! Focused invalidation, negotiation, suppression, and freshness contracts.

use std::time::Duration;

use fensu_policy::lifecycle::constants::{
    CACHE_IDENTITY_SCHEMA_VERSION, CUSTOM_HOST_PROTOCOL_VERSION,
};
use fensu_policy::lifecycle::errors::{HostOutputStream, LifecycleError};
use fensu_policy::lifecycle::models::{
    AnalysisInput, ApplySuppressionsRequest, CacheRead, CustomHostInvocation,
    CustomHostOutputLimits, CustomHostRequest, ExactSuppression, ScopedIgnore, SkillFreshness,
};
use fensu_policy::policy::models::ProductRuleCodeGrammar;
use fensu_policy::{
    apply_suppressions, evaluate_batch, invalidate_cache, read_cache, render_owned_skill,
    run_custom_host, serialize_findings, skill_freshness, write_cache,
};

use crate::helpers::{
    early_failure_host_command, empty_request, finding, hanging_host_command, host_output_limits,
    oversized_stderr_host_command, oversized_stdout_host_command, process_stops,
    process_tree_host_command, response_host_command, successful_leader_with_descendant_command,
    versioned_requests,
};
use crate::test_types::{
    CacheLifecycleTestCase, ErrorLifecycleTestCase, HostOverflowLifecycleTestCase,
    HostResponseLifecycleTestCase, IdentityLifecycleTestCase, OrderedIdentityLifecycleTestCase,
    ProcessTreeLifecycleTestCase, SerializationLifecycleTestCase, SkillLifecycleTestCase,
    SuccessfulProcessTreeLifecycleTestCase, SuppressionMatchLifecycleTestCase,
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
fn given_input_order_changes_when_identifying_batch_then_cache_identity_changes_under_schema_v2() {
    let test_cases = [OrderedIdentityLifecycleTestCase {
        description: "analysis input sequence participates in schema-v2 identity",
        expected_schema: 2,
        expected_distinct: true,
    }];

    for test_case in test_cases {
        let mut forward = empty_request();
        forward.inputs = vec![
            AnalysisInput {
                path: "src/first.rs".to_owned(),
                fingerprint: "first-1".to_owned(),
                facts: (),
            },
            AnalysisInput {
                path: "src/second.rs".to_owned(),
                fingerprint: "second-1".to_owned(),
                facts: (),
            },
        ];
        let mut reverse = forward.clone();
        reverse.inputs.reverse();
        let forward_identity =
            evaluate_batch(&forward, &["relations".to_owned()], |_| Ok(Vec::new()))
                .expect("forward batch identifies")
                .cache_identity;
        let reverse_identity =
            evaluate_batch(&reverse, &["relations".to_owned()], |_| Ok(Vec::new()))
                .expect("reverse batch identifies")
                .cache_identity;

        assert_eq!(
            CACHE_IDENTITY_SCHEMA_VERSION, test_case.expected_schema,
            "{}",
            test_case.description
        );
        assert_eq!(
            forward_identity != reverse_identity,
            test_case.expected_distinct,
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
fn given_invalid_finding_code_when_suppressing_then_input_is_rejected() {
    let test_cases = [ErrorLifecycleTestCase {
        description: "finding selectors are not exact codes",
        expected_error: LifecycleError::InvalidRuleCode {
            code: "STBK".to_owned(),
        },
    }];

    for test_case in test_cases {
        let grammar = ProductRuleCodeGrammar::new("STBK", "XSTBK").expect("valid namespaces");
        let error = apply_suppressions(ApplySuppressionsRequest {
            findings: vec![finding("STBK", "flows/orders.yaml", None)],
            evaluated_codes: &[],
            suppressions: &[],
            scoped_ignores: &[],
            grammar: &grammar,
        })
        .expect_err("finding selectors are not exact codes");

        assert_eq!(error, test_case.expected_error, "{}", test_case.description);
    }
}

#[test]
fn given_invalid_finding_path_when_suppressing_then_input_is_rejected() {
    let test_cases = [ErrorLifecycleTestCase {
        description: "finding paths must be canonical",
        expected_error: LifecycleError::InvalidRepositoryPath {
            path: "../flows/orders.yaml".to_owned(),
        },
    }];

    for test_case in test_cases {
        let grammar = ProductRuleCodeGrammar::new("STBK", "XSTBK").expect("valid namespaces");
        let error = apply_suppressions(ApplySuppressionsRequest {
            findings: vec![finding("STBKS001", "../flows/orders.yaml", None)],
            evaluated_codes: &[],
            suppressions: &[],
            scoped_ignores: &[],
            grammar: &grammar,
        })
        .expect_err("finding paths must be canonical");

        assert_eq!(error, test_case.expected_error, "{}", test_case.description);
    }
}

#[test]
fn given_invalid_evaluated_code_when_suppressing_then_input_is_rejected() {
    let test_cases = [ErrorLifecycleTestCase {
        description: "evaluated selectors are not exact codes",
        expected_error: LifecycleError::InvalidRuleCode {
            code: "STBK".to_owned(),
        },
    }];

    for test_case in test_cases {
        let grammar = ProductRuleCodeGrammar::new("STBK", "XSTBK").expect("valid namespaces");
        let evaluated_codes = ["STBK".to_owned()];
        let error = apply_suppressions(ApplySuppressionsRequest {
            findings: Vec::new(),
            evaluated_codes: &evaluated_codes,
            suppressions: &[],
            scoped_ignores: &[],
            grammar: &grammar,
        })
        .expect_err("evaluated selectors are not exact codes");

        assert_eq!(error, test_case.expected_error, "{}", test_case.description);
    }
}

#[test]
fn given_indexed_exact_and_scoped_matches_when_suppressing_then_each_match_applies_once() {
    let test_cases = [SuppressionMatchLifecycleTestCase {
        description: "exact and scoped indexes retain unmatched symbols",
        expected_suppressions: 1,
        expected_scoped_ignores: 1,
        expected_findings: 1,
        expected_symbol: "payments",
    }];

    for test_case in test_cases {
        let grammar = ProductRuleCodeGrammar::new("STBK", "XSTBK").expect("valid namespaces");
        let suppressions = [ExactSuppression {
            code: "STBKS001".to_owned(),
            path: "flows/orders.yaml".to_owned(),
            symbol: Some("orders".to_owned()),
            reason: "accepted fixture debt".to_owned(),
        }];
        let scoped_ignores = [ScopedIgnore {
            selectors: vec!["XSTBK".to_owned()],
            paths: vec!["generated/**".to_owned(), "vendor/**".to_owned()],
            reason: "generated inputs".to_owned(),
        }];
        let evaluated_codes = ["STBKS001".to_owned(), "XSTBKS001".to_owned()];
        let result = apply_suppressions(ApplySuppressionsRequest {
            findings: vec![
                finding("STBKS001", "flows/orders.yaml", Some("orders")),
                finding("STBKS001", "flows/orders.yaml", Some("payments")),
                finding("XSTBKS001", "generated/orders.yaml", None),
            ],
            evaluated_codes: &evaluated_codes,
            suppressions: &suppressions,
            scoped_ignores: &scoped_ignores,
            grammar: &grammar,
        })
        .expect("prepared suppression indexes match");

        assert_eq!(
            result.applied_suppressions, test_case.expected_suppressions,
            "{}",
            test_case.description
        );
        assert_eq!(
            result.applied_scoped_ignores, test_case.expected_scoped_ignores,
            "{}",
            test_case.description
        );
        assert_eq!(
            result.findings.len(),
            test_case.expected_findings,
            "{}",
            test_case.description
        );
        assert_eq!(
            result.findings[0].symbol.as_deref(),
            Some(test_case.expected_symbol),
            "{}",
            test_case.description
        );
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
            output_limits: host_output_limits(),
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
            output_limits: host_output_limits(),
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
            output_limits: host_output_limits(),
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
            output_limits: host_output_limits(),
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
            output_limits: host_output_limits(),
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
fn given_host_output_exceeds_explicit_limit_when_invoking_then_returns_stream_overflow() {
    let test_cases = [
        HostOverflowLifecycleTestCase {
            description: "stdout capture limit",
            command: oversized_stdout_host_command,
            output_limits: CustomHostOutputLimits {
                stdout_bytes: 8,
                stderr_bytes: 1_024,
            },
            expected_error: LifecycleError::HostOutputOverflow {
                stream: HostOutputStream::Stdout,
                limit_bytes: 8,
            },
        },
        HostOverflowLifecycleTestCase {
            description: "stderr capture limit",
            command: oversized_stderr_host_command,
            output_limits: CustomHostOutputLimits {
                stdout_bytes: 1_024,
                stderr_bytes: 8,
            },
            expected_error: LifecycleError::HostOutputOverflow {
                stream: HostOutputStream::Stderr,
                limit_bytes: 8,
            },
        },
    ];

    for test_case in test_cases {
        let request = CustomHostRequest {
            protocol: CUSTOM_HOST_PROTOCOL_VERSION,
            runtime_version: "runtime-1".to_owned(),
            payload: (),
        };
        let (program, arguments) = (test_case.command)();
        let error = run_custom_host::<_, serde_json::Value>(CustomHostInvocation {
            program: &program,
            arguments: &arguments,
            timeout: Duration::from_secs(5),
            output_limits: test_case.output_limits,
            request: &request,
        })
        .expect_err("bounded output must reject overflow");

        assert_eq!(error, test_case.expected_error, "{}", test_case.description);
    }
}

#[test]
fn given_successful_host_leader_with_live_descendant_when_invoking_then_job_is_cleaned_up() {
    let test_cases = [SuccessfulProcessTreeLifecycleTestCase {
        description: "successful leader leaves a live group descendant",
        expected_payload: true,
        expected_stopped: true,
    }];

    for test_case in test_cases {
        let directory = tempfile::tempdir().expect("process tree directory");
        let pid_file = directory.path().join("descendant.pid");
        let (program, arguments) = successful_leader_with_descendant_command(&pid_file);
        let request = CustomHostRequest {
            protocol: CUSTOM_HOST_PROTOCOL_VERSION,
            runtime_version: "runtime-1".to_owned(),
            payload: (),
        };
        let response = run_custom_host::<_, serde_json::Value>(CustomHostInvocation {
            program: &program,
            arguments: &arguments,
            timeout: Duration::from_secs(5),
            output_limits: host_output_limits(),
            request: &request,
        })
        .expect("successful leader response is retained");
        let pid = std::fs::read_to_string(&pid_file)
            .expect("host wrote descendant pid")
            .trim()
            .parse::<u32>()
            .expect("host pid is numeric");

        assert_eq!(
            response.payload.is_some(),
            test_case.expected_payload,
            "{}",
            test_case.description
        );
        assert_eq!(
            process_stops(pid),
            test_case.expected_stopped,
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_empty_host_runtime_when_invoking_then_process_is_not_launched() {
    let test_cases = [ErrorLifecycleTestCase {
        description: "empty request runtime fails before launch",
        expected_error: LifecycleError::InvalidConfiguration {
            message: "custom host runtime version must be non-empty".to_owned(),
        },
    }];

    for test_case in test_cases {
        let request = CustomHostRequest {
            protocol: CUSTOM_HOST_PROTOCOL_VERSION,
            runtime_version: " ".to_owned(),
            payload: (),
        };
        let error = run_custom_host::<_, serde_json::Value>(CustomHostInvocation {
            program: std::path::Path::new("not-a-real-host"),
            arguments: &[],
            timeout: Duration::from_secs(1),
            output_limits: host_output_limits(),
            request: &request,
        })
        .expect_err("empty request runtime fails before launch");

        assert_eq!(error, test_case.expected_error, "{}", test_case.description);
    }
}

#[test]
fn given_invalid_host_response_envelope_when_invoking_then_contract_is_rejected() {
    let envelope_error = LifecycleError::HostResponse {
        message: "response must contain exactly one non-empty error or payload".to_owned(),
    };
    let test_cases = [
        HostResponseLifecycleTestCase {
            description: "response contains neither payload nor error",
            response: "{\"protocol\":1,\"runtime_version\":\"runtime-1\",\"error\":null,\"payload\":null,\"messages\":[]}",
            expected_error: envelope_error.clone(),
        },
        HostResponseLifecycleTestCase {
            description: "response contains both payload and error",
            response: "{\"protocol\":1,\"runtime_version\":\"runtime-1\",\"error\":\"failure\",\"payload\":{},\"messages\":[]}",
            expected_error: envelope_error.clone(),
        },
        HostResponseLifecycleTestCase {
            description: "response error is empty",
            response: "{\"protocol\":1,\"runtime_version\":\"runtime-1\",\"error\":\" \",\"payload\":null,\"messages\":[]}",
            expected_error: envelope_error,
        },
        HostResponseLifecycleTestCase {
            description: "response runtime is empty",
            response: "{\"protocol\":1,\"runtime_version\":\"\",\"error\":null,\"payload\":{},\"messages\":[]}",
            expected_error: LifecycleError::HostResponse {
                message: "runtime_version must be non-empty".to_owned(),
            },
        },
    ];

    for test_case in test_cases {
        let request = CustomHostRequest {
            protocol: CUSTOM_HOST_PROTOCOL_VERSION,
            runtime_version: "runtime-1".to_owned(),
            payload: (),
        };
        let (program, arguments) = response_host_command(test_case.response);
        let error = run_custom_host::<_, serde_json::Value>(CustomHostInvocation {
            program: &program,
            arguments: &arguments,
            timeout: Duration::from_secs(5),
            output_limits: host_output_limits(),
            request: &request,
        })
        .expect_err("invalid host response fails");

        assert_eq!(error, test_case.expected_error, "{}", test_case.description);
    }
}

#[test]
fn given_host_identity_or_error_with_incompatible_payload_when_invoking_then_envelope_wins() {
    let test_cases = [
        HostResponseLifecycleTestCase {
            description: "dual envelope validation precedes payload decoding",
            response: "{\"protocol\":1,\"runtime_version\":\"runtime-1\",\"error\":\"boom\",\"payload\":{},\"messages\":[]}",
            expected_error: LifecycleError::HostResponse {
                message: "response must contain exactly one non-empty error or payload".to_owned(),
            },
        },
        HostResponseLifecycleTestCase {
            description: "protocol validation precedes payload decoding",
            response: "{\"protocol\":2,\"runtime_version\":\"runtime-1\",\"error\":null,\"payload\":{},\"messages\":[]}",
            expected_error: LifecycleError::HostProtocol {
                actual: 2,
                expected: CUSTOM_HOST_PROTOCOL_VERSION,
            },
        },
        HostResponseLifecycleTestCase {
            description: "runtime validation precedes payload decoding",
            response: "{\"protocol\":1,\"runtime_version\":\"runtime-2\",\"error\":null,\"payload\":{},\"messages\":[]}",
            expected_error: LifecycleError::HostRuntimeVersion {
                actual: "runtime-2".to_owned(),
                expected: "runtime-1".to_owned(),
            },
        },
    ];

    for test_case in test_cases {
        let request = CustomHostRequest {
            protocol: CUSTOM_HOST_PROTOCOL_VERSION,
            runtime_version: "runtime-1".to_owned(),
            payload: (),
        };
        let (program, arguments) = response_host_command(test_case.response);
        let error = run_custom_host::<_, bool>(CustomHostInvocation {
            program: &program,
            arguments: &arguments,
            timeout: Duration::from_secs(5),
            output_limits: host_output_limits(),
            request: &request,
        })
        .expect_err("envelope validation must precede typed payload decoding");

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
        let content = render_owned_skill(
            "fensu-policy",
            "streambuild-kata",
            "input-1",
            b"# StreamBuild Kata\n",
        )
        .expect("skill renders");
        let mut divergent = content.clone();
        divergent[0] = b'!';

        assert_eq!(
            skill_freshness(
                Some(&content),
                "fensu-policy",
                "streambuild-kata",
                "input-2",
            ),
            test_case.expected_stale,
            "{}",
            test_case.description
        );
        assert_eq!(
            skill_freshness(
                Some(&divergent),
                "fensu-policy",
                "streambuild-kata",
                "input-1",
            ),
            test_case.expected_divergent,
            "{}",
            test_case.description
        );
        assert_eq!(
            skill_freshness(
                Some(&divergent),
                "fensu-policy",
                "streambuild-kata",
                "input-2",
            ),
            SkillFreshness::Divergent,
            "content divergence takes precedence over stale inputs: {}",
            test_case.description
        );
        assert_eq!(
            skill_freshness(
                Some(&content),
                "another-owner",
                "streambuild-kata",
                "input-1",
            ),
            SkillFreshness::Unowned,
            "foreign ownership must not be claimed: {}",
            test_case.description
        );
        assert_eq!(
            skill_freshness(None, "fensu-policy", "streambuild-kata", "input-1"),
            test_case.expected_missing,
            "{}",
            test_case.description
        );
        assert!(
            render_owned_skill("fensu-policy", "streambuild-kata", "input-1", &content).is_err(),
            "owned content must not acquire a second marker: {}",
            test_case.description
        );
        assert!(
            render_owned_skill("fensu-policy", "streambuild-kata", "input-1", &content).is_err(),
            "owned content must not acquire a second marker: {}",
            test_case.description
        );
        let inline_marker = b"> <!-- fensu-policy-skill-owner: {\"content_fingerprint\":\"\",\"identity\":\"streambuild-kata\",\"input_fingerprint\":\"input-1\",\"schema\":1} -->\n";
        let quoted =
            render_owned_skill("fensu-policy", "streambuild-kata", "input-1", inline_marker)
                .expect("quoted marker text is not ownership");
        assert_eq!(
            skill_freshness(Some(&quoted), "fensu-policy", "streambuild-kata", "input-1",),
            SkillFreshness::Fresh,
            "appended marker must be replaced instead of quoted text: {}",
            test_case.description
        );
        let legacy = b"# Legacy\n<!-- fensu-policy-skill-owner: {\"content_fingerprint\":\"legacy-fingerprint\",\"identity\":\"streambuild-kata\",\"input_fingerprint\":\"input-1\",\"schema\":1} -->\n";
        assert_eq!(
            skill_freshness(Some(legacy), "fensu-policy", "streambuild-kata", "input-1",),
            SkillFreshness::Unowned,
            "schema v1 is recognized without claiming ownership: {}",
            test_case.description
        );
    }
}
