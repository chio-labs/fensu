//! Direct native core-rule diagnostic contracts.

use std::collections::HashMap;

use fensu_facts::extension::models::ProgramHandle;
use fensu_native::rules::constants::{
    DAGSTER_AUTOLOAD_EXTERNAL_DISCOVERY_CODE, TOP_LEVEL_DIRECT_MODULES_CODE,
};
use fensu_native::rules::main::evaluate_core_rules::evaluate_core_rules;
use fensu_native::rules::main::plan_execution_owners::plan_execution_owners;
use fensu_native::rules::models::{
    NativeExecutionRule, NativeExecutionTarget, NativeProjectModule, NativeProjectPlane,
    NativeRuleContext,
};
use ruff_python_ast::PythonVersion;

use crate::test_types;

#[test]
fn given_core_rule_contract_corpus_when_evaluating_then_diagnostics_are_exact() {
    let test_cases = [test_types::CoreRuleCorpusTestCase {
        description: "legacy captured requests preserve every proven core diagnostic",
        expected_fixture_count: 658,
        expected_core_code_count: 116,
        expected_non_faulting_codes: &["FFR504", "FFR707", "FFT001"],
    }];
    for test_case in &test_cases {
        assert_eq!(
            crate::helpers::fixtures().len(),
            test_case.expected_fixture_count,
            "{}",
            test_case.description
        );
        crate::helpers::assert_corpus_contract(test_case, crate::helpers::fixtures());
    }
}

#[test]
fn given_generated_core_rule_corpus_when_evaluating_then_every_registration_is_covered() {
    let test_cases = [test_types::CoreRuleCorpusTestCase {
        description: "current rule suites reproducibly cover every core registration",
        expected_fixture_count: 269,
        expected_core_code_count: 116,
        expected_non_faulting_codes: &["FFR301", "FFR302", "FFR306", "FFR308", "FFR309", "FFR403"],
    }];
    for test_case in &test_cases {
        assert_eq!(
            crate::helpers::generated_fixtures().len(),
            test_case.expected_fixture_count,
            "{}",
            test_case.description
        );
        crate::helpers::assert_corpus_contract(test_case, crate::helpers::generated_fixtures());
    }
}

#[test]
fn given_applicable_rule_without_execution_owner_when_planning_then_fails_closed() {
    let test_cases = [test_types::ExecutionPlanningErrorTestCase {
        description: "unknown execution owner cannot silently suppress an applicable rule",
        code: "FPDG004",
        family: "custom",
        owner: "unknown",
        expected_error: "Selected rule FPDG004 has applicable files but execution owner 'unknown' produced no targets.",
    }];
    for test_case in test_cases {
        let targets = [NativeExecutionTarget {
            repository_path: "pkg/defs/assets/example/main.py".to_owned(),
            scope: "root".to_owned(),
            root: "pkg".to_owned(),
            relative_parts: vec![
                "defs".to_owned(),
                "assets".to_owned(),
                "example".to_owned(),
                "main.py".to_owned(),
            ],
            direct: true,
            ownership_root: Some("pkg".to_owned()),
            ownership_offset: Some(0),
        }];
        let rules = [NativeExecutionRule::new(
            test_case.code.to_owned(),
            test_case.family.to_owned(),
            test_case.owner.to_owned(),
        )];

        let error = plan_execution_owners(&targets, &rules)
            .expect_err("applicable rule without an owner must fail");

        assert_eq!(error, test_case.expected_error, "{}", test_case.description);
    }
}

