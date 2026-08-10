use crate::helpers::{poison_processes, run_internal_web_check_with, run_web_command, write};
use crate::test_types::{
    HostedWebPolicyTestCase, InternalGateCommandTestCase, WebCacheCheckTestCase,
    WebConfigFailureTestCase, WebExceptionOwnerTestCase, WebParseDiagnosticTestCase,
    WebPolicyCheckTestCase, WebSourcePurposeTestCase, WebTestCaseTypeResolutionTestCase,
};

const CONFIG: &str = "[targets.a_typescript]\nanalyzer = \"typescript\"\nroots = [\"src\"]\ntests = []\ntooling = []\nselect = []\n\n[targets.a_typescript.cache]\nenabled = true\n\n[targets.a_typescript.evaluation]\nexclude = [\"src/lib/value.ts\"]\n\n[targets.b_svelte]\nanalyzer = \"svelte\"\nroots = [\"src\"]\ntests = []\ntooling = []\nselect = []\n\n[targets.b_svelte.cache]\nenabled = true\n";
const VALID_COMPONENT: &str = "<script lang=\"ts\">\nimport { value } from '$lib/value';\nconst doubled: number = value * 2;\n</script>\n<p>{doubled}</p>\n";
const VALID_TYPESCRIPT: &str = "export const value: number = 2;\n";

#[test]
fn given_web_method_exception_when_checking_then_qualified_owner_disambiguates_repeated_names() {
    let test_cases = [
        WebExceptionOwnerTestCase {
            description: "qualified class method suppresses only its own diagnostic",
            symbol: "First.run",
            expected_exit_code: 1,
            expected_stdout: "src/classes.ts:2:",
            expected_stderr: "",
        },
        WebExceptionOwnerTestCase {
            description: "unqualified repeated method name is rejected as ambiguous",
            symbol: "run",
            expected_exit_code: 2,
            expected_stdout: "",
            expected_stderr: "Rule exception symbol is ambiguous in src/classes.ts: run.",
        },
    ];
    for test_case in &test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        write(
            repository.path().join("fensu.toml"),
            &format!(
                "[targets.web]\nanalyzer = \"typescript\"\nroots = [\"src\"]\ntests = []\ntooling = []\nselect = [\"FWS010\"]\n[targets.web.thresholds]\nmax_arguments = 0\n[targets.web.cache]\nenabled = false\n[[targets.web.rule_exceptions]]\nrule = \"FWS010\"\npath = \"src/classes.ts\"\nsymbols = [\"{}\"]\nreason = \"External class callback.\"\n",
                test_case.symbol
            ),
        );
        write(
            repository.path().join("src/classes.ts"),
            "export class First { run(value: string): void { void value; } }\nexport class Second { run(value: string): void { void value; } }\n",
        );
        let process_directory = poison_processes(repository.path());

        let output =
            run_internal_web_check_with(repository.path(), &["--no-cache"], &process_directory);
        let stdout = String::from_utf8_lossy(&output.stdout);
        let stderr = String::from_utf8_lossy(&output.stderr);

        assert_eq!(
            output.status.code(),
            Some(test_case.expected_exit_code),
            "{}: {stdout} {stderr}",
            test_case.description
        );
        assert!(
            stdout.contains(test_case.expected_stdout),
            "{}: {stdout}",
            test_case.description
        );
        assert!(
            stderr.contains(test_case.expected_stderr),
            "{}: {stderr}",
            test_case.description
        );
    }
}

