use crate::helpers::{
    poison_processes, require_workspace_python, run_internal_web_check_with, write,
};
use crate::test_types::{
    WebCustomCacheTestCase, WebCustomCoverageTestCase, WebCustomPolicyTestCase,
    WebCustomRoutingTestCase, WebCustomRuleTestCase,
};

#[test]
fn given_selected_typescript_rule_when_checking_then_owned_facts_and_graph_emit_fault() {
    let python = require_workspace_python!();
    let test_cases = [WebCustomRuleTestCase {
        description: "typed TypeScript rule reads owned imports and the resolved graph",
        expected_exit_code: 1,
        expected_code: "XWEB001",
        expected_location: "src/main.ts:1:0",
        expected_message: "src/value.ts",
        expected_count: 1,
    }];
    for test_case in test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        write(
            repository.path().join("src/main.ts"),
            "import { value } from '@/value';\nexport function run(): number { return value(); }\n",
        );
        write(
            repository.path().join("src/value.ts"),
            "export interface Product { readonly id: string; }\nexport class ValueService {}\nexport function value(): number { return 1; }\n",
        );
        write(
            repository.path().join("tsconfig.json"),
            "{\"compilerOptions\":{\"baseUrl\":\".\",\"paths\":{\"@/*\":[\"src/*\"]}}}\n",
        );
        write(
            repository.path().join("rules/custom.py"),
            "from fensu import AnalyzerId, Family, Fault, File, ProjectPath, RuleContext, RuleOption, WebSyntaxKind, rule\nTARGET = RuleOption.string(name='target', default='value.ts')\n@rule(code='XWEB001', family=Family.CUSTOM, slug='resolved-import', message='resolved import', analyzers=(AnalyzerId.TYPESCRIPT,), options=(TARGET,), cacheable=True)\ndef resolved_import(*, file: File, ctx: RuleContext) -> list[Fault]:\n    facts = ctx.web.file(file)\n    target_facts = ctx.web.file(ProjectPath('src/value.ts'))\n    position = ctx.project.tree.position(file.path)\n    node = ctx.graph.node(file)\n    if facts is None or not facts.imports or target_facts is None or position is None or node is None:\n        return []\n    edge = ctx.graph.imports(file)[0]\n    handle = next(item for item in facts.syntax_handles if item.kind is WebSyntaxKind.IMPORT)\n    message = edge.target.file.path.value if edge.target is not None else 'missing'\n    authored = facts.text(handle)\n    semantic = bool(facts.calls and target_facts.classes and target_facts.models and target_facts.functions)\n    ownership = node.domain_parts == position.domain_parts\n    return [ctx.fault_at(location=facts.imports[0].location, message=message)] if message.endswith(ctx.option(TARGET)) and authored and semantic and ownership else []\n",
        );
        write(
            repository.path().join("fensu.toml"),
            "[targets.web]\nanalyzer = \"typescript\"\nroots = [\"src\"]\ntests = []\ntooling = []\nrule_paths = [\"rules/custom.py\"]\nselect = [\"XWEB001\"]\n[targets.web.rule_options.XWEB001]\ntarget = \"value.ts\"\n",
        );
        let process_directory = poison_processes(repository.path());

        let output = std::process::Command::new(env!("CARGO_BIN_EXE_fensu"))
            .args(["check", "--no-color", "--no-cache"])
            .current_dir(repository.path())
            .env("FENSU_PYTHON", &python)
            .env("PATH", &process_directory)
            .env(
                "FENSU_PROCESS_MARKER",
                repository.path().join("process-invoked"),
            )
            .output()
            .expect("custom TypeScript check runs");
        let stdout = String::from_utf8_lossy(&output.stdout);
        let stderr = String::from_utf8_lossy(&output.stderr);

        assert_eq!(
            output.status.code(),
            Some(test_case.expected_exit_code),
            "{}: {stdout} {stderr}",
            test_case.description
        );
        assert!(
            !repository.path().join("process-invoked").exists(),
            "{}: selected custom TypeScript rules must remain Node-free",
            test_case.description
        );
        assert!(
            stdout.contains(test_case.expected_code),
            "{}: {stdout}",
            test_case.description
        );
        assert!(
            stdout.contains(test_case.expected_location),
            "{}: {stdout}",
            test_case.description
        );
        assert!(
            stdout.contains(test_case.expected_message),
            "{}: {stdout}",
            test_case.description
        );
        assert_eq!(
            stdout.matches(test_case.expected_code).count(),
            test_case.expected_count,
            "{}: {stdout}",
            test_case.description
        );
    }
}