#[test]
fn given_same_named_domains_in_sibling_groups_when_planning_then_each_leaf_executes() {
    let test_cases = [test_types::GroupedExecutionPlanningTestCase {
        description: "physical group prefixes keep same-named domain leaves distinct",
        expected_planned_targets: 2,
    }];
    for test_case in test_cases {
        let targets = [
            NativeExecutionTarget {
                repository_path: "src/example/sources/orders/main/process.py".to_owned(),
                scope: "root".to_owned(),
                root: "src/example".to_owned(),
                relative_parts: ["sources", "orders", "main", "process.py"]
                    .into_iter()
                    .map(str::to_owned)
                    .collect(),
                direct: true,
                ownership_root: Some("src/example/sources".to_owned()),
                ownership_offset: Some(1),
            },
            NativeExecutionTarget {
                repository_path: "src/example/platform/orders/main/report.py".to_owned(),
                scope: "root".to_owned(),
                root: "src/example".to_owned(),
                relative_parts: ["platform", "orders", "main", "report.py"]
                    .into_iter()
                    .map(str::to_owned)
                    .collect(),
                direct: true,
                ownership_root: Some("src/example/platform".to_owned()),
                ownership_offset: Some(1),
            },
        ];
        let rules = [NativeExecutionRule::new(
            "FFR309".to_owned(),
            "roles".to_owned(),
            "leaf".to_owned(),
        )];

        let plans = plan_execution_owners(&targets, &rules).expect("grouped leaves plan");

        assert_eq!(
            plans.iter().filter(|plan| plan.codes == ["FFR309"]).count(),
            test_case.expected_planned_targets,
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_runtime_root_and_domain_modules_when_checking_roles_then_enforces_domain_ownership() {
    let test_cases = [
        test_types::TopLevelDirectModuleTestCase {
            description: "runtime root config module is rejected",
            repository_path: "src/example/config.py",
            relative_parts: &["config.py"],
            source: "value: int = 1\n",
            expected_fault_count: 1,
        },
        test_types::TopLevelDirectModuleTestCase {
            description: "runtime root model role module is rejected",
            repository_path: "src/example/models.py",
            relative_parts: &["models.py"],
            source: "value: int = 1\n",
            expected_fault_count: 1,
        },
        test_types::TopLevelDirectModuleTestCase {
            description: "runtime root constants role module is rejected",
            repository_path: "src/example/constants.py",
            relative_parts: &["constants.py"],
            source: "value: int = 1\n",
            expected_fault_count: 1,
        },
        test_types::TopLevelDirectModuleTestCase {
            description: "runtime root pure re-export facade is allowed",
            repository_path: "src/example/orders.py",
            relative_parts: &["orders.py"],
            source: "from example.orders.models import Order\n\n__all__ = (\"Order\",)\n",
            expected_fault_count: 0,
        },
        test_types::TopLevelDirectModuleTestCase {
            description: "runtime root forwarding facade is allowed",
            repository_path: "src/example/orders.py",
            relative_parts: &["orders.py"],
            source: "from example.orders.main.create_order import create_order as _create_order\n\n__all__ = (\"create_order\",)\n\ndef create_order(*, number: str) -> object:\n    return _create_order(number=number)\n",
            expected_fault_count: 0,
        },
        test_types::TopLevelDirectModuleTestCase {
            description: "runtime root context manager facade is allowed",
            repository_path: "src/example/orders.py",
            relative_parts: &["orders.py"],
            source: "from collections.abc import Iterator\nfrom contextlib import contextmanager\nfrom example.orders.main.order_scope import order_scope as _order_scope\n\n__all__ = (\"order_scope\",)\n\n@contextmanager\ndef order_scope(order_id: str) -> Iterator[str]:\n    with _order_scope(order_id) as active_id:\n        yield active_id\n",
            expected_fault_count: 0,
        },
        test_types::TopLevelDirectModuleTestCase {
            description: "runtime root context manager with transformed yield is rejected",
            repository_path: "src/example/orders.py",
            relative_parts: &["orders.py"],
            source: "from collections.abc import Iterator\nfrom contextlib import contextmanager\nfrom example.orders.main.order_scope import order_scope as _order_scope\n\n__all__ = (\"order_scope\",)\n\n@contextmanager\ndef order_scope(callback: object) -> Iterator[object]:\n    with _order_scope() as active:\n        yield callback(active)\n",
            expected_fault_count: 1,
        },
        test_types::TopLevelDirectModuleTestCase {
            description: "runtime root compatibility subclass facade is allowed",
            repository_path: "src/example/orders.py",
            relative_parts: &["orders.py"],
            source: "from example.orders.classes.order_store import OrderStore as _OrderStore\n\n__all__ = (\"OrderStore\",)\n\nclass OrderStore(_OrderStore):\n    \"\"\"Supported public order store.\"\"\"\n",
            expected_fault_count: 0,
        },
        test_types::TopLevelDirectModuleTestCase {
            description: "runtime root imported type alias facade is allowed",
            repository_path: "src/example/orders.py",
            relative_parts: &["orders.py"],
            source: "from example.orders.types import OrderStore\n\nPublicOrderStore: type[OrderStore] = OrderStore\n\n__all__ = (\"PublicOrderStore\",)\n",
            expected_fault_count: 0,
        },
        test_types::TopLevelDirectModuleTestCase {
            description: "runtime root overload facade is allowed",
            repository_path: "src/example/orders.py",
            relative_parts: &["orders.py"],
            source: "from typing import overload\nfrom example.orders.main.read_order import read_order as _read_order\n\n__all__ = (\"read_order\",)\n\n@overload\ndef read_order(number: str) -> str: ...\n\ndef read_order(number: object) -> object:\n    return _read_order(number)\n",
            expected_fault_count: 0,
        },
        test_types::TopLevelDirectModuleTestCase {
            description: "runtime root wrapper without static exports is rejected",
            repository_path: "src/example/orders.py",
            relative_parts: &["orders.py"],
            source: "from example.orders.main.create_order import create_order as _create_order\n\ndef create_order(*, number: str) -> object:\n    return _create_order(number=number)\n",
            expected_fault_count: 1,
        },
        test_types::TopLevelDirectModuleTestCase {
            description: "runtime root facade with branching implementation is rejected",
            repository_path: "src/example/orders.py",
            relative_parts: &["orders.py"],
            source: "from example.orders.main.create_order import create_order as _create_order\n\n__all__ = (\"create_order\",)\n\ndef create_order(*, number: str | None = None) -> object:\n    if number is None:\n        number = \"unknown\"\n    return _create_order(number=number)\n",
            expected_fault_count: 1,
        },
        test_types::TopLevelDirectModuleTestCase {
            description: "runtime root facade with an import-time default call is rejected",
            repository_path: "src/example/orders.py",
            relative_parts: &["orders.py"],
            source: "from types import MappingProxyType\nfrom example.orders.main.create_order import create_order as _create_order\n\n__all__ = (\"create_order\",)\n\ndef create_order(meta: object = MappingProxyType({})) -> object:\n    return _create_order(meta)\n",
            expected_fault_count: 1,
        },
        test_types::TopLevelDirectModuleTestCase {
            description: "runtime root overload with an import-time default call is rejected",
            repository_path: "src/example/orders.py",
            relative_parts: &["orders.py"],
            source: "from typing import overload\nfrom example.orders.main.configure import configure\nfrom example.orders.main.read_order import read_order as _read_order\n\n__all__ = (\"read_order\",)\n\n@overload\ndef read_order(number: str = configure()) -> str: ...\n\ndef read_order(number: object) -> object:\n    return _read_order(number)\n",
            expected_fault_count: 1,
        },
        test_types::TopLevelDirectModuleTestCase {
            description: "runtime root all annotation with an import-time call is rejected",
            repository_path: "src/example/orders.py",
            relative_parts: &["orders.py"],
            source: "from example.orders.main.configure import configure\nfrom example.orders.models import Order\n\n__all__: configure() = (\"Order\",)\n",
            expected_fault_count: 1,
        },
        test_types::TopLevelDirectModuleTestCase {
            description: "runtime root wrapper with a shadowing parameter is rejected",
            repository_path: "src/example/orders.py",
            relative_parts: &["orders.py"],
            source: "from example.orders.main.run import callback\n\n__all__ = (\"run\",)\n\ndef run(callback: object) -> object:\n    return callback()\n",
            expected_fault_count: 1,
        },
        test_types::TopLevelDirectModuleTestCase {
            description: "runtime root wrapper shadowing its imported target is rejected",
            repository_path: "src/example/orders.py",
            relative_parts: &["orders.py"],
            source: "from example.orders.main.run import run\n\n__all__ = (\"run\",)\n\ndef run() -> object:\n    return run()\n",
            expected_fault_count: 1,
        },
        test_types::TopLevelDirectModuleTestCase {
            description: "runtime root wrappers shadowing each other's imported targets are rejected",
            repository_path: "src/example/orders.py",
            relative_parts: &["orders.py"],
            source: "from example.orders.main.run import first, second\n\n__all__ = (\"first\", \"second\")\n\ndef first() -> object:\n    return second()\n\ndef second() -> object:\n    return first()\n",
            expected_fault_count: 1,
        },
        test_types::TopLevelDirectModuleTestCase {
            description: "runtime root facade with module state is rejected",
            repository_path: "src/example/orders.py",
            relative_parts: &["orders.py"],
            source: "from example.orders.models import Order\n\n_CACHE: list[Order] = []\n__all__ = (\"Order\",)\n",
            expected_fault_count: 1,
        },
        test_types::TopLevelDirectModuleTestCase {
            description: "runtime root facade with an unresolved export is rejected",
            repository_path: "src/example/orders.py",
            relative_parts: &["orders.py"],
            source: "from example.orders.models import Order\n\n__all__ = (\"Order\", \"Missing\")\n",
            expected_fault_count: 1,
        },
        test_types::TopLevelDirectModuleTestCase {
            description: "runtime root facade without an owning-domain import is rejected",
            repository_path: "src/example/orders.py",
            relative_parts: &["orders.py"],
            source: "from pathlib import Path\n\n__all__ = (\"Path\",)\n",
            expected_fault_count: 1,
        },
        test_types::TopLevelDirectModuleTestCase {
            description: "runtime root initializer is allowed",
            repository_path: "src/example/__init__.py",
            relative_parts: &["__init__.py"],
            source: "value: int = 1\n",
            expected_fault_count: 0,
        },
        test_types::TopLevelDirectModuleTestCase {
            description: "runtime root module entrypoint is allowed",
            repository_path: "src/example/__main__.py",
            relative_parts: &["__main__.py"],
            source: "value: int = 1\n",
            expected_fault_count: 0,
        },
        test_types::TopLevelDirectModuleTestCase {
            description: "domain model role module is allowed",
            repository_path: "src/example/orders/models.py",
            relative_parts: &["orders", "models.py"],
            source: "value: int = 1\n",
            expected_fault_count: 0,
        },
        test_types::TopLevelDirectModuleTestCase {
            description: "ad hoc direct domain module is rejected",
            repository_path: "src/example/orders/config.py",
            relative_parts: &["orders", "config.py"],
            source: "value: int = 1\n",
            expected_fault_count: 1,
        },
        test_types::TopLevelDirectModuleTestCase {
            description: "subdomain model role module is left to nested role policy",
            repository_path: "src/example/orders/fulfillment/models.py",
            relative_parts: &["orders", "fulfillment", "models.py"],
            source: "value: int = 1\n",
            expected_fault_count: 0,
        },
    ];

    for test_case in test_cases {
        let program = ProgramHandle::parse_many(
            vec![test_case.source.to_owned()],
            PythonVersion {
                major: 3,
                minor: 12,
            },
        )
        .pop()
        .flatten()
        .expect("valid Python");
        let context = NativeRuleContext {
            scope: "root".to_owned(),
            repository_path: test_case.repository_path.to_owned(),
            relative_parts: test_case
                .relative_parts
                .iter()
                .map(|part| (*part).to_owned())
                .collect(),
            package_name: "example".to_owned(),
            ..NativeRuleContext::default()
        };
        let faults = evaluate_core_rules(
            &program,
            &[TOP_LEVEL_DIRECT_MODULES_CODE.to_owned()],
            &context,
            &NativeProjectPlane::default(),
        )
        .expect("top-level module policy evaluates");

        assert_eq!(
            faults.len(),
            test_case.expected_fault_count,
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_public_facade_when_runtime_code_imports_it_then_reports_inward_dependency() {
    let test_cases = [test_types::PublicFacadeImportTestCase {
        description: "runtime import through a public facade is rejected at the import",
        source: "from example.orders import Order\n",
        expected_fault_count: 1,
        expected_path: None,
        expected_message: "runtime modules must import the facade's owning domain directly",
    }];
    let version = PythonVersion {
        major: 3,
        minor: 12,
    };
    for test_case in test_cases {
        let program = ProgramHandle::parse_many(vec![test_case.source.to_owned()], version)
            .pop()
            .flatten()
            .expect("valid Python");
        let context = NativeRuleContext {
            scope: "root".to_owned(),
            repository_path: "src/example/billing/main/create_invoice.py".to_owned(),
            relative_parts: vec![
                "billing".to_owned(),
                "main".to_owned(),
                "create_invoice.py".to_owned(),
            ],
            package_name: "example".to_owned(),
            scope_roots: vec![("root".to_owned(), "src/example".to_owned())],
            observations: HashMap::from([(
                "public_facade\0src/example/orders.py\0example".to_owned(),
                vec!["true".to_owned()],
            )]),
            ..NativeRuleContext::default()
        };

        let faults = evaluate_core_rules(
            &program,
            &["FFR310".to_owned()],
            &context,
            &NativeProjectPlane::default(),
        )
        .expect("public facade direction policy evaluates");

        assert_eq!(
            faults.len(),
            test_case.expected_fault_count,
            "{}",
            test_case.description
        );
        assert_eq!(
            faults[0].path.as_deref(),
            test_case.expected_path,
            "{}",
            test_case.description
        );
        assert_eq!(
            faults[0].message.as_deref(),
            Some(test_case.expected_message),
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_call_without_reference_parts_when_checking_autoload_then_skips_unresolvable_call() {
    let test_cases = [test_types::AutoloadEmptyCallTestCase {
        description: "direct lambda call has no traversable module or function reference",
        source: "import dagster as dg\n\n@dg.definitions\ndef definitions() -> dg.Definitions:\n    (lambda: None)()\n    return dg.Definitions()\n",
        expected_fault_count: 0,
    }];
    for test_case in test_cases {
        let program = ProgramHandle::parse_many(
            vec![test_case.source.to_owned()],
            PythonVersion {
                major: 3,
                minor: 12,
            },
        )
        .pop()
        .flatten()
        .expect("valid Python");
        assert!(
            program
                .named_call_rows()
                .iter()
                .any(|call| call.reference.parts.is_empty()),
            "{}",
            test_case.description
        );
        let context = NativeRuleContext {
            repository_path: "pkg/defs/resources/example.py".to_owned(),
            relative_parts: vec![
                "defs".to_owned(),
                "resources".to_owned(),
                "example.py".to_owned(),
            ],
            package_name: "pkg".to_owned(),
            rule_options: HashMap::from([(
                DAGSTER_AUTOLOAD_EXTERNAL_DISCOVERY_CODE.to_owned(),
                HashMap::from([("approved_loader_boundaries".to_owned(), "[]".to_owned())]),
            )]),
            ..NativeRuleContext::default()
        };
        let project = NativeProjectPlane::new(
            vec![NativeProjectModule::new(
                context.repository_path.clone(),
                "root".to_owned(),
                vec![
                    "pkg".to_owned(),
                    "defs".to_owned(),
                    "resources".to_owned(),
                    "example".to_owned(),
                ],
                program.clone(),
            )],
            Vec::new(),
        );

        let faults = evaluate_core_rules(
            &program,
            &[DAGSTER_AUTOLOAD_EXTERNAL_DISCOVERY_CODE.to_owned()],
            &context,
            &project,
        )
        .expect("unresolvable calls are skipped");

        assert_eq!(
            faults.len(),
            test_case.expected_fault_count,
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_undeclared_native_option_when_evaluating_then_value_is_rejected_not_ignored() {
    let test_cases = [test_types::NativeOptionRejectionTestCase {
        description: "undeclared native option is transported and rejected",
        code: "FFA001",
        option_name: "mode",
        option_value: "\"strict\"",
        expected_error_fragment: "does not declare option mode",
        expected_stored_value: "\"strict\"",
    }];
    for test_case in test_cases {
        let program = ProgramHandle::parse_many(
            vec!["def run(value):\n    return value\n".to_owned()],
            PythonVersion {
                major: 3,
                minor: 12,
            },
        )
        .pop()
        .flatten()
        .expect("valid Python");
        let context = NativeRuleContext {
            rule_options: HashMap::from([(
                test_case.code.to_owned(),
                HashMap::from([(
                    test_case.option_name.to_owned(),
                    test_case.option_value.to_owned(),
                )]),
            )]),
            ..NativeRuleContext::default()
        };

        let error = evaluate_core_rules(
            &program,
            &[test_case.code.to_owned()],
            &context,
            &NativeProjectPlane::default(),
        )
        .expect_err("undeclared native option must fail");

        assert!(
            error.contains(test_case.expected_error_fragment),
            "{}",
            test_case.description
        );
        assert_eq!(
            context.option(test_case.code, test_case.option_name),
            Some(test_case.expected_stored_value),
            "{}",
            test_case.description
        );
    }
}