#[test]
fn given_valid_typescript_and_svelte_targets_when_checking_then_native_parsers_share_one_process_and_cache_without_collisions(
) {
    let test_cases = [WebCacheCheckTestCase {
        description: "native web targets retain distinct cache identities without host processes",
        expected_cold: "hits=0 misses=23",
        expected_warm: "hits=23 misses=0",
        expected_invalidated: "hits=0 misses=23",
    }];
    for test_case in &test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        write(repository.path().join("fensu.toml"), CONFIG);
        write(
            repository.path().join("tsconfig.json"),
            "{\n  // JSONC root\n  \"extends\": \"./config/middle\",\n  \"compilerOptions\": {\n    \"paths\": { \"@/*\": [\"src/*\"], },\n  },\n}\n",
        );
        write(
            repository.path().join("config/middle.json"),
            "{ \"extends\": \"./base\", }\n",
        );
        write(
            repository.path().join("config/base.json"),
            "{ \"compilerOptions\": { \"baseUrl\": \"..\", }, }\n",
        );
        write(
            repository.path().join("package.json"),
            "{\"type\":\"module\"}\n",
        );
        write(
            repository.path().join("svelte.config.js"),
            "export default {};\n",
        );
        write(repository.path().join("src/lib/value.ts"), VALID_TYPESCRIPT);
        write(
            repository.path().join("src/View.tsx"),
            "export const View = <div />;\n",
        );
        write(
            repository.path().join("src/helper.js"),
            "export const enabled = true;\n",
        );
        write(
            repository.path().join("src/Widget.jsx"),
            "export const Widget = <span />;\n",
        );
        write(
            repository.path().join("src/types.d.ts"),
            "export declare const label: string;\n",
        );
        write(
            repository.path().join("src/module.mts"),
            "export const esm: number = 1;\n",
        );
        write(
            repository.path().join("src/module.cts"),
            "export const cts: number = 1;\n",
        );
        write(
            repository.path().join("src/module.mjs"),
            "export const mjs = 1;\n",
        );
        write(
            repository.path().join("src/module.cjs"),
            "const cjs = 1; module.exports = { cjs };\n",
        );
        write(
            repository.path().join("src/types.d.mts"),
            "export declare const esmLabel: string;\n",
        );
        write(
            repository.path().join("src/types.d.cts"),
            "export declare const cjsLabel: string;\n",
        );
        write(repository.path().join("src/App.svelte"), VALID_COMPONENT);
        for artifact in ["node_modules", ".svelte-kit", "build", "dist", "coverage"] {
            write(
                repository
                    .path()
                    .join("src")
                    .join(artifact)
                    .join("malformed.ts"),
                "export const broken: = 1;\n",
            );
        }
        let process_directory = poison_processes(repository.path());

        let cold = run_internal_web_check_with(
            repository.path(),
            &["--cache", "--cache-stats"],
            &process_directory,
        );
        let warm = run_internal_web_check_with(
            repository.path(),
            &["--cache", "--cache-stats"],
            &process_directory,
        );
        write(
            repository.path().join("config/base.json"),
            "{ \"compilerOptions\": { \"baseUrl\": \"..\", \"strict\": true, }, }\n",
        );
        let changed_project_input = run_internal_web_check_with(
            repository.path(),
            &["--cache", "--cache-stats"],
            &process_directory,
        );

        assert_eq!(
            cold.status.code(),
            Some(0),
            "{}: {}",
            test_case.description,
            String::from_utf8_lossy(&cold.stderr),
        );
        assert_eq!(
            warm.status.code(),
            Some(0),
            "{}: {}",
            test_case.description,
            String::from_utf8_lossy(&warm.stderr),
        );
        assert_eq!(
            changed_project_input.status.code(),
            Some(0),
            "{}: {}",
            test_case.description,
            String::from_utf8_lossy(&changed_project_input.stderr),
        );
        assert_eq!(cold.stdout, warm.stdout, "{}", test_case.description);
        assert!(
            String::from_utf8_lossy(&cold.stdout)
                .contains("Evaluation: 16 of 17 source files (1 excluded by config)"),
            "{}: {}",
            test_case.description,
            String::from_utf8_lossy(&cold.stdout)
        );
        assert!(
            !String::from_utf8_lossy(&cold.stdout).contains("Python files"),
            "{}",
            test_case.description
        );
        assert!(
            String::from_utf8_lossy(&cold.stderr).contains(test_case.expected_cold),
            "{}",
            test_case.description
        );
        assert!(
            String::from_utf8_lossy(&warm.stderr).contains(test_case.expected_warm),
            "{}",
            test_case.description
        );
        assert!(
            String::from_utf8_lossy(&changed_project_input.stderr)
                .contains(test_case.expected_invalidated),
            "{}",
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
fn given_target_local_web_configuration_dependencies_when_changed_then_cache_identity_is_invalidated(
) {
    let test_cases = [WebCacheCheckTestCase {
        description: "target-local web configuration dependencies invalidate cached findings",
        expected_cold: "hits=0 misses=1",
        expected_warm: "hits=1 misses=0",
        expected_invalidated: "hits=0 misses=1",
    }];
    for test_case in &test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        write(
            repository.path().join("fensu.toml"),
            concat!(
                "[targets.web]\n",
                "analyzer = \"svelte\"\n",
                "root = \"frontend\"\n",
                "roots = [\"src\"]\n",
                "tests = []\n",
                "tooling = []\n",
                "ui_kit = \"src/ui-kit\"\n",
                "shadcn = \"config/components.json\"\n",
                "openapi = \"contracts/openapi.json\"\n",
                "select = []\n",
                "[targets.web.cache]\n",
                "enabled = true\n",
            ),
        );
        write(
            repository.path().join("frontend/src/App.svelte"),
            "<p>application</p>\n",
        );
        write(
            repository.path().join("frontend/config/components.json"),
            "{\"aliases\":{\"ui\":\"$ui-kit\",\"utils\":\"$ui-kit/utils\"}}\n",
        );
        write(
            repository.path().join("frontend/contracts/openapi.json"),
            "{\"paths\":{\"/api/orders\":{}}}\n",
        );
        write(
            repository.path().join("config/components.json"),
            "{\"aliases\":{\"ui\":\"wrong\"}}\n",
        );
        let process_directory = poison_processes(repository.path());

        let cold = run_internal_web_check_with(
            repository.path(),
            &["--cache", "--cache-stats"],
            &process_directory,
        );
        let warm = run_internal_web_check_with(
            repository.path(),
            &["--cache", "--cache-stats"],
            &process_directory,
        );
        write(
            repository.path().join("frontend/contracts/openapi.json"),
            "{\"paths\":{\"/api/orders\":{},\"/api/payments\":{}}}\n",
        );
        let changed = run_internal_web_check_with(
            repository.path(),
            &["--cache", "--cache-stats"],
            &process_directory,
        );

        assert_eq!(cold.status.code(), Some(0));
        assert_eq!(warm.status.code(), Some(0));
        assert_eq!(changed.status.code(), Some(0));
        assert!(
            String::from_utf8_lossy(&cold.stderr).contains(test_case.expected_cold),
            "{}",
            test_case.description
        );
        assert!(
            String::from_utf8_lossy(&warm.stderr).contains(test_case.expected_warm),
            "{}",
            test_case.description
        );
        assert!(
            String::from_utf8_lossy(&changed.stderr).contains(test_case.expected_invalidated),
            "{}",
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
fn given_malformed_web_sources_when_checking_then_diagnostics_name_repository_path_line_and_column()
{
    let test_cases = [WebParseDiagnosticTestCase {
        description: "malformed native web sources report repository positions without hosts",
        expected_svelte: "src/App.svelte:2:",
        expected_typescript: "src/lib/value.ts:1:",
    }];
    for test_case in &test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        write(
            repository.path().join("fensu.toml"),
            &CONFIG
                .replace("select = []", "select = [\"FWP001\"]")
                .replace(
                    "\n[targets.a_typescript.evaluation]\nexclude = [\"src/lib/value.ts\"]\n",
                    "\n",
                ),
        );
        write(repository.path().join("src/lib/value.ts"), VALID_TYPESCRIPT);
        write(
            repository.path().join("src/App.svelte"),
            "<script lang=\"ts\">\nconst value: = 1;\n</script>\n",
        );
        let process_directory = poison_processes(repository.path());

        let malformed_svelte =
            run_internal_web_check_with(repository.path(), &["--no-cache"], &process_directory);

        assert_eq!(
            malformed_svelte.status.code(),
            Some(1),
            "{}",
            test_case.description
        );
        assert!(
            String::from_utf8_lossy(&malformed_svelte.stdout).contains(test_case.expected_svelte),
            "{}",
            test_case.description
        );

        write(repository.path().join("src/App.svelte"), VALID_COMPONENT);
        write(
            repository.path().join("src/lib/value.ts"),
            "export const value: = 2;\n",
        );
        let malformed_typescript =
            run_internal_web_check_with(repository.path(), &["--no-cache"], &process_directory);

        assert_eq!(
            malformed_typescript.status.code(),
            Some(1),
            "{}",
            test_case.description
        );
        assert!(
            String::from_utf8_lossy(&malformed_typescript.stdout)
                .contains(test_case.expected_typescript),
            "{}",
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
fn given_web_source_purposes_when_checking_then_only_trusted_parse_surfaces_emit_diagnostics() {
    let test_cases = [
        WebSourcePurposeTestCase {
            description: "malformed declaration support reports a trusted parse failure",
            config: "[targets.web]\nanalyzer = \"typescript\"\nroots = [\"src\"]\ntests = []\ntooling = []\nselect = [\"FWP001\"]\n[targets.web.cache]\nenabled = false\n",
            files: &[("src/contracts.d.ts", "export interface Contract { value: ; }\n")],
            expected_exit_code: 1,
            expected_present: Some("FWP001"),
            expected_absent: None,
        },
        WebSourcePurposeTestCase {
            description: "evaluation-excluded malformed source remains graph context without diagnostics",
            config: "[targets.web]\nanalyzer = \"typescript\"\nroots = [\"src\"]\ntests = []\ntooling = []\nselect = [\"FWP001\"]\n[targets.web.evaluation]\nexclude = [\"src/excluded.ts\"]\n[targets.web.cache]\nenabled = false\n",
            files: &[("src/excluded.ts", "export const value: = 1;\n")],
            expected_exit_code: 0,
            expected_present: None,
            expected_absent: Some("FWP001"),
        },
        WebSourcePurposeTestCase {
            description: "generated malformed source remains graph context without diagnostics",
            config: "[targets.web]\nanalyzer = \"typescript\"\nroots = [\"src\"]\ntests = []\ntooling = []\ngenerated = [\"src/generated/**\"]\nselect = [\"FWP001\"]\n[targets.web.cache]\nenabled = false\n",
            files: &[("src/generated/value.ts", "export const value: = 1;\n")],
            expected_exit_code: 0,
            expected_present: None,
            expected_absent: Some("FWP001"),
        },
        WebSourcePurposeTestCase {
            description: "generated import targets do not trigger target-sensitive layer rules",
            config: "[targets.web]\nanalyzer = \"typescript\"\nroots = [\"src\"]\ntests = []\ntooling = []\ngenerated = [\"src/generated/**\"]\nselect = [\"FWL101\", \"FWL102\", \"FWL103\", \"FWL105\", \"FWL108\"]\n[targets.web.cache]\nenabled = false\n",
            files: &[
                ("src/generated/index.ts", "export const value: number = 1;\n"),
                ("src/use.ts", "import * as generated from './generated'; export const value = generated.value;\n"),
            ],
            expected_exit_code: 0,
            expected_present: None,
            expected_absent: Some("FWL"),
        },
        WebSourcePurposeTestCase {
            description: "TypeScript analyzer does not classify Svelte components as TypeScript sources",
            config: "[targets.web]\nanalyzer = \"typescript\"\nroots = [\"src\"]\ntests = []\ntooling = []\nselect = [\"FWP001\"]\n[targets.web.cache]\nenabled = false\n",
            files: &[
                ("src/value.ts", VALID_TYPESCRIPT),
                ("src/App.svelte", "<script>const value: = 1;</script>\n"),
            ],
            expected_exit_code: 0,
            expected_present: None,
            expected_absent: Some("FWP001"),
        },
        WebSourcePurposeTestCase {
            description: "Svelte analyzer parses malformed TypeScript support as TypeScript",
            config: "[targets.web]\nanalyzer = \"svelte\"\nroots = [\"src\"]\ntests = []\ntooling = []\nselect = [\"FWP001\"]\n[targets.web.cache]\nenabled = false\n",
            files: &[
                ("src/App.svelte", "<p>value</p>\n"),
                ("src/support.ts", "export const value: = 1;\n"),
            ],
            expected_exit_code: 1,
            expected_present: Some("src/support.ts:1:"),
            expected_absent: None,
        },
        WebSourcePurposeTestCase {
            description: "evaluation-excluded Svelte runtime support remains graph-only",
            config: "[targets.web]\nanalyzer = \"svelte\"\nroots = [\"src\"]\ntests = []\ntooling = []\nselect = [\"FWR309\"]\n[targets.web.evaluation]\nexclude = [\"src/lib/payments/**\"]\n[targets.web.cache]\nenabled = false\n",
            files: &[
                ("src/lib/views/main/View.svelte", "<p>view</p>\n"),
                (
                    "src/lib/payments/_helpers/load.ts",
                    "export function load(): string { return 'payment'; }\n",
                ),
            ],
            expected_exit_code: 0,
            expected_present: None,
            expected_absent: Some("FWR309"),
        },
    ];
    for test_case in &test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        write(repository.path().join("fensu.toml"), test_case.config);
        for (path, source) in test_case.files {
            write(repository.path().join(path), source);
        }
        let process_directory = poison_processes(repository.path());

        let output =
            run_internal_web_check_with(repository.path(), &["--no-cache"], &process_directory);
        let stdout = String::from_utf8_lossy(&output.stdout);

        assert_eq!(
            output.status.code(),
            Some(test_case.expected_exit_code),
            "{}: {stdout} {}",
            test_case.description,
            String::from_utf8_lossy(&output.stderr)
        );
        assert_eq!(
            test_case
                .expected_present
                .is_some_and(|expected| stdout.contains(expected)),
            test_case.expected_present.is_some(),
            "{}: {stdout}",
            test_case.description
        );
        assert!(
            test_case
                .expected_absent
                .is_none_or(|expected| !stdout.contains(expected)),
            "{}: {stdout}",
            test_case.description
        );
    }
}

#[test]
fn given_web_target_when_mapping_then_clear_capability_error_is_returned() {
    let test_cases = [InternalGateCommandTestCase {
        description: "map capability remains unavailable",
        arguments: &["map", "symbol", "--target", "a_typescript", "--no-cache"],
        expected_error:
            "Map capability unavailable for analyzer typescript: native mapping is not implemented.",
    }];
    for test_case in &test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        write(repository.path().join("fensu.toml"), CONFIG);
        write(repository.path().join("src/value.ts"), VALID_TYPESCRIPT);

        let output = run_web_command(repository.path(), test_case.arguments);

        assert_eq!(output.status.code(), Some(2), "{}", test_case.description);
        assert!(
            String::from_utf8_lossy(&output.stderr).contains(test_case.expected_error),
            "{}: {}",
            test_case.description,
            String::from_utf8_lossy(&output.stderr)
        );
    }
}

#[test]
fn given_invalid_extended_typescript_configs_when_checking_then_precise_errors_fail_closed() {
    let test_cases = [
        WebConfigFailureTestCase {
            description: "missing extended config names its owner and specifier",
            files: &[("tsconfig.json", "{ \"extends\": \"./missing\" }\n")],
            expected_error: "Could not resolve TypeScript config extends \"./missing\" from tsconfig.json.",
        },
        WebConfigFailureTestCase {
            description: "recursive config cycle names the complete cycle",
            files: &[
                ("tsconfig.json", "{ \"extends\": \"./config/base\" }\n"),
                ("config/base.json", "{ \"extends\": \"../tsconfig\" }\n"),
            ],
            expected_error: "TypeScript config extends cycle: tsconfig.json -> config/base.json -> tsconfig.json.",
        },
        WebConfigFailureTestCase {
            description: "malformed JSONC reports its config and source line",
            files: &[(
                "tsconfig.json",
                "{\n  \"compilerOptions\": { /* unterminated\n}\n",
            )],
            expected_error: "Could not parse TypeScript config tsconfig.json: unterminated block comment at line 2.",
        },
    ];
    for test_case in &test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        write(repository.path().join("fensu.toml"), CONFIG);
        write(repository.path().join("src/value.ts"), VALID_TYPESCRIPT);
        for (path, content) in test_case.files {
            write(repository.path().join(path), content);
        }
        let process_directory = poison_processes(repository.path());

        let output =
            run_internal_web_check_with(repository.path(), &["--no-cache"], &process_directory);

        assert_eq!(output.status.code(), Some(2), "{}", test_case.description);
        assert!(
            String::from_utf8_lossy(&output.stderr).contains(test_case.expected_error),
            "{}: {}",
            test_case.description,
            String::from_utf8_lossy(&output.stderr)
        );
    }
}

#[test]
fn given_hosted_policy_on_web_target_when_checking_then_rejects_after_native_parsing_before_python()
{
    let test_cases = [
        HostedWebPolicyTestCase {
            description: "custom rule paths cannot route a TypeScript target to Python",
            config: "[targets.web]\nanalyzer = \"typescript\"\nroots = [\"src\"]\ntests = []\ntooling = []\nselect = []\nrule_paths = [\"rules/custom.py\"]\n",
            expected_error: "Native typescript check integration does not support Python-hosted rule paths, modules, or options.",
        },
        HostedWebPolicyTestCase {
            description: "custom rule modules cannot route a Svelte target to Python",
            config: "[targets.web]\nanalyzer = \"svelte\"\nroots = [\"src\"]\ntests = []\ntooling = []\nselect = []\nrule_modules = [\"policy.web\"]\n",
            expected_error: "Native svelte check integration does not support Python-hosted rule paths, modules, or options.",
        },
        HostedWebPolicyTestCase {
            description: "custom rule options cannot route a TypeScript target to Python",
            config: "[targets.web]\nanalyzer = \"typescript\"\nroots = [\"src\"]\ntests = []\ntooling = []\nselect = []\n[targets.web.rule_options.XOP001]\nenabled = true\n",
            expected_error: "Native typescript check integration does not support Python-hosted rule paths, modules, or options.",
        },
    ];
    for test_case in &test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        write(repository.path().join("fensu.toml"), test_case.config);
        write(
            repository.path().join("src/valid.ts"),
            "export const valid: number = 1;\n",
        );
        let process_directory = poison_processes(repository.path());

        let output =
            run_internal_web_check_with(repository.path(), &["--no-cache"], &process_directory);

        assert_eq!(output.status.code(), Some(2), "{}", test_case.description);
        assert!(
            String::from_utf8_lossy(&output.stderr).contains(test_case.expected_error),
            "{}: {}",
            test_case.description,
            String::from_utf8_lossy(&output.stderr)
        );
        assert!(
            !repository.path().join("process-invoked").exists(),
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_hosted_policy_and_malformed_web_source_when_checking_then_configuration_still_fails_closed(
) {
    let test_cases = [HostedWebPolicyTestCase {
        description: "hosted policy cannot bypass native TypeScript parsing",
        config: "[targets.web]\nanalyzer = \"typescript\"\nroots = [\"src\"]\ntests = []\ntooling = []\nselect = []\nrule_paths = [\"rules/custom.py\"]\n",
        expected_error: "Native typescript check integration does not support Python-hosted rule paths, modules, or options.",
    }];
    for test_case in &test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        write(repository.path().join("fensu.toml"), test_case.config);
        write(
            repository.path().join("src/malformed.ts"),
            "export const malformed: = 1;\n",
        );
        let process_directory = poison_processes(repository.path());

        let output =
            run_internal_web_check_with(repository.path(), &["--no-cache"], &process_directory);

        assert_eq!(output.status.code(), Some(2), "{}", test_case.description);
        assert!(
            String::from_utf8_lossy(&output.stderr).contains(test_case.expected_error),
            "{}: {}",
            test_case.description,
            String::from_utf8_lossy(&output.stderr)
        );
        assert!(
            !repository.path().join("process-invoked").exists(),
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_retained_web_rules_when_checking_then_native_evaluator_reports_owned_fact_locations() {
    let test_cases = [WebPolicyCheckTestCase {
        description: "retained fact rules report exact native locations",
        expected_exit_code: 1,
    }];
    for test_case in test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        write(
        repository.path().join("fensu.toml"),
        "[targets.web]\nanalyzer = \"typescript\"\nroots = [\"src\"]\ntests = []\ntooling = []\nselect = [\"FWA003\", \"FWS201\", \"FWR501\"]\n[targets.web.cache]\nenabled = false\n",
    );
        write(
            repository.path().join("src/lib/orders/models.ts"),
            "export interface Order { value: string; }\n",
        );
        write(
        repository
            .path()
            .join("src/lib/orders/classes/wrong-name.ts"),
        "declare function buildOrder(): string;\nexport class OrderProcessor {\n  run(): void {\n    const order = buildOrder();\n    void order;\n  }\n}\n",
    );
        let process_directory = poison_processes(repository.path());

        let output =
            run_internal_web_check_with(repository.path(), &["--no-cache"], &process_directory);
        let stdout = String::from_utf8_lossy(&output.stdout);

        assert_eq!(
            output.status.code(),
            Some(test_case.expected_exit_code),
            "{}",
            test_case.description
        );
        assert!(stdout.contains("models.ts:1:"));
        assert!(
            stdout.contains("model 'Order' exposes mutable properties"),
            "{stdout}"
        );
        assert!(stdout.contains("wrong-name.ts:2:"));
        assert!(stdout.contains("exported class 'OrderProcessor'"));
        assert!(stdout.contains("wrong-name.ts:4:"));
        assert!(stdout.contains("local variable 'order'"));
        assert!(!repository.path().join("process-invoked").exists());
    }
}

#[test]
fn given_explicit_local_contracts_when_checking_then_model_class_and_fwa003_near_misses_pass() {
    let test_cases = [WebPolicyCheckTestCase {
        description: "explicit local contracts are passing near misses",
        expected_exit_code: 0,
    }];
    for test_case in test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        write(
        repository.path().join("fensu.toml"),
        "[targets.web]\nanalyzer = \"typescript\"\nroots = [\"src\"]\ntests = []\ntooling = []\nselect = [\"FWA003\", \"FWS201\", \"FWR501\"]\n[targets.web.cache]\nenabled = false\n",
    );
        write(
            repository.path().join("src/lib/orders/models.ts"),
            "export interface Order { readonly values: readonly string[]; }\n",
        );
        write(
        repository
            .path()
            .join("src/lib/orders/classes/order-processor.ts"),
        "interface Order { readonly value: string; }\ndeclare function buildOrder<T>(): T;\nexport class OrderProcessor {\n  run(): void {\n    const scalar = 1;\n    const explicit: Order = buildOrder<Order>();\n    const checked = { value: 'x' } satisfies Order;\n    void scalar; void explicit; void checked;\n  }\n}\n",
    );
        let process_directory = poison_processes(repository.path());

        let output =
            run_internal_web_check_with(repository.path(), &["--no-cache"], &process_directory);

        assert_eq!(
            output.status.code(),
            Some(test_case.expected_exit_code),
            "{}: {}",
            test_case.description,
            String::from_utf8_lossy(&output.stdout),
        );
    }
}

#[test]
fn given_main_only_leaf_with_empty_placeholder_when_checking_then_fwr311_still_reports() {
    let test_cases = [WebPolicyCheckTestCase {
        description: "an empty role cannot disguise a main-only leaf",
        expected_exit_code: 1,
    }];
    for test_case in test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        write(
        repository.path().join("fensu.toml"),
        "[targets.web]\nanalyzer = \"typescript\"\nroots = [\"src\"]\ntests = []\ntooling = []\nselect = [\"FWR311\"]\n[targets.web.cache]\nenabled = false\n",
    );
        write(
            repository.path().join("src/lib/orders/main/read-order.ts"),
            "export function readOrder(): string { return 'order'; }\n",
        );
        write(repository.path().join("src/lib/orders/types.ts"), "");
        write(
            repository
                .path()
                .join("src/lib/payments/main/read-payment.ts"),
            "export function readPayment(): string { return 'payment'; }\n",
        );
        write(
            repository
                .path()
                .join("src/lib/payments/_helpers/load-payment.ts"),
            "export function loadPayment(): string { return 'payment'; }\n",
        );
        let process_directory = poison_processes(repository.path());

        let output =
            run_internal_web_check_with(repository.path(), &["--no-cache"], &process_directory);
        let stdout = String::from_utf8_lossy(&output.stdout);

        assert_eq!(
            output.status.code(),
            Some(test_case.expected_exit_code),
            "{}",
            test_case.description
        );
        assert_eq!(stdout.matches("FWR311").count(), 1);
        assert!(stdout.contains("leaf 'orders' contains only main entries"));
        assert!(!stdout.contains("leaf 'payments'"));
        assert!(stdout.contains(" --> src/lib/orders:-:-"));
    }
}

#[test]
fn given_same_capability_in_multiple_roots_when_checking_then_project_ownership_stays_root_scoped()
{
    let test_cases = [WebPolicyCheckTestCase {
        description: "same-named capabilities remain isolated by source root",
        expected_exit_code: 1,
    }];
    for test_case in test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        write(
        repository.path().join("fensu.toml"),
        "[targets.web]\nanalyzer = \"typescript\"\nroots = [\"apps/one/src\", \"apps/two/src\"]\ntests = []\ntooling = []\nselect = [\"FWR311\"]\n[targets.web.cache]\nenabled = false\n",
    );
        write(
            repository
                .path()
                .join("apps/one/src/lib/orders/main/read.ts"),
            "export function read(): string { return 'one'; }\n",
        );
        write(
            repository
                .path()
                .join("apps/one/src/lib/orders/_helpers/load.ts"),
            "export function load(): string { return 'one'; }\n",
        );
        write(
            repository
                .path()
                .join("apps/two/src/lib/orders/main/read.ts"),
            "export function read(): string { return 'two'; }\n",
        );
        let process_directory = poison_processes(repository.path());

        let output =
            run_internal_web_check_with(repository.path(), &["--no-cache"], &process_directory);
        let stdout = String::from_utf8_lossy(&output.stdout);

        assert_eq!(
            output.status.code(),
            Some(test_case.expected_exit_code),
            "{}",
            test_case.description
        );
        assert_eq!(
            stdout.matches("FWR311").count(),
            1,
            "{}",
            test_case.description
        );
        assert!(
            stdout.contains(" --> apps/two/src/lib/orders:-:-"),
            "{}",
            test_case.description
        );
        assert!(
            !stdout.contains(" --> apps/one/src/lib/orders:-:-"),
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_configured_naming_contract_when_checking_then_web_naming_uses_the_contract() {
    let test_cases = [WebPolicyCheckTestCase {
        description: "custom contract patterns govern TypeScript function names",
        expected_exit_code: 1,
    }];
    for test_case in test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        write(
        repository.path().join("fensu.toml"),
        "[targets.web]\nanalyzer = \"typescript\"\nroots = [\"src\"]\ntests = []\ntooling = []\nselect = [\"FWN001\"]\n[targets.web.contracts]\n\"fetch_*\" = \"returns-bool\"\n[targets.web.cache]\nenabled = false\n",
    );
        write(
            repository.path().join("src/fetch-order.ts"),
            "export function fetchOrder(): string { return 'order'; }\n",
        );
        let process_directory = poison_processes(repository.path());

        let output =
            run_internal_web_check_with(repository.path(), &["--no-cache"], &process_directory);

        assert_eq!(
            output.status.code(),
            Some(test_case.expected_exit_code),
            "{}",
            test_case.description
        );
        assert!(
            String::from_utf8_lossy(&output.stdout).contains("FWN001"),
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_overridden_default_contract_when_checking_then_configured_behavior_replaces_default() {
    let test_cases = [WebPolicyCheckTestCase {
        description: "configured should contract replaces its default predicate behavior",
        expected_exit_code: 1,
    }];
    for test_case in test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        write(
            repository.path().join("fensu.toml"),
            "[targets.web]\nanalyzer = \"typescript\"\nroots = [\"src\"]\ntests = []\ntooling = []\nselect = [\"FWN001\", \"FWN003\"]\n[targets.web.contracts]\n\"should_*\" = \"returns-value\"\n[targets.web.cache]\nenabled = false\n",
        );
        write(
            repository.path().join("src/should-run.ts"),
            "export function shouldRun(): void {}\n",
        );
        let process_directory = poison_processes(repository.path());

        let output =
            run_internal_web_check_with(repository.path(), &["--no-cache"], &process_directory);
        let stdout = String::from_utf8_lossy(&output.stdout);

        assert_eq!(
            output.status.code(),
            Some(test_case.expected_exit_code),
            "{}: {stdout}",
            test_case.description
        );
        assert!(
            stdout.contains("FWN003"),
            "{}: {stdout}",
            test_case.description
        );
        assert!(
            !stdout.contains("FWN001"),
            "{}: {stdout}",
            test_case.description
        );
    }
}

#[test]
fn given_configured_ui_kit_when_checking_then_deliberate_surface_exemptions_apply() {
    let test_cases = [WebPolicyCheckTestCase {
        description: "configured UI-kit surfaces permit deliberate exports and imports",
        expected_exit_code: 0,
    }];
    for test_case in test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        write(
        repository.path().join("fensu.toml"),
        "[targets.web]\nanalyzer = \"typescript\"\nroots = [\"src\"]\ntests = []\ntooling = []\nui_kit = \"src/ui-kit\"\nselect = [\"FWA003\", \"FWL102\", \"FWL103\", \"FWR001\", \"FWR002\", \"FWR003\", \"FWR201\", \"FWR304\", \"FWR310\", \"FWR401\", \"FWR403\", \"FWR404\", \"FWR405\", \"FWR501\", \"FWS106\"]\n[targets.web.thresholds]\nmax_public_exports = 1\n[targets.web.cache]\nenabled = false\n",
    );
        write(
            repository.path().join("src/ui-kit/family/button.ts"),
            "export const button: string = 'button';\n",
        );
        write(
            repository.path().join("src/ui-kit/family/wrong.ts"),
            "declare function build(): object; export class Button { run(): void { const value = build(); void value; } }\n",
        );
        write(
            repository.path().join("src/ui-kit/family/types.ts"),
            "export const runtime: number = 1;\n",
        );
        write(
            repository.path().join("src/ui-kit/family/constants.ts"),
            "export function value(): number { return 1; }\n",
        );
        write(
            repository.path().join("src/ui-kit/family/errors.ts"),
            "export class Value {}\n",
        );
        write(
            repository.path().join("src/ui-kit/family/helpers.ts"),
            "export const helper: number = 1;\n",
        );
        write(
            repository.path().join("src/ui-kit/family/index.ts"),
            "export { button } from './button'; export { Button } from './wrong'; export { runtime } from './types'; export { helper } from './helpers';\n",
        );
        write(
            repository.path().join("src/use.ts"),
            "import * as ui from './ui-kit/family'; export const button = ui.button;\n",
        );
        let process_directory = poison_processes(repository.path());

        let output =
            run_internal_web_check_with(repository.path(), &["--no-cache"], &process_directory);

        assert_eq!(
            output.status.code(),
            Some(test_case.expected_exit_code),
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_svelte_target_when_checking_generic_policy_then_component_and_support_facts_share_rules() {
    let test_cases = [WebPolicyCheckTestCase {
        description: "Svelte and support modules share generic policy",
        expected_exit_code: 1,
    }];
    for test_case in test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        write(
        repository.path().join("fensu.toml"),
        "[targets.web]\nanalyzer = \"svelte\"\nroots = [\"src\"]\ntests = []\ntooling = []\nselect = [\"FWA003\"]\n[targets.web.cache]\nenabled = false\n",
    );
        write(
        repository.path().join("src/App.svelte"),
        "<script lang=\"ts\">\ndeclare function buildValue(): string;\nfunction run(): void { const componentValue = buildValue(); void componentValue; }\n</script>\n<p>value</p>\n",
    );
        write(
        repository.path().join("src/support.ts"),
        "declare function buildValue(): string;\nexport function run(): void { const supportValue = buildValue(); void supportValue; }\n",
    );
        let process_directory = poison_processes(repository.path());

        let output =
            run_internal_web_check_with(repository.path(), &["--no-cache"], &process_directory);
        let stdout = String::from_utf8_lossy(&output.stdout);

        assert_eq!(
            output.status.code(),
            Some(test_case.expected_exit_code),
            "{}",
            test_case.description
        );
        assert!(stdout.contains("App.svelte:3:"));
        assert!(stdout.contains("local variable 'componentValue'"));
        assert!(stdout.contains("support.ts:2:"));
        assert!(stdout.contains("local variable 'supportValue'"));
    }
}

#[test]
fn given_svelte_target_when_checking_project_policy_then_runtime_support_modules_join_capabilities()
{
    let test_cases = [WebPolicyCheckTestCase {
        description: "Svelte project policy includes runtime TS and JS support without changing target identity",
        expected_exit_code: 1,
    }];
    for test_case in test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        write(
            repository.path().join("fensu.toml"),
            "[targets.web]\nanalyzer = \"svelte\"\nroots = [\"src\"]\ntests = []\ntooling = []\nselect = [\"FWR309\"]\n[targets.web.cache]\nenabled = false\n",
        );
        write(
            repository.path().join("src/lib/orders/_helpers/load.ts"),
            "export function load(): string { return 'order'; }\n",
        );
        write(
            repository.path().join("src/lib/orders/main/read.mjs"),
            "export function read() { return 'order'; }\n",
        );
        write(
            repository.path().join("src/lib/payments/_helpers/load.cjs"),
            "function load() { return 'payment'; } module.exports = { load };\n",
        );
        write(
            repository.path().join("src/lib/views/main/View.svelte"),
            "<p>view</p>\n",
        );
        let process_directory = poison_processes(repository.path());

        let output =
            run_internal_web_check_with(repository.path(), &["--no-cache"], &process_directory);
        let stdout = String::from_utf8_lossy(&output.stdout);

        assert_eq!(output.status.code(), Some(test_case.expected_exit_code));
        assert_eq!(
            stdout.matches("FWR309").count(),
            1,
            "{}: {stdout}",
            test_case.description
        );
        assert!(
            stdout.contains("src/lib/payments"),
            "{}: {stdout}",
            test_case.description
        );
        assert!(
            !stdout.contains("src/lib/orders:-:-"),
            "{}: {stdout}",
            test_case.description
        );
    }
}

#[test]
fn given_tooling_tests_when_checking_mirror_then_one_configured_tooling_prefix_is_removed() {
    let test_cases = [
        WebSourcePurposeTestCase {
            description: "one tooling prefix mirrors the configured tooling area",
            config: "[targets.web]\nanalyzer = \"typescript\"\nroots = [\"src\"]\ntests = [\"tests\"]\ntooling = [\"scripts\"]\nselect = [\"FWT002\"]\n[targets.web.cache]\nenabled = false\n",
            files: &[
                ("src/value.ts", VALID_TYPESCRIPT),
                ("scripts/catalogue/run.ts", VALID_TYPESCRIPT),
                (
                    "tests/scripts/catalogue/run.test.ts",
                    "test('given input when run then succeeds', () => {});\n",
                ),
            ],
            expected_exit_code: 0,
            expected_present: None,
            expected_absent: Some("FWT002"),
        },
        WebSourcePurposeTestCase {
            description: "a doubled tooling prefix is not removed twice",
            config: "[targets.web]\nanalyzer = \"typescript\"\nroots = [\"src\"]\ntests = [\"tests\"]\ntooling = [\"scripts\"]\nselect = [\"FWT002\"]\n[targets.web.cache]\nenabled = false\n",
            files: &[
                ("src/value.ts", VALID_TYPESCRIPT),
                ("scripts/catalogue/run.ts", VALID_TYPESCRIPT),
                (
                    "tests/scripts/scripts/catalogue/run.test.ts",
                    "test('given input when run then succeeds', () => {});\n",
                ),
            ],
            expected_exit_code: 1,
            expected_present: Some("FWT002"),
            expected_absent: None,
        },
        WebSourcePurposeTestCase {
            description: "the tooling root itself mirrors files directly beneath that root",
            config: "[targets.web]\nanalyzer = \"typescript\"\nroots = [\"src\"]\ntests = [\"tests\"]\ntooling = [\"scripts\"]\nselect = [\"FWT002\"]\n[targets.web.cache]\nenabled = false\n",
            files: &[
                ("src/value.ts", VALID_TYPESCRIPT),
                ("scripts/run.ts", VALID_TYPESCRIPT),
                (
                    "tests/scripts/run.test.ts",
                    "test('given input when run then succeeds', () => {});\n",
                ),
            ],
            expected_exit_code: 0,
            expected_present: None,
            expected_absent: Some("FWT002"),
        },
    ];
    for test_case in &test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        write(repository.path().join("fensu.toml"), test_case.config);
        for (path, source) in test_case.files {
            write(repository.path().join(path), source);
        }
        let process_directory = poison_processes(repository.path());

        let output =
            run_internal_web_check_with(repository.path(), &["--no-cache"], &process_directory);
        let stdout = String::from_utf8_lossy(&output.stdout);

        assert_eq!(output.status.code(), Some(test_case.expected_exit_code));
        assert_eq!(
            test_case
                .expected_present
                .is_some_and(|code| stdout.contains(code)),
            test_case.expected_present.is_some(),
            "{}: {stdout}",
            test_case.description
        );
        assert!(
            test_case
                .expected_absent
                .is_none_or(|code| !stdout.contains(code)),
            "{}: {stdout}",
            test_case.description
        );
    }
}

#[test]
fn given_colocated_test_owner_when_checking_boundaries_and_coverage_then_uses_adjacent_capability()
{
    let test_cases = [
        WebSourcePurposeTestCase {
            description: "colocated test importing its adjacent internal API stays capability-local",
            config: "[targets.web]\nanalyzer = \"typescript\"\nroots = [\"src\"]\ntests = []\ntooling = []\ntest_layout = \"colocated\"\nselect = [\"FWL101\"]\n[targets.web.cache]\nenabled = false\n",
            files: &[
                (
                    "src/lib/orders/_api/client.ts",
                    "export function client(): string { return 'ok'; }\n",
                ),
                (
                    "src/lib/orders/_api/client.test.ts",
                    "import { client } from './client'; test('client', () => client());\n",
                ),
            ],
            expected_exit_code: 0,
            expected_present: None,
            expected_absent: Some("FWL101"),
        },
        WebSourcePurposeTestCase {
            description: "colocated focused state test satisfies critical-role coverage",
            config: "[targets.web]\nanalyzer = \"typescript\"\nroots = [\"src\"]\ntests = []\ntooling = []\ntest_layout = \"colocated\"\nselect = [\"FWT003\"]\n[targets.web.cache]\nenabled = false\n",
            files: &[
                (
                    "src/lib/orders/_state/orders.state.ts",
                    "export const orders: string[] = [];\n",
                ),
                (
                    "src/lib/orders/_state/orders.state.test.ts",
                    "test('orders state', () => {});\n",
                ),
            ],
            expected_exit_code: 0,
            expected_present: None,
            expected_absent: Some("FWT003"),
        },
        WebSourcePurposeTestCase {
            description: "colocated integration adapter test satisfies both coverage rules",
            config: "[targets.web]\nanalyzer = \"typescript\"\nroots = [\"src\"]\ntests = []\ntooling = []\ntest_layout = \"colocated\"\nselect = [\"FWT003\", \"FWT004\"]\n[targets.web.cache]\nenabled = false\n",
            files: &[
                (
                    "src/lib/orders/_adapters/payment.ts",
                    "export function payment(): string { return 'ok'; }\n",
                ),
                (
                    "src/lib/orders/_adapters/payment.integration.test.ts",
                    "test('payment integration', () => {});\n",
                ),
            ],
            expected_exit_code: 0,
            expected_present: None,
            expected_absent: Some("FWT00"),
        },
    ];
    for test_case in &test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        write(repository.path().join("fensu.toml"), test_case.config);
        for (path, source) in test_case.files {
            write(repository.path().join(path), source);
        }
        let process_directory = poison_processes(repository.path());

        let output =
            run_internal_web_check_with(repository.path(), &["--no-cache"], &process_directory);
        let stdout = String::from_utf8_lossy(&output.stdout);

        assert_eq!(
            output.status.code(),
            Some(test_case.expected_exit_code),
            "{}: {stdout} {}",
            test_case.description,
            String::from_utf8_lossy(&output.stderr)
        );
        assert!(
            test_case
                .expected_present
                .is_none_or(|code| stdout.contains(code)),
            "{}: {stdout}",
            test_case.description
        );
        assert!(
            test_case
                .expected_absent
                .is_none_or(|code| !stdout.contains(code)),
            "{}: {stdout}",
            test_case.description
        );
    }
}

#[test]
fn given_multiple_json_results_when_checking_contracts_then_each_flow_is_evaluated_independently() {
    let test_cases = [WebPolicyCheckTestCase {
        description:
            "schema decoding, Date parsing, and assertions remain attached to their JSON origin",
        expected_exit_code: 1,
    }];
    for test_case in test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        write(
            repository.path().join("fensu.toml"),
            "[targets.web]\nanalyzer = \"typescript\"\nroots = [\"src\"]\ntests = []\ntooling = []\nselect = [\"FWC101\", \"FWC102\"]\n[targets.web.cache]\nenabled = false\n",
        );
        write(
            repository.path().join("src/run.ts"),
            concat!(
                "export async function run(firstResponse: Response, secondResponse: Response, thirdResponse: Response): Promise<unknown> {\n",
                "  const first = await firstResponse.json \n ( ); const firstAlias = first; FirstSchema.parse(firstAlias);\n",
                "  const second = await secondResponse.json\n( ); Date.parse(second);\n",
                "  const third = await thirdResponse.json ( ); const thirdAlias = third; return thirdAlias as Data;\n",
                "}\n",
            ),
        );
        let process_directory = poison_processes(repository.path());

        let output =
            run_internal_web_check_with(repository.path(), &["--no-cache"], &process_directory);
        let stdout = String::from_utf8_lossy(&output.stdout);

        assert_eq!(output.status.code(), Some(test_case.expected_exit_code));
        assert_eq!(
            stdout.matches("FWC101  ").count(),
            2,
            "{}: {stdout}",
            test_case.description
        );
        assert_eq!(
            stdout.matches("FWC102  ").count(),
            1,
            "{}: {stdout}",
            test_case.description
        );
        assert!(
            !stdout.contains("src/run.ts:2:"),
            "{}: {stdout}",
            test_case.description
        );
        assert!(
            stdout.contains("src/run.ts:4:"),
            "{}: {stdout}",
            test_case.description
        );
        assert!(
            stdout.contains("src/run.ts:6:"),
            "{}: {stdout}",
            test_case.description
        );
    }
}

#[test]
fn given_svelte_component_rune_when_checking_import_side_effects_then_component_execution_is_exempt(
) {
    let test_cases = [WebPolicyCheckTestCase {
        description: "component rune execution is not an import-time side effect",
        expected_exit_code: 0,
    }];
    for test_case in test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        write(
        repository.path().join("fensu.toml"),
        "[targets.web]\nanalyzer = \"svelte\"\nroots = [\"src\"]\ntests = []\ntooling = []\nselect = [\"FWH009\"]\n[targets.web.cache]\nenabled = false\n",
    );
        write(
            repository.path().join("src/App.svelte"),
            "<script lang=\"ts\">$effect(() => {});</script><p>value</p>\n",
        );
        let process_directory = poison_processes(repository.path());

        let output =
            run_internal_web_check_with(repository.path(), &["--no-cache"], &process_directory);

        assert_eq!(
            output.status.code(),
            Some(test_case.expected_exit_code),
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_combined_sveltekit_project_when_checking_retained_pack_then_all_boundaries_pass_natively()
{
    let test_cases = [WebPolicyCheckTestCase {
        description: "combined SvelteKit project passes every retained web boundary natively",
        expected_exit_code: 0,
    }];
    for test_case in &test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        write(
        repository.path().join("fensu.toml"),
        concat!(
            "[targets.web]\n",
            "analyzer = \"svelte\"\n",
            "framework = \"sveltekit\"\n",
            "roots = [\"src\"]\n",
            "tests = []\n",
            "tooling = []\n",
            "ui_kit = \"src/ui-kit\"\n",
            "shadcn = \"config/components.json\"\n",
            "openapi = \"contracts/openapi.json\"\n",
            "select = [\"FWS101\", \"FWS102\", \"FWS103\", \"FWS104\", \"FWS107\", \"FWS108\", \"FWS109\", \"FWS110\", \"FWS111\", \"FWA101\", \"FWA102\", \"FWA103\", \"FWL104\", \"FWL106\", \"FWL107\", \"FWV101\", \"FWV102\", \"FWV103\", \"FWV104\", \"FWV105\", \"FWV106\", \"FWV107\", \"FWV201\", \"FWV202\", \"FWU001\", \"FWU002\", \"FWU003\", \"FWC201\"]\n",
            "[targets.web.cache]\n",
            "enabled = false\n",
        ),
    );
        write(
            repository.path().join("config/components.json"),
            "{\"aliases\":{\"ui\":\"$ui-kit\",\"utils\":\"$ui-kit/utils\"}}\n",
        );
        write(
            repository.path().join("contracts/openapi.json"),
            "{\"paths\":{\"/api/orders\":{}}}\n",
        );
        write(
            repository
                .path()
                .join("src/lib/orders/_state/order.state.svelte.ts"),
            concat!(
                "export function createOrderState(): object {\n",
                "  let selected = $state<string | null>(null);\n",
                "  const label = $derived.by(() => selected ?? 'none');\n",
                "  function select(value: string): void { selected = value; }\n",
                "  $effect(() => { document.title = label; });\n",
                "  return { get selected() { return selected; }, label, select };\n",
                "}\n",
            ),
        );
        write(
            repository
                .path()
                .join("src/lib/orders/_resources/socket.resource.ts"),
            concat!(
                "export function createSocket(): object {\n",
                "  const socket = new WebSocket('ws://localhost');\n",
                "  function stop(): void { socket.close(); }\n",
                "  return { socket, stop };\n",
                "}\n",
            ),
        );
        write(
            repository.path().join("src/lib/orders/_api/read-orders.ts"),
            "export function readOrders(): Promise<Response> { return fetch('/api/orders'); }\n",
        );
        write(
            repository.path().join("src/lib/orders/types.ts"),
            "export interface Order { readonly id: string; }\n",
        );
        write(
        repository.path().join("src/routes/orders/+page.ts"),
        "export async function load(): Promise<object> { const response = await fetch('/api/orders'); return { response }; }\n",
    );
        write(
        repository.path().join("src/routes/orders/+page.server.ts"),
        "import type { Order } from '$lib/orders/types'; export function load(): Order { return { id: '1' }; }\n",
    );
        write(
        repository.path().join("src/routes/orders/+page.svelte"),
        "<script lang=\"ts\">import Button from '../../ui-kit/button/button.svelte';</script><Button />\n",
    );
        write(
        repository
            .path()
            .join("src/lib/orders/components/OrderCard.svelte"),
        "<script lang=\"ts\">let { onOpen }: { onOpen: () => void } = $props();</script><button onclick={onOpen}>Open</button>\n",
    );
        write(
            repository.path().join("src/ui-kit/button/button.svelte"),
            "<button><slot /></button>\n",
        );
        write(
            repository.path().join("src/ui-kit/utils.ts"),
            "export const className: string = 'button';\n",
        );
        let process_directory = poison_processes(repository.path());

        let output =
            run_internal_web_check_with(repository.path(), &["--no-cache"], &process_directory);

        assert_eq!(
            output.status.code(),
            Some(test_case.expected_exit_code),
            "{}: {} {}",
            test_case.description,
            String::from_utf8_lossy(&output.stdout),
            String::from_utf8_lossy(&output.stderr)
        );
        assert!(
            !repository.path().join("process-invoked").exists(),
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_invalid_generic_typescript_tests_when_checking_then_complete_retained_test_policy_reports()
{
    let test_cases = [WebPolicyCheckTestCase {
        description: "invalid TypeScript tests cover every retained FWT rule",
        expected_exit_code: 1,
    }];
    for test_case in test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        write(
        repository.path().join("fensu.toml"),
        "[targets.web]\nanalyzer = \"typescript\"\nroots = [\"src\"]\ntests = [\"tests\"]\ntooling = []\nselect = [\"FWT\"]\n[targets.web.cache]\nenabled = false\n",
    );
        write(
            repository
                .path()
                .join("src/lib/orders/_state/order.state.svelte.ts"),
            "export function createOrderState(): object { return {}; }\n",
        );
        write(
            repository.path().join("src/lib/orders/_adapters/order.ts"),
            "export function createOrderAdapter(): object { return {}; }\n",
        );
        write(
        repository.path().join("tests/orphan/bad.test.ts"),
        concat!(
            "interface Case { value: string; }\n",
            "const cases: Case[] = [{ value: 'x' }];\n",
            "test.skip('pending', () => {});\n",
            "test('bad name', () => {});\n",
            "test.each<Case>(cases)('bad title', (item) => {\n",
            "  if (item.value) { expect(item.value).toBe('x'); }\n",
            "});\n",
            "test.each<Case>([])('$description', (testCase) => {\n",
            "  if (testCase.value) { testCase.value = 'changed'; } expect(testCase.value).toBe('changed');\n",
            "});\n",
            "test.each<Case>([['x']])('$description', (testCase) => {\n",
            "  expect(testCase.value).toBe('x');\n",
            "});\n",
        ),
    );
        let process_directory = poison_processes(repository.path());

        let output =
            run_internal_web_check_with(repository.path(), &["--no-cache"], &process_directory);
        let stdout = String::from_utf8_lossy(&output.stdout);

        assert_eq!(
            output.status.code(),
            Some(test_case.expected_exit_code),
            "{}",
            test_case.description
        );
        for code in [
            "FWT001", "FWT002", "FWT003", "FWT004", "FWT201", "FWT202", "FWT302", "FWT401",
            "FWT402", "FWT403", "FWT404", "FWT405", "FWT406", "FWT410", "FWT411", "FWT412",
        ] {
            assert!(stdout.contains(code), "missing {code}: {stdout}");
        }
    }
}

#[test]
fn given_exact_generic_typescript_test_conventions_when_checking_then_near_misses_pass() {
    let test_cases = [WebPolicyCheckTestCase {
        description: "exact TypeScript test conventions pass",
        expected_exit_code: 0,
    }];
    for test_case in test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        write(
        repository.path().join("fensu.toml"),
        "[targets.web]\nanalyzer = \"typescript\"\nroots = [\"src\"]\ntests = [\"tests\"]\ntooling = []\nselect = [\"FWT\"]\n[targets.web.cache]\nenabled = false\n",
    );
        write(
            repository
                .path()
                .join("src/lib/orders/_state/order.state.svelte.ts"),
            "export function createOrderState(): object { return {}; }\n",
        );
        write(
        repository
            .path()
            .join("tests/lib/orders/_state/order.state.test.ts"),
        concat!(
            "interface Case { readonly description: string; readonly value: string; readonly expectedValue: string; }\n",
            "test.each<Case>([{ description: 'returns value', value: 'x', expectedValue: 'x' }])",
            "('$description', (testCase) => {\n",
            "  expect(testCase.value).toBe(testCase.expectedValue);\n",
            "});\n",
            "test('given value when reading then returns value', () => { expect('x').toBe('x'); });\n",
        ),
    );
        let process_directory = poison_processes(repository.path());

        let output =
            run_internal_web_check_with(repository.path(), &["--no-cache"], &process_directory);

        assert_eq!(
            output.status.code(),
            Some(test_case.expected_exit_code),
            "{}: {}",
            test_case.description,
            String::from_utf8_lossy(&output.stdout),
        );
    }
}

#[test]
fn given_parameterized_case_type_when_checking_then_fwt403_requires_a_resolved_nonempty_readonly_declaration(
) {
    let test_cases = [
        WebTestCaseTypeResolutionTestCase {
            description: "resolved owner-local readonly case type passes",
            test_source: "import type { Case } from './_test/case'; test.each<Case>([{ description: 'case', expected: 'x' }])('$description', (testCase) => expect(testCase.expected).toBe('x'));\n",
            support_source:
                "export interface Case { readonly description: string; readonly expected: string; }\n",
            expected_exit_code: 0,
            expected_fwt403: false,
        },
        WebTestCaseTypeResolutionTestCase {
            description: "comment text cannot spoof an owner-local type import",
            test_source: "// import type { Case } from './_test/case';\ntest.each<Case>([{ description: 'case', expected: 'x' }])('$description', (testCase) => expect(testCase.expected).toBe('x'));\n",
            support_source: "",
            expected_exit_code: 1,
            expected_fwt403: true,
        },
        WebTestCaseTypeResolutionTestCase {
            description: "empty local interface is not a readonly behavior-case contract",
            test_source: "interface Case {} test.each<Case>([{}])('$description', (testCase) => expect(true).toBe(true));\n",
            support_source: "",
            expected_exit_code: 1,
            expected_fwt403: true,
        },
    ];
    for test_case in &test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        write(
            repository.path().join("fensu.toml"),
            "[targets.web]\nanalyzer = \"typescript\"\nroots = [\"src\"]\ntests = [\"tests\"]\ntooling = []\nselect = [\"FWT201\", \"FWT202\", \"FWT403\"]\n[targets.web.cache]\nenabled = false\n",
        );
        write(repository.path().join("src/value.ts"), VALID_TYPESCRIPT);
        write(
            repository.path().join("tests/lib/orders/value.test.ts"),
            test_case.test_source,
        );
        write(
            repository.path().join("tests/lib/orders/_test/case.ts"),
            test_case.support_source,
        );
        let process_directory = poison_processes(repository.path());

        let output =
            run_internal_web_check_with(repository.path(), &["--no-cache"], &process_directory);
        let stdout = String::from_utf8_lossy(&output.stdout);

        assert_eq!(
            output.status.code(),
            Some(test_case.expected_exit_code),
            "{}: {stdout}",
            test_case.description
        );
        assert_eq!(
            stdout.contains("FWT403"),
            test_case.expected_fwt403,
            "{}: {stdout}",
            test_case.description
        );
    }
}

#[test]
fn given_imported_owner_local_case_models_when_checking_then_description_and_expected_are_enforced()
{
    let test_cases = [
        WebSourcePurposeTestCase {
            description: "imported case model without description emits only FWT201",
            config: "[targets.web]\nanalyzer = \"typescript\"\nroots = [\"src\"]\ntests = [\"tests\"]\ntooling = []\nselect = [\"FWT201\", \"FWT202\"]\n[targets.web.cache]\nenabled = false\n",
            files: &[
                ("src/value.ts", VALID_TYPESCRIPT),
                (
                    "tests/lib/orders/value.test.ts",
                    "import type { Case } from './_test/case'; test.each<Case>([{ expectedValue: 'x' }])('$description', (testCase) => expect(testCase.expectedValue).toBe('x'));\n",
                ),
                (
                    "tests/lib/orders/_test/case.ts",
                    "export interface Case { readonly expectedValue: string; }\n",
                ),
            ],
            expected_exit_code: 1,
            expected_present: Some("FWT201"),
            expected_absent: Some("FWT202"),
        },
        WebSourcePurposeTestCase {
            description: "imported case model without expected emits only FWT202",
            config: "[targets.web]\nanalyzer = \"typescript\"\nroots = [\"src\"]\ntests = [\"tests\"]\ntooling = []\nselect = [\"FWT201\", \"FWT202\"]\n[targets.web.cache]\nenabled = false\n",
            files: &[
                ("src/value.ts", VALID_TYPESCRIPT),
                (
                    "tests/lib/orders/value.test.ts",
                    "import type { Case } from './_test/case'; test.each<Case>([{ description: 'case' }])('$description', (testCase) => expect(testCase.description).toBe('case'));\n",
                ),
                (
                    "tests/lib/orders/_test/case.ts",
                    "export interface Case { readonly description: string; }\n",
                ),
            ],
            expected_exit_code: 1,
            expected_present: Some("FWT202"),
            expected_absent: Some("FWT201"),
        },
    ];
    for test_case in &test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        write(repository.path().join("fensu.toml"), test_case.config);
        for (path, source) in test_case.files {
            write(repository.path().join(path), source);
        }
        let process_directory = poison_processes(repository.path());

        let output =
            run_internal_web_check_with(repository.path(), &["--no-cache"], &process_directory);
        let stdout = String::from_utf8_lossy(&output.stdout);

        assert_eq!(output.status.code(), Some(test_case.expected_exit_code));
        assert_eq!(
            stdout.matches("FWT20").count(),
            1,
            "{}: {stdout}",
            test_case.description
        );
        assert!(
            stdout.contains(test_case.expected_present.expect("expected diagnostic")),
            "{}: {stdout}",
            test_case.description
        );
        assert!(
            !stdout.contains(test_case.expected_absent.expect("absent diagnostic")),
            "{}: {stdout}",
            test_case.description
        );
    }
}

#[test]
fn given_project_import_cycle_when_checking_then_one_deterministic_fwl201_fault_is_reported() {
    let test_cases = [WebPolicyCheckTestCase {
        description: "one deterministic cycle fault is emitted",
        expected_exit_code: 1,
    }];
    for test_case in test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        write(
        repository.path().join("fensu.toml"),
        "[targets.web]\nanalyzer = \"typescript\"\nroots = [\"src\"]\ntests = []\ntooling = []\nselect = [\"FWL201\"]\n[targets.web.cache]\nenabled = false\n",
    );
        write(
            repository.path().join("src/first.ts"),
            "import { second } from './second';\nexport const first: number = second;\n",
        );
        write(
            repository.path().join("src/second.ts"),
            "import { first } from './first';\nexport const second: number = first;\n",
        );
        let process_directory = poison_processes(repository.path());

        let output =
            run_internal_web_check_with(repository.path(), &["--no-cache"], &process_directory);
        let stdout = String::from_utf8_lossy(&output.stdout);

        assert_eq!(
            output.status.code(),
            Some(test_case.expected_exit_code),
            "{}",
            test_case.description
        );
        assert_eq!(stdout.matches("FWL201").count(), 1);
        assert!(stdout.contains("src/first.ts -> src/second.ts -> src/first.ts"));
    }
}

#[test]
fn given_web_warning_exception_and_ignore_when_checking_then_shared_policy_order_is_preserved() {
    let test_cases = [WebPolicyCheckTestCase {
        description: "web diagnostics use shared policy ordering",
        expected_exit_code: 0,
    }];
    for test_case in test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        write(
        repository.path().join("fensu.toml"),
        "[targets.web]\nanalyzer = \"typescript\"\nroots = [\"src\"]\ntests = []\ntooling = []\nselect = [\"FWA001\"]\nwarn = [\"FWA002\"]\nignore = []\n[targets.web.cache]\nenabled = false\n[[targets.web.rule_exceptions]]\nrule = \"FWA001\"\npath = \"src/exempt.ts\"\nreason = \"External callback contract.\"\n[[targets.web.rule_ignores]]\nrules = [\"FWA002\"]\npaths = [\"src/exempt.ts\", \"src/ignored.ts\"]\nreason = \"Generated declaration.\"\n",
    );
        write(
            repository.path().join("src/exempt.ts"),
            "export function exempt(value) { return value; }\n",
        );
        write(
            repository.path().join("src/ignored.ts"),
            "export function ignored(value: string) { return value; }\n",
        );
        let process_directory = poison_processes(repository.path());

        let output = run_internal_web_check_with(
            repository.path(),
            &["--no-cache", "--warn"],
            &process_directory,
        );

        assert_eq!(
            output.status.code(),
            Some(test_case.expected_exit_code),
            "{}",
            test_case.description
        );
        assert!(!String::from_utf8_lossy(&output.stdout).contains("FWA"));
    }
}

#[test]
fn given_web_threshold_and_path_override_when_checking_then_exact_boundary_and_override_apply() {
    let test_cases = [WebPolicyCheckTestCase {
        description: "web thresholds preserve strict boundaries and path overrides",
        expected_exit_code: 1,
    }];
    for test_case in test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        write(
        repository.path().join("fensu.toml"),
        "[targets.web]\nanalyzer = \"typescript\"\nroots = [\"src\"]\ntests = []\ntooling = []\nselect = [\"FWS010\"]\n[targets.web.thresholds]\nmax_arguments = 1\n[targets.web.cache]\nenabled = false\n[[targets.web.threshold_overrides]]\npaths = [\"src/relaxed.ts\"]\nthresholds = { max_arguments = 2 }\nreason = \"External two-argument callback.\"\n",
    );
        write(
        repository.path().join("src/failing.ts"),
        "export function failing(first: string, second: string): string { return first + second; }\n",
    );
        write(
            repository.path().join("src/boundary.ts"),
            "export function boundary(value: string): string { return value; }\n",
        );
        write(
        repository.path().join("src/relaxed.ts"),
        "export function relaxed(first: string, second: string): string { return first + second; }\n",
    );
        let process_directory = poison_processes(repository.path());

        let output =
            run_internal_web_check_with(repository.path(), &["--no-cache"], &process_directory);
        let stdout = String::from_utf8_lossy(&output.stdout);

        assert_eq!(
            output.status.code(),
            Some(test_case.expected_exit_code),
            "{}",
            test_case.description
        );
        assert_eq!(stdout.matches("FWS010").count(), 1);
        assert!(stdout.contains("src/failing.ts"));
        assert!(!stdout.contains("src/boundary.ts"));
        assert!(!stdout.contains("src/relaxed.ts:1:"));
    }
}

#[cfg(unix)]
#[test]
fn given_extended_config_symlink_escape_when_checking_then_canonical_confinement_fails_closed() {
    use std::os::unix::fs::symlink;

    let test_cases = [WebConfigFailureTestCase {
        description: "nearest existing symlink ancestor cannot escape the repository",
        files: &[(
            "tsconfig.json",
            "{ \"extends\": \"./config/external/missing\" }\n",
        )],
        expected_error: "TypeScript config path escapes the repository:",
    }];
    for test_case in &test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        let external = tempfile::tempdir().expect("external directory");
        write(repository.path().join("fensu.toml"), CONFIG);
        write(repository.path().join("src/value.ts"), VALID_TYPESCRIPT);
        for (path, content) in test_case.files {
            write(repository.path().join(path), content);
        }
        crate::helpers::create_directory(repository.path().join("config"));
        symlink(external.path(), repository.path().join("config/external"))
            .expect("escaping config symlink");
        let process_directory = poison_processes(repository.path());

        let output =
            run_internal_web_check_with(repository.path(), &["--no-cache"], &process_directory);

        assert_eq!(output.status.code(), Some(2), "{}", test_case.description);
        assert!(
            String::from_utf8_lossy(&output.stderr).contains(test_case.expected_error),
            "{}: {}",
            test_case.description,
            String::from_utf8_lossy(&output.stderr)
        );
    }
}