#[test]
fn given_typescript_custom_rule_when_checking_coverage_then_public_harness_is_required() {
    let python = require_workspace_python!();
    let test_cases = [WebCustomCoverageTestCase {
        description: "TypeScript custom-rule coverage requires a public harness",
        expected_uncovered_exit_code: 1,
        expected_covered_exit_code: 0,
        expected_code: "FFR707",
        expected_zero_faults: "Found 0 faults",
    }];
    for test_case in test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        write(
            repository.path().join("src/main.ts"),
            "export function main(): number { return 1; }\n",
        );
        write(repository.path().join("rules/__init__.py"), "");
        write(
        repository.path().join("rules/custom.py"),
        "from fensu import AnalyzerId, Family, Fault, Project, RuleContext, rule\n@rule(code='XWEB707', family=Family.CUSTOM, slug='web-policy', message='web policy', analyzers=(AnalyzerId.TYPESCRIPT,), cacheable=True)\ndef web_policy(*, project: Project, ctx: RuleContext) -> list[Fault]:\n    del project, ctx\n    return []\n",
    );
        write(
        repository.path().join("fensu.toml"),
        "[targets.web]\nanalyzer = \"typescript\"\nroots = [\"src\"]\ntests = [\"policy_tests\"]\ntooling = []\nrule_packs = [\"typescript\"]\nrule_paths = [\"rules/custom.py\"]\nselect = [\"FFR707\"]\n",
    );

        let uncovered = std::process::Command::new(env!("CARGO_BIN_EXE_fensu"))
            .args(["check", "--no-color", "--no-cache"])
            .current_dir(repository.path())
            .env("FENSU_PYTHON", &python)
            .output()
            .expect("uncovered custom TypeScript rule check runs");
        write(
        repository.path().join("policy_tests/test_custom.py"),
        "from fensu import RuleCase, evaluate_rule\nfrom rules.custom import web_policy\n\ndef test_given_project_when_checking_then_matches() -> None:\n    evaluate_rule(rule=web_policy, test_case=RuleCase(description='covered', source='VALUE: int = 1', expected_fault_count=0))\n",
    );
        let covered = std::process::Command::new(env!("CARGO_BIN_EXE_fensu"))
            .args(["check", "--no-color", "--no-cache"])
            .current_dir(repository.path())
            .env("FENSU_PYTHON", &python)
            .output()
            .expect("covered custom TypeScript rule check runs");
        let uncovered_stdout = String::from_utf8_lossy(&uncovered.stdout);
        let covered_stdout = String::from_utf8_lossy(&covered.stdout);

        assert_eq!(
            uncovered.status.code(),
            Some(test_case.expected_uncovered_exit_code),
            "{}: {uncovered_stdout}",
            test_case.description
        );
        assert!(
            uncovered_stdout.contains(test_case.expected_code),
            "{}: {uncovered_stdout}",
            test_case.description
        );
        assert!(
            uncovered_stdout.contains("custom rule XWEB707 has 0 statically declared test cases"),
            "{}: {uncovered_stdout}",
            test_case.description
        );
        assert_eq!(
            covered.status.code(),
            Some(test_case.expected_covered_exit_code),
            "{}: {covered_stdout}",
            test_case.description
        );
        assert!(
            covered_stdout.contains(test_case.expected_zero_faults),
            "{}: {covered_stdout}",
            test_case.description
        );
    }
}

