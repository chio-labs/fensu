use crate::helpers::{
    require_workspace_python, run_check_case, run_init_case, BASE, ENABLED, ROOT,
};
use crate::test_types::{CheckStep, CheckTestCase, InitTestCase};

#[test]
fn given_reachability_configuration_when_checking_then_faults_and_cache_follow_production_roots() {
    let test_cases = [
        CheckTestCase {
            description: "excluding the final production source leaves a stale configured root",
            config: format!("{BASE}[evaluation]\nexclude = ['**']\n{ENABLED}{ROOT}"),
            expected_steps: vec![CheckStep { status: 1, contains: &["FFL107"], ..Default::default() }],
        },
        CheckTestCase {
            description: "enabled, reasoned roots, and stale roots after dependency deletion",
            config: format!("{BASE}{ENABLED}"),
            expected_steps: vec![
                CheckStep { status: 1, contains: &["FFL106", "orders.service.main._parse.parse_orders", "orders.service.main.parse.parse_orders"], absent: &["unreachable function tests"], ..Default::default() },
                CheckStep { config: Some(format!("{BASE}{ENABLED}{ROOT}")), ..Default::default() },
                CheckStep { writes: vec![("src/orders/service/main/_parse.py", None), ("src/orders/service/main/parse.py", None)], status: 1, contains: &["FFL107"], ..Default::default() },
                CheckStep { config: Some(format!("{BASE}[[rule_exceptions]]\nrule = 'FFL107'\npath = 'fensu.toml'\nreason = 'Keep the integration registration pending its replacement.'\n{ENABLED}{ROOT}")), ..Default::default() },
            ],
        },
        CheckTestCase {
            description: "missing, disabled, and roots alone preserve prior behavior",
            config: BASE.to_owned(),
            expected_steps: vec![CheckStep::default(), CheckStep { config: Some(format!("{BASE}[dead_code]\nenabled = false\n")), ..Default::default() }, CheckStep { config: Some(format!("{BASE}{ROOT}")), ..Default::default() }],
        },
        CheckTestCase {
            description: "deleting the final root does not disable enforcement",
            config: format!("{BASE}{ENABLED}{ROOT}"),
            expected_steps: vec![CheckStep::default(), CheckStep { config: Some(format!("{BASE}{ENABLED}")), status: 1, contains: &["FFL106"], ..Default::default() }],
        },
        CheckTestCase {
            description: "project metadata edits invalidate cached reachability",
            config: format!("{BASE}{ENABLED}"),
            expected_steps: vec![
                CheckStep { writes: vec![("src/orders/__init__.py", Some("from .service.main._parse import parse_orders\n__all__ = ['parse_orders']\n")), ("pyproject.toml", Some("[project.scripts]\norders = 'orders.service.main.parse:parse_orders'\n"))], ..Default::default() },
                CheckStep { writes: vec![("pyproject.toml", Some("[project]\nname = 'orders'\n"))], status: 1, contains: &["orders.service.main.parse.parse_orders"], ..Default::default() },
            ],
        },
        CheckTestCase {
            description: "TOML and pyproject agree",
            config: format!("{BASE}{ENABLED}"),
            expected_steps: vec![CheckStep { status: 1, contains: &["FFL106"], ..Default::default() }, CheckStep { writes: vec![("fensu.toml", None), ("pyproject.toml", Some("[tool.fensu]\nroots = ['src/orders']\ntests = ['tests']\nselect = []\n[tool.fensu.dead_code]\nenabled = true\n"))], status: 1, contains: &["FFL106"], ..Default::default() }],
        },
        CheckTestCase {
            description: "gitignored and hidden files remain selected; explicit excludes win",
            config: format!("{BASE}{ENABLED}{ROOT}"),
            expected_steps: vec![
                CheckStep { writes: vec![(".gitignore", Some("build/\n.hidden/\n")), ("src/orders/build/unused.py", Some("def orphan(): pass\n")), ("src/orders/.hidden/unused.py", Some("def hidden(): pass\n"))], status: 1, contains: &["orphan", "hidden"], ..Default::default() },
                CheckStep { config: Some(format!("{BASE}[evaluation]\nexclude = ['src/orders/build/**', 'src/orders/.hidden/**']\n{ENABLED}{ROOT}")), ..Default::default() },
            ],
        },
        CheckTestCase {
            description: "malformed keys, types, reasons, and patterns fail validation",
            config: format!("{BASE}[dead_code]\nenable = true\n"),
            expected_steps: vec![
                CheckStep { status: 2, ..Default::default() },
                CheckStep { config: Some(format!("{BASE}[dead_code]\nenabled = 'yes'\n")), status: 2, ..Default::default() },
                CheckStep { config: Some(format!("{BASE}[[dead_code.roots]]\nmodules = ['orders.*']\nsymbols = ['*']\n")), status: 2, ..Default::default() },
                CheckStep { config: Some(format!("{BASE}[[dead_code.roots]]\nmodules = ['[']\nsymbols = ['*']\nreason = 'Dispatch.'\n")), status: 2, ..Default::default() },
            ],
        },
        CheckTestCase {
            description: "named Python target reports stale configuration at its actual owner",
            config: "[targets.backend]\nanalyzer = 'python'\nroot = 'backend'\nroots = ['src/orders']\ntests = []\nselect = []\n[targets.backend.dead_code]\nenabled = true\n[[targets.backend.dead_code.roots]]\nmodules = ['orders.missing']\nsymbols = ['*']\nreason = 'Plugin registration.'\n".to_owned(),
            expected_steps: vec![CheckStep { writes: vec![("backend/src/orders/__init__.py", Some(""))], status: 1, contains: &["FFL107", "fensu.toml"], absent: &["backend/fensu.toml"], ..Default::default() }],
        },
    ];
    for test_case in test_cases {
        let actual = run_check_case(&test_case, None);
        assert_eq!(
            actual,
            test_case
                .expected_steps
                .iter()
                .map(|step| step.status)
                .collect::<Vec<_>>(),
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_new_or_existing_python_code_when_initializing_then_only_blank_scaffolding_enables_dead_code(
) {
    let test_cases = [
        InitTestCase {
            description: "blank Python project",
            arguments: &["--yes", "--name", "orders"],
            files: &[],
            expected_enabled: true,
        },
        InitTestCase {
            description: "adoption of existing Python code",
            arguments: &["--yes", "--root", "src/orders"],
            files: &[("src/orders/__init__.py", "")],
            expected_enabled: false,
        },
    ];
    for test_case in test_cases {
        assert_eq!(
            run_init_case(&test_case),
            test_case.expected_enabled,
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_custom_python_rules_when_checking_then_reachability_and_cache_match_native_mode() {
    let python = require_workspace_python!();
    let test_cases = [CheckTestCase {
        description: "custom Python host roots, excludes, and cache identity",
        config: format!("{BASE}rule_paths = ['rules.py']\n{ENABLED}"),
        expected_steps: vec![
            CheckStep { writes: vec![("rules.py", Some("from fensu import Family, Fault, File, RuleContext, rule\n@rule(code='XORD001', family=Family.CUSTOM, slug='orders', message='orders', cacheable=True)\ndef check_orders(*, file: File, ctx: RuleContext) -> list[Fault]:\n    return []\n"))], status: 1, contains: &["FFL106", "orders.service.main._parse.parse_orders"], ..Default::default() },
            CheckStep { writes: vec![("pyproject.toml", Some("[project.scripts]\norders = 'orders.service.main._parse:parse_orders'\nparse = 'orders.service.main.parse:parse_orders'\n"))], ..Default::default() },
            CheckStep { writes: vec![("pyproject.toml", None)], status: 1, contains: &["FFL106"], ..Default::default() },
            CheckStep { config: Some(format!("{BASE}rule_paths = ['rules.py']\n{ENABLED}{ROOT}")), ..Default::default() },
            CheckStep { config: Some(format!("{BASE}rule_paths = ['rules.py']\n[evaluation]\nexclude = ['src/orders/service/**']\n{ENABLED}")), ..Default::default() },
            CheckStep { config: Some(format!("{BASE}rule_paths = ['rules.py']\n[evaluation]\nexclude = ['**']\n{ENABLED}{ROOT}")), status: 1, contains: &["FFL107"], ..Default::default() },
        ],
    }];
    for test_case in test_cases {
        let actual = run_check_case(&test_case, Some(&python));
        assert_eq!(
            actual,
            test_case
                .expected_steps
                .iter()
                .map(|step| step.status)
                .collect::<Vec<_>>(),
            "{}",
            test_case.description
        );
    }
}