#[cfg(unix)]
#[test]
fn given_extended_config_symlink_alias_cycle_when_checking_then_canonical_identity_detects_cycle() {
    use std::os::unix::fs::symlink;

    let test_cases = [WebConfigFailureTestCase {
        description: "symlink aliases use canonical config identity for cycle detection",
        files: &[("tsconfig.json", "{ \"extends\": \"./config/base\" }\n")],
        expected_error: "TypeScript config extends cycle: tsconfig.json -> tsconfig.json.",
    }];
    for test_case in &test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        write(repository.path().join("fensu.toml"), CONFIG);
        write(repository.path().join("src/value.ts"), VALID_TYPESCRIPT);
        for (path, content) in test_case.files {
            write(repository.path().join(path), content);
        }
        crate::helpers::create_directory(repository.path().join("config"));
        symlink(
            repository.path().join("tsconfig.json"),
            repository.path().join("config/base.json"),
        )
        .expect("config cycle symlink");
        let process_directory = poison_processes(repository.path());

        let output =
            run_internal_web_check_with(repository.path(), &["--no-cache"], &process_directory);

        assert_eq!(output.status.code(), Some(2), "{}", test_case.description);
        assert!(
            String::from_utf8_lossy(&output.stderr).contains(test_case.expected_error),
            "{}: {}",
            test_case.description,
            String::from_utf8_lossy(&output.stderr)
        );
    }
}