#[test]
fn given_selected_svelte_rule_when_checking_then_route_and_rune_facts_emit_fault() {
    let python = require_workspace_python!();
    let test_cases = [WebCustomRuleTestCase {
        description: "typed Svelte rule reads route and rune facts",
        expected_exit_code: 1,
        expected_code: "XWEB002",
        expected_location: "src/routes/+page.svelte:2:14",
        expected_message: "route owns state",
        expected_count: 1,
    }];
    for test_case in test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        write(
            repository.path().join("src/routes/+page.svelte"),
            "<script lang=\"ts\">\n  let count = $state(0);\n</script>\n<button>{count}</button>\n",
        );
        write(
            repository.path().join("src/lib/state/session.svelte.ts"),
            "export const session = $state({ user: null });\nconst label = $format('ready');\nexport function createState() { return $state({ user: null }); }\n",
        );
        write(
            repository.path().join("rules/custom.py"),
            "from fensu import AnalyzerId, Family, Fault, File, ProjectPath, RuleContext, rule\n@rule(code='XWEB002', family=Family.CUSTOM, slug='route-state', message='route owns state', analyzers=(AnalyzerId.SVELTE,), cacheable=True)\ndef route_state(*, file: File, ctx: RuleContext) -> list[Fault]:\n    facts = ctx.facts\n    state = ctx.web.file(ProjectPath('src/lib/state/session.svelte.ts'))\n    if facts.svelte is None or not facts.svelte.route or state is None or state.svelte is None or not state.svelte.state_module:\n        return []\n    runes = state.svelte.module_runes\n    if len(runes) != 1 or runes[0].name != '$state':\n        return []\n    return [ctx.fault_at(location=rune.location) for rune in facts.svelte.module_runes if rune.name == '$state']\n",
        );
        write(
            repository.path().join("fensu.toml"),
            "[targets.web]\nanalyzer = \"svelte\"\nroots = [\"src\"]\ntests = []\ntooling = []\nrule_paths = [\"rules/custom.py\"]\nselect = [\"XWEB002\"]\n",
        );

        let output = std::process::Command::new(env!("CARGO_BIN_EXE_fensu"))
            .args(["check", "--no-color", "--no-cache"])
            .current_dir(repository.path())
            .env("FENSU_PYTHON", &python)
            .output()
            .expect("custom Svelte check runs");
        let stdout = String::from_utf8_lossy(&output.stdout);
        let stderr = String::from_utf8_lossy(&output.stderr);

        assert_eq!(
            output.status.code(),
            Some(test_case.expected_exit_code),
            "{}: {stdout} {stderr}",
            test_case.description
        );
        assert!(
            stdout.contains(test_case.expected_code),
            "{}: {stdout}",
            test_case.description
        );
        assert!(
            stdout.contains(test_case.expected_location),
            "{}: {stdout}",
            test_case.description
        );
        assert!(
            stdout.contains(test_case.expected_message),
            "{}: {stdout}",
            test_case.description
        );
        assert_eq!(
            stdout.matches(test_case.expected_code).count(),
            test_case.expected_count,
            "{}: {stdout}",
            test_case.description
        );
    }
}

