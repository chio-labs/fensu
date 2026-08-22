//! Complete non-Fensu consumer lifecycle through public crate contracts.

use fensu_policy::lifecycle::constants::CUSTOM_HOST_PROTOCOL_VERSION;
use fensu_policy::lifecycle::models::{
    ApplySuppressionsRequest, CacheRead, CustomHostRequest, ExactSuppression, FindingSeverity,
    ScopedIgnore, SkillFreshness,
};
use fensu_policy::policy::main::resolve_policy::resolve_policy;
use fensu_policy::policy::models::{PolicySelectors, ProductRuleCodeGrammar};
use fensu_policy::policy::types::PolicyRule;
use fensu_policy::{
    apply_suppressions, evaluate_batch, read_cache, render_owned_skill, report_summary,
    run_custom_host, serialize_findings, skill_freshness, write_cache,
};

use crate::helpers::{consumer_request, finding, host_command};
use crate::test_types::{ConsumerLifecycleTestCase, ConsumerRule, HostPayload};

#[test]
fn given_non_fensu_rule_pack_when_running_lifecycle_then_all_shared_contracts_compose() {
    let test_cases = [ConsumerLifecycleTestCase {
        description: "SQLBuild-style complete lifecycle",
        expected_codes: vec!["SQBKS001", "XSQBKS001"],
        expected_blocking: 1,
        expected_warnings: 0,
        expected_suppressions: 1,
        expected_scoped_ignores: 1,
        expected_hosted: true,
        expected_freshness: SkillFreshness::Fresh,
    }];

    for test_case in test_cases {
        let grammar = ProductRuleCodeGrammar::new("SQBK", "XSQBK").expect("valid namespaces");
        let rules = [
            ConsumerRule { code: "SQBKS001" },
            ConsumerRule { code: "XSQBKS001" },
        ];
        let catalogue = rules.iter().collect::<Vec<_>>();
        let policy = resolve_policy(
            &catalogue,
            &(),
            &PolicySelectors {
                select: vec!["SQBK".to_owned(), "XSQBK".to_owned()],
                warn: Vec::new(),
                ignore: Vec::new(),
            },
            &grammar,
        )
        .expect("consumer policy resolves");
        let request = consumer_request();
        let response = evaluate_batch(&request, &["sql-relations".to_owned()], |_| {
            let mut ignored = finding("XSQBKS001", "models/ignored.sql", None);
            ignored.severity = FindingSeverity::Warning;
            Ok(vec![
                ignored,
                finding("SQBKS001", "models/retained.sql", None),
                finding("SQBKS001", "models/suppressed.sql", None),
            ])
        })
        .expect("batch evaluates");
        let evaluated_codes = policy
            .blocking
            .iter()
            .map(|rule| rule.code().to_owned())
            .collect::<Vec<_>>();
        let suppressions = [ExactSuppression {
            code: "SQBKS001".to_owned(),
            path: "models/suppressed.sql".to_owned(),
            symbol: None,
            reason: "accepted fixture debt".to_owned(),
        }];
        let scoped_ignores = [ScopedIgnore {
            selectors: vec!["XSQBK".to_owned()],
            paths: vec!["models/ignored.sql".to_owned()],
            reason: "generated fixture model".to_owned(),
        }];
        let suppressed = apply_suppressions(ApplySuppressionsRequest {
            findings: response.findings,
            evaluated_codes: &evaluated_codes,
            suppressions: &suppressions,
            scoped_ignores: &scoped_ignores,
            grammar: &grammar,
        })
        .expect("suppressions apply");
        let report = report_summary(
            &suppressed.findings,
            suppressed.applied_suppressions,
            suppressed.applied_scoped_ignores,
        );
        let encoded = serialize_findings(&suppressed.findings).expect("findings serialize");
        let cache = tempfile::tempdir().expect("cache directory");
        write_cache(
            cache.path(),
            "sqlbuild-kata",
            &response.cache_identity,
            &encoded,
        )
        .expect("cache writes");
        let cached = read_cache::<Vec<u8>>(cache.path(), "sqlbuild-kata", &response.cache_identity)
            .expect("cache reads");
        let host_request = CustomHostRequest {
            protocol: CUSTOM_HOST_PROTOCOL_VERSION,
            runtime_version: "fixture-runtime-1".to_owned(),
            payload: request,
        };
        let (program, arguments) = host_command();
        let hosted = run_custom_host::<_, HostPayload>(&program, &arguments, &host_request)
            .expect("isolated custom host runs");
        let skill = render_owned_skill(
            "sqlbuild-kata",
            &response.cache_identity,
            b"# SQLBuild Kata\n",
        )
        .expect("skill renders");
        let actual_codes = policy
            .blocking
            .iter()
            .map(|rule| rule.code())
            .collect::<Vec<_>>();

        assert_eq!(
            actual_codes, test_case.expected_codes,
            "{}",
            test_case.description
        );
        assert_eq!(
            report.blocking, test_case.expected_blocking,
            "{}",
            test_case.description
        );
        assert_eq!(
            report.warnings, test_case.expected_warnings,
            "{}",
            test_case.description
        );
        assert_eq!(
            report.applied_suppressions, test_case.expected_suppressions,
            "{}",
            test_case.description
        );
        assert_eq!(
            report.applied_scoped_ignores, test_case.expected_scoped_ignores,
            "{}",
            test_case.description
        );
        assert_eq!(cached, CacheRead::Hit(encoded), "{}", test_case.description);
        assert_eq!(
            hosted.payload.expect("host payload").hosted,
            test_case.expected_hosted,
            "{}",
            test_case.description
        );
        assert_eq!(
            skill_freshness(Some(&skill), "sqlbuild-kata", &response.cache_identity),
            test_case.expected_freshness,
            "{}",
            test_case.description
        );
    }
}