#[cfg(unix)]
#[test]
fn given_unreadable_source_directory_when_checking_then_discovery_error_is_reported() {
    use std::fs;
    use std::os::unix::fs::PermissionsExt;

    let test_cases = [WebConfigFailureTestCase {
        description: "WalkDir permission failures are not silently discarded",
        files: &[("src/value.ts", VALID_TYPESCRIPT)],
        expected_error: "Could not discover sources under src:",
    }];
    for test_case in &test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        write(repository.path().join("fensu.toml"), CONFIG);
        for (path, content) in test_case.files {
            write(repository.path().join(path), content);
        }
        let denied = repository.path().join("src/denied");
        crate::helpers::create_directory(&denied);
        fs::set_permissions(&denied, fs::Permissions::from_mode(0o000))
            .expect("deny directory traversal");
        let process_directory = poison_processes(repository.path());

        let output =
            run_internal_web_check_with(repository.path(), &["--no-cache"], &process_directory);
        fs::set_permissions(&denied, fs::Permissions::from_mode(0o755))
            .expect("restore directory traversal");

        assert_eq!(output.status.code(), Some(2), "{}", test_case.description);
        assert!(
            String::from_utf8_lossy(&output.stderr).contains(test_case.expected_error),
            "{}: {}",
            test_case.description,
            String::from_utf8_lossy(&output.stderr)
        );
    }
}

include!("web_policy_fixtures.inc");