#[test]
fn given_unselected_custom_web_rule_when_checking_then_python_host_does_not_start() {
    let test_cases = [
        WebCustomRoutingTestCase {
            description: "unselected TypeScript custom rule remains Python-free",
            analyzer: "typescript",
            source_path: "src/valid.ts",
            source: "export const valid: number = 1;\n",
            selection: "select = []\n",
            expected_exit_code: 0,
            expected_present: "Found 0 faults",
            expected_absent: "host started",
        },
        WebCustomRoutingTestCase {
            description: "unselected Svelte custom rule remains Python-free",
            analyzer: "svelte",
            source_path: "src/valid.svelte",
            source: "<p>valid</p>\n",
            selection: "select = [\"XWEB\"]\nignore = [\"X\"]\n",
            expected_exit_code: 0,
            expected_present: "Found 0 faults",
            expected_absent: "host started",
        },
        WebCustomRoutingTestCase {
            description: "custom web options fail closed without starting an unselected host",
            analyzer: "typescript",
            source_path: "src/valid.ts",
            source: "export const valid: number = 1;\n",
            selection: "select = []\n[targets.web.rule_options.XWEB999]\nenabled = true\n",
            expected_exit_code: 2,
            expected_present: "Web custom rule options require a selected custom rule: XWEB999",
            expected_absent: "host started",
        },
    ];
    for test_case in test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        write(
            repository.path().join(test_case.source_path),
            test_case.source,
        );
        write(
            repository.path().join("rules/custom.py"),
            "raise RuntimeError('host started for an unselected custom rule')\n",
        );
        write(
            repository.path().join("fensu.toml"),
            &format!(
                "[targets.web]\nanalyzer = \"{}\"\nroots = [\"src\"]\ntests = []\ntooling = []\nrule_paths = [\"rules/custom.py\"]\n{}",
                test_case.analyzer, test_case.selection
            ),
        );
        let process_directory = poison_processes(repository.path());

        let output =
            run_internal_web_check_with(repository.path(), &["--no-cache"], &process_directory);
        let stderr = String::from_utf8_lossy(&output.stderr);
        let stdout = String::from_utf8_lossy(&output.stdout);
        let combined = format!("{stdout}{stderr}");

        assert_eq!(
            output.status.code(),
            Some(test_case.expected_exit_code),
            "{}: {stderr}",
            test_case.description
        );
        assert!(
            combined.contains(test_case.expected_present),
            "{}: {combined}",
            test_case.description
        );
        assert!(
            !stderr.contains(test_case.expected_absent),
            "{}: {stderr}",
            test_case.description
        );
        assert!(
            !repository.path().join("process-invoked").exists(),
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_focused_web_fact_query_when_unrelated_file_changes_then_subject_cache_reuses_result() {
    let python = require_workspace_python!();
    let test_cases = [WebCustomCacheTestCase {
        description: "focused web file query survives an unrelated source edit",
        expected_initial: "src/first.ts",
        expected_reused: "reused narrow result",
        expected_changed: "src/second.ts",
        expected_code: "XWEB003",
        expected_exit_code: 1,
    }];
    for test_case in test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        write(
            repository.path().join("src/first.ts"),
            "import { second } from './second';\nexport const first: number = second;\n",
        );
        write(
            repository.path().join("src/second.ts"),
            "export const second: number = 2;\n",
        );
        write(repository.path().join("rules/__init__.py"), "");
        write(
            repository.path().join("rules/custom.py"),
            "from fensu import AnalyzerId, Family, Fault, File, RuleContext, rule\n@rule(code='XWEB003', family=Family.CUSTOM, slug='narrow-cache', message='narrow cache', analyzers=(AnalyzerId.TYPESCRIPT,), cacheable=True)\ndef narrow_cache(*, file: File, ctx: RuleContext) -> list[Fault]:\n    facts = ctx.web.file(file)\n    edges = ctx.graph.imports(file)\n    return [] if facts is None else [ctx.path_fault(message=file.path.value if not edges else edges[0].source.file.path.value)]\n",
        );
        write(
            repository.path().join("fensu.toml"),
            "[targets.web]\nanalyzer = \"typescript\"\nroots = [\"src\"]\ntests = []\ntooling = []\nrule_modules = [\"rules.custom\"]\nselect = [\"XWEB003\"]\n[targets.web.cache]\nenabled = true\nrequire_cacheable = true\n",
        );
        let run = || {
            std::process::Command::new(env!("CARGO_BIN_EXE_fensu"))
                .args(["check", "--no-color", "--cache"])
                .current_dir(repository.path())
                .env("FENSU_PYTHON", &python)
                .output()
                .expect("custom web cache check runs")
        };

        let before = run();
        let warm = run();
        assert_eq!(
            before.stdout, warm.stdout,
            "{}: cached and uncached diagnostics differ",
            test_case.description
        );
        let cache_path = repository.path().join(".fensu/cache/web-custom-v1.json");
        let cache = std::fs::read_to_string(&cache_path).expect("custom web subject cache");
        let marked = cache.replace(
            &format!("\"message\":\"{}\"", test_case.expected_initial),
            &format!("\"message\":\"{}\"", test_case.expected_reused),
        );
        assert_ne!(cache, marked, "{}", test_case.description);
        std::fs::write(&cache_path, marked).expect("cache marker");
        write(
            repository.path().join("src/second.ts"),
            "export const second: number = 3;\n",
        );
        let after = run();
        let before_stdout = String::from_utf8_lossy(&before.stdout);
        let after_stdout = String::from_utf8_lossy(&after.stdout);
        std::fs::write(&cache_path, [0xff]).expect("invalid UTF-8 cache fixture");
        write(
            repository.path().join("src/second.ts"),
            "export const second: number = 4;\n",
        );
        let corrupted = run();
        let corrupted_stdout = String::from_utf8_lossy(&corrupted.stdout);

        assert!(
            before_stdout.contains(test_case.expected_initial),
            "{}: {before_stdout}",
            test_case.description
        );
        assert!(
            after_stdout.contains(test_case.expected_reused),
            "{}: {after_stdout}",
            test_case.description
        );
        assert!(
            after_stdout.contains(test_case.expected_changed),
            "{}: {after_stdout}",
            test_case.description
        );
        assert_eq!(
            corrupted.status.code(),
            Some(test_case.expected_exit_code),
            "{}: {corrupted_stdout}",
            test_case.description
        );
        assert!(
            corrupted_stdout.contains(test_case.expected_code),
            "{}: {corrupted_stdout}",
            test_case.description
        );
    }
}

#[test]
fn given_malformed_web_source_when_custom_rule_reads_facts_then_parse_error_remains_explicit() {
    let python = require_workspace_python!();
    let test_cases = [WebCustomRuleTestCase {
        description: "malformed source remains explicit in custom web facts",
        expected_exit_code: 1,
        expected_code: "XWEB004",
        expected_location: "src/malformed.ts",
        expected_message: "source did not parse",
        expected_count: 1,
    }];
    for test_case in test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        write(
            repository.path().join("src/malformed.ts"),
            "export const malformed: = 1;\n",
        );
        write(
            repository.path().join("rules/custom.py"),
            "from fensu import AnalyzerId, Family, Fault, File, RuleContext, rule\n@rule(code='XWEB004', family=Family.CUSTOM, slug='parse-evidence', message='source did not parse', analyzers=(AnalyzerId.TYPESCRIPT,), cacheable=True)\ndef parse_evidence(*, file: File, ctx: RuleContext) -> list[Fault]:\n    facts = ctx.web.file(file)\n    return [ctx.path_fault()] if facts is not None and facts.parse_error is not None else []\n",
        );
        write(
            repository.path().join("fensu.toml"),
            "[targets.web]\nanalyzer = \"typescript\"\nroots = [\"src\"]\ntests = []\ntooling = []\nrule_paths = [\"rules/custom.py\"]\nselect = [\"XWEB004\"]\n",
        );

        let output = std::process::Command::new(env!("CARGO_BIN_EXE_fensu"))
            .args(["check", "--no-color", "--no-cache"])
            .current_dir(repository.path())
            .env("FENSU_PYTHON", &python)
            .output()
            .expect("malformed custom web check runs");
        let stdout = String::from_utf8_lossy(&output.stdout);
        let stderr = String::from_utf8_lossy(&output.stderr);

        assert_eq!(
            output.status.code(),
            Some(test_case.expected_exit_code),
            "{}: {stdout} {stderr}",
            test_case.description
        );
        assert!(
            stdout.contains(test_case.expected_code),
            "{}: {stdout}",
            test_case.description
        );
        assert!(
            stdout.contains(test_case.expected_location),
            "{}: {stdout}",
            test_case.description
        );
        assert!(
            stdout.contains(test_case.expected_message),
            "{}: {stdout}",
            test_case.description
        );
        assert_eq!(
            stdout.matches(test_case.expected_code).count(),
            test_case.expected_count,
            "{}: {stdout}",
            test_case.description
        );
    }
}

#[test]
fn given_custom_web_project_rule_when_checking_then_rule_executes_once_without_source_anchor() {
    let python = require_workspace_python!();
    let test_cases = [WebCustomRuleTestCase {
        description: "typed web project rule executes once over the broad file inventory",
        expected_exit_code: 1,
        expected_code: "XWEB006",
        expected_location: "src/first.ts",
        expected_message: "2 web files",
        expected_count: 1,
    }];
    for test_case in test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        write(
            repository.path().join("src/first.ts"),
            "export const first = 1;\n",
        );
        write(
            repository.path().join("src/second.ts"),
            "export const second = 2;\n",
        );
        write(
            repository.path().join("rules/custom.py"),
            "from fensu import AnalyzerId, Family, Fault, Project, RuleContext, rule\n@rule(code='XWEB006', family=Family.CUSTOM, slug='project-files', message='web inventory', analyzers=(AnalyzerId.TYPESCRIPT,), cacheable=True)\ndef project_files(*, project: Project, ctx: RuleContext) -> list[Fault]:\n    del project\n    files = ctx.web.files\n    tree_files = ctx.project.tree.files\n    return [ctx.path_fault(path=files[0].file.path, message=f'{len(tree_files)} web files')]\n",
        );
        write(
            repository.path().join("fensu.toml"),
            "[targets.web]\nanalyzer = \"typescript\"\nroots = [\"src\"]\ntests = []\ntooling = []\nrule_paths = [\"rules/custom.py\"]\nselect = [\"XWEB006\"]\n",
        );

        let output = std::process::Command::new(env!("CARGO_BIN_EXE_fensu"))
            .args(["check", "--no-color", "--no-cache"])
            .current_dir(repository.path())
            .env("FENSU_PYTHON", &python)
            .output()
            .expect("custom web project check runs");
        let stdout = String::from_utf8_lossy(&output.stdout);
        let stderr = String::from_utf8_lossy(&output.stderr);

        assert_eq!(
            output.status.code(),
            Some(test_case.expected_exit_code),
            "{}: {stdout} {stderr}",
            test_case.description
        );
        assert!(
            stdout.contains(test_case.expected_location),
            "{}: {stdout}",
            test_case.description
        );
        assert!(
            stdout.contains(test_case.expected_message),
            "{}: {stdout}",
            test_case.description
        );
        assert_eq!(
            stdout.matches(test_case.expected_code).count(),
            test_case.expected_count,
            "{}: {stdout}",
            test_case.description
        );
    }
}

#[test]
fn given_custom_web_policy_when_checking_then_warning_ignore_and_exception_semantics_are_shared() {
    let python = require_workspace_python!();
    let test_cases = [
        WebCustomPolicyTestCase {
            description: "warning tier emits advisory custom web finding",
            selection: "select = []\nwarn = [\"XWEB005\"]\n",
            policy: "",
            arguments: &["--no-cache", "--warn"],
            expected_exit_code: 0,
            expected_present: "XWEB005",
            expected_absent: "Found 1 fault",
        },
        WebCustomPolicyTestCase {
            description: "scoped ignore suppresses custom web finding",
            selection: "select = [\"XWEB005\"]\n",
            policy: "[[targets.web.rule_ignores]]\nrules = [\"XWEB005\"]\npaths = [\"src/**\"]\nreason = \"Generated adapter.\"\n",
            arguments: &["--no-cache"],
            expected_exit_code: 0,
            expected_present: "Found 0 faults",
            expected_absent: "XWEB005 ",
        },
        WebCustomPolicyTestCase {
            description: "exact exception suppresses custom web finding",
            selection: "select = [\"XWEB005\"]\n",
            policy: "[[targets.web.rule_exceptions]]\nrule = \"XWEB005\"\npath = \"src/value.ts\"\nreason = \"Accepted adapter.\"\n",
            arguments: &["--no-cache"],
            expected_exit_code: 0,
            expected_present: "Applied 1 rule exception",
            expected_absent: "XWEB005 ",
        },
    ];
    for test_case in test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        write(
            repository.path().join("src/value.ts"),
            "export const value: number = 1;\n",
        );
        write(
            repository.path().join("rules/custom.py"),
            "from fensu import AnalyzerId, Family, Fault, File, RuleContext, rule\n@rule(code='XWEB005', family=Family.CUSTOM, slug='shared-policy', message='review web file', analyzers=(AnalyzerId.TYPESCRIPT,), cacheable=True)\ndef shared_policy(*, file: File, ctx: RuleContext) -> list[Fault]:\n    return [ctx.path_fault()]\n",
        );
        write(
            repository.path().join("fensu.toml"),
            &format!(
                "[targets.web]\nanalyzer = \"typescript\"\nroots = [\"src\"]\ntests = []\ntooling = []\nrule_paths = [\"rules/custom.py\"]\n{}{}",
                test_case.selection, test_case.policy
            ),
        );

        let output = std::process::Command::new(env!("CARGO_BIN_EXE_fensu"))
            .args(["check", "--no-color"])
            .args(test_case.arguments)
            .current_dir(repository.path())
            .env("FENSU_PYTHON", &python)
            .output()
            .expect("custom web policy check runs");
        let combined = format!(
            "{}{}",
            String::from_utf8_lossy(&output.stdout),
            String::from_utf8_lossy(&output.stderr)
        );

        assert_eq!(
            output.status.code(),
            Some(test_case.expected_exit_code),
            "{}: {combined}",
            test_case.description
        );
        assert!(
            combined.contains(test_case.expected_present),
            "{}: {combined}",
            test_case.description
        );
        assert!(
            !combined.contains(test_case.expected_absent),
            "{}: {combined}",
            test_case.description
        );
    }
}
