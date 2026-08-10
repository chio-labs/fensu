use std::fs;
use std::process::Command;

use crate::helpers::{poison_processes, run_internal_web_check_with, write};
use crate::test_types::{
    CheckCacheTestCase, FreshSvelteKitCheckTestCase, MixedWebExecutionTestCase,
    WebConfigFailureTestCase, WebDiagnosticCountTestCase, WebSourcePurposeTestCase,
    WebThresholdCacheIdentityTestCase,
};

#[test]
fn given_fresh_racewatch_sveltekit_shape_when_checking_then_ui_alias_resolves_without_node() {
    let test_cases = [FreshSvelteKitCheckTestCase {
        description:
            "RaceWatch literal $ui-kit alias resolves before generated SvelteKit config exists",
        expected_exit_code: 0,
        expected_cold_cache: "hits=0 misses=2",
        expected_warm_cache: "hits=2 misses=0",
        expected_appearance_cache: "hits=0 misses=2",
    }];
    for test_case in &test_cases {
        let repository = tempfile::tempdir().expect("fresh SvelteKit repository");
        write(
            repository.path().join("fensu.toml"),
            "[targets.web]\nanalyzer = \"svelte\"\nframework = \"sveltekit\"\nroots = [\"src\"]\ntests = []\ntooling = []\nselect = []\n[targets.web.cache]\nenabled = true\n",
        );
        write(
            repository.path().join("tsconfig.json"),
            "{ \"extends\": \"./.svelte-kit/tsconfig.json\" }\n",
        );
        write(
            repository.path().join("svelte.config.js"),
            "import adapter from '@sveltejs/adapter-static';\nconst config = { kit: { adapter: adapter(), alias: { $lib: 'src/lib', '$ui-kit': 'src/ui-kit' } } };\nexport default config;\n",
        );
        write(
            repository.path().join("src/App.svelte"),
            "<script lang=\"ts\">import * as Button from '$ui-kit/button';</script>\n<Button.Button />\n",
        );
        write(
            repository.path().join("src/ui-kit/button/index.ts"),
            "export const Button = 1;\n",
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
        crate::helpers::create_directory(repository.path().join(".svelte-kit"));
        write(repository.path().join(".svelte-kit/tsconfig.json"), "{}\n");
        let generated_appeared = run_internal_web_check_with(
            repository.path(),
            &["--cache", "--cache-stats"],
            &process_directory,
        );

        assert_eq!(
            cold.status.code(),
            Some(test_case.expected_exit_code),
            "{}",
            test_case.description
        );
        assert_eq!(
            warm.status.code(),
            Some(test_case.expected_exit_code),
            "{}",
            test_case.description
        );
        assert_eq!(
            generated_appeared.status.code(),
            Some(test_case.expected_exit_code),
            "{}",
            test_case.description
        );
        assert!(
            String::from_utf8_lossy(&cold.stderr).contains(test_case.expected_cold_cache),
            "{}",
            test_case.description
        );
        assert!(
            String::from_utf8_lossy(&warm.stderr).contains(test_case.expected_warm_cache),
            "{}",
            test_case.description
        );
        assert!(
            String::from_utf8_lossy(&generated_appeared.stderr)
                .contains(test_case.expected_appearance_cache),
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
fn given_route_roles_and_server_exports_when_checking_then_boundaries_apply_without_lib_ownership()
{
    let test_cases = [
        WebDiagnosticCountTestCase {
            description: "route-local _api is an API role but not a lib capability",
            config: "[targets.web]\nanalyzer = \"svelte\"\nframework = \"sveltekit\"\nroots = [\"src\"]\ntests = []\ntooling = []\nselect = [\"FWS110\", \"FWR309\"]\n[targets.web.thresholds]\nmax_api_lines = 0\n[targets.web.cache]\nenabled = false\n",
            files: &[(
                "src/routes/orders/_api/read.ts",
                "export function read(): string { return 'order'; }\n",
            )],
            expected_exit_code: 1,
            expected_counts: &[("FWS110", 1)],
            expected_absent: Some("FWR309"),
        },
        WebDiagnosticCountTestCase {
            description: "generic TypeScript _api modules receive API line and export budgets",
            config: "[targets.web]\nanalyzer = \"typescript\"\nroots = [\"src\"]\ntests = []\ntooling = []\nselect = [\"FWS110\", \"FWS111\"]\n[targets.web.thresholds]\nmax_api_lines = 0\nmax_api_exports = 0\n[targets.web.cache]\nenabled = false\n",
            files: &[(
                "src/lib/orders/_api/read.ts",
                "export function read(): string { return 'order'; }\n",
            )],
            expected_exit_code: 1,
            expected_counts: &[("FWS110", 1), ("FWS111", 1)],
            expected_absent: None,
        },
        WebDiagnosticCountTestCase {
            description: "arbitrary server capability segments remain browser-classified",
            config: "[targets.web]\nanalyzer = \"svelte\"\nframework = \"sveltekit\"\nroots = [\"src\"]\ntests = []\ntooling = []\nselect = [\"FWL106\"]\n[targets.web.cache]\nenabled = false\n",
            files: &[(
                "src/lib/orders/server/read.ts",
                "import fs from 'node:fs'; export const read = (): object => fs;\n",
            )],
            expected_exit_code: 1,
            expected_counts: &[("FWL106", 1)],
            expected_absent: None,
        },
        WebDiagnosticCountTestCase {
            description: "SvelteKit lib/server modules remain server-only",
            config: "[targets.web]\nanalyzer = \"svelte\"\nframework = \"sveltekit\"\nroots = [\"src\"]\ntests = []\ntooling = []\nselect = [\"FWL106\"]\n[targets.web.cache]\nenabled = false\n",
            files: &[(
                "src/lib/server/read.ts",
                "import fs from 'node:fs'; export const read = (): object => fs;\n",
            )],
            expected_exit_code: 0,
            expected_counts: &[("FWL106", 0)],
            expected_absent: Some("FWL106"),
        },
        WebDiagnosticCountTestCase {
        description: "server load, action, and HTTP handler exports receive entry budgets",
        config: "[targets.web]\nanalyzer = \"svelte\"\nframework = \"sveltekit\"\nroots = [\"src\"]\ntests = []\ntooling = []\nselect = [\"FWS001\", \"FWS002\", \"FWS003\"]\n[targets.web.thresholds]\nmax_entry_statements = 0\nmax_entry_distinct_calls = 0\nmax_entry_locals = 0\nmax_function_statements = 70\n[targets.web.cache]\nenabled = false\n",
        files: &[
            (
                "src/routes/orders/+page.server.ts",
                "declare function read(): string;\nexport function load(): object { const value = read(); return { value }; }\nexport const actions = { default: async (): Promise<object> => { const value = read(); return { value }; } };\n",
            ),
            (
                "src/routes/orders/+server.ts",
                "declare function read(): string;\nexport function GET(): Response { const value = read(); return new Response(value); }\n",
            ),
        ],
        expected_exit_code: 1,
        expected_counts: &[("FWS001", 3), ("FWS002", 3), ("FWS003", 3)],
        expected_absent: None,
        },
        WebDiagnosticCountTestCase {
            description: "web threshold alias retains path override behavior",
            config: "[targets.web]\nanalyzer = \"svelte\"\nframework = \"sveltekit\"\nroots = [\"src\"]\ntests = []\ntooling = []\nselect = [\"FWS001\"]\n[targets.web.thresholds]\nmax_entry_statements = 0\n[[targets.web.threshold_overrides]]\npaths = [\"src/routes/relaxed/+page.server.ts\"]\nthresholds = { max_entry_statements = 10 }\nreason = \"Relaxed generated entry.\"\n[targets.web.cache]\nenabled = false\n",
            files: &[
                (
                    "src/routes/strict/+page.server.ts",
                    "export function load(): number { return 1; }\n",
                ),
                (
                    "src/routes/relaxed/+page.server.ts",
                    "export function load(): number { return 1; }\n",
                ),
            ],
            expected_exit_code: 1,
            expected_counts: &[("FWS001", 1)],
            expected_absent: None,
        },
    ];
    for test_case in &test_cases {
        let repository = tempfile::tempdir().expect("web diagnostic repository");
        write(repository.path().join("fensu.toml"), test_case.config);
        for (path, content) in test_case.files {
            write(repository.path().join(path), content);
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
        for (code, count) in test_case.expected_counts {
            assert_eq!(
                stdout.matches(code).count(),
                *count,
                "{}: {stdout}",
                test_case.description
            );
        }
        assert!(
            test_case
                .expected_absent
                .is_none_or(|value| !stdout.contains(value)),
            "{}: {stdout}",
            test_case.description
        );
        assert!(!repository.path().join("process-invoked").exists());
    }
}

#[test]
fn given_alias_and_canonical_web_thresholds_when_caching_then_identity_is_shared() {
    let test_cases = [WebThresholdCacheIdentityTestCase {
        description: "alias and canonical threshold spellings share native cache identity",
        alias: "max_entry_statements",
        canonical: "max_statements",
        expected_exit_code: 0,
        expected_cold: "hits=0 misses=1",
        expected_warm: "hits=1 misses=0",
    }];
    for test_case in &test_cases {
        let repository = tempfile::tempdir().expect("web threshold cache repository");
        let template = "[targets.web]\nanalyzer = \"svelte\"\nframework = \"sveltekit\"\nroots = [\"src\"]\ntests = []\ntooling = []\nselect = [\"FWS001\"]\n[targets.web.thresholds]\n{} = 40\n";
        write(
            repository.path().join("fensu.toml"),
            &template.replace("{}", test_case.alias),
        );
        write(
            repository.path().join("src/routes/+page.server.ts"),
            "export function load(): number { return 1; }\n",
        );
        let process_directory = poison_processes(repository.path());
        let cold = run_internal_web_check_with(
            repository.path(),
            &["--cache", "--cache-stats"],
            &process_directory,
        );
        write(
            repository.path().join("fensu.toml"),
            &template.replace("{}", test_case.canonical),
        );

        let warm = run_internal_web_check_with(
            repository.path(),
            &["--cache", "--cache-stats"],
            &process_directory,
        );

        assert_eq!(
            cold.status.code(),
            Some(test_case.expected_exit_code),
            "{}",
            test_case.description
        );
        assert_eq!(
            warm.status.code(),
            Some(test_case.expected_exit_code),
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
    }
}

#[test]
fn given_racewatch_web_empty_exclude_when_caching_then_identity_matches_omission() {
    let test_cases = [CheckCacheTestCase {
        description: "RaceWatch empty web exclusion reuses the omitted-exclusion cache",
        expected_exit_code: 0,
        expected_cold_fragment: "hits=0 misses=1",
        expected_warm_fragment: "hits=1 misses=0",
    }];
    for test_case in &test_cases {
        let repository = tempfile::tempdir().expect("RaceWatch web cache repository");
        let template = "[targets.web]\nanalyzer = \"svelte\"\nroot = \"frontend\"\nframework = \"sveltekit\"\nroots = [\"src\"]\ntests = [\"tests\"]\ntooling = [\"tooling\"]\nui_kit = \"src/ui-kit\"\ntest_layout = \"mirrored\"\nselect = [\"FW\"]\n\n[targets.web.thresholds]\nmax_route_script_lines = 200\nmax_component_script_lines = 250\nmax_state_lines = 300\nmax_imported_bindings = 20\nmax_public_exports = 20\nmax_state_public_members = 20\nmax_state_cells = 15\nmax_total_runes = 20\nmax_state_functions = 15\nmax_resource_families = 1\nmax_main_container_modules = 20\nmax_helpers_container_modules = 10\nmax_role_depth = 1\nmax_function_statements = 70\nmax_entry_statements = 40\nmax_entry_distinct_calls = 20\nmax_entry_locals = 20\nmax_arguments = 10\nmax_file_lines = 2000\nmax_api_lines = 200\nmax_api_exports = 3\n\n[targets.web.evaluation]\ninclude = [\"src/**/*.{ts,js,svelte}\", \"tests/**/*.ts\", \"tooling/**/*.ts\"]\n{}";
        write(
            repository.path().join("fensu.toml"),
            &template.replace("{}", ""),
        );
        write(
            repository.path().join("frontend/src/lib/value.ts"),
            "export const value = 1;\n",
        );
        let process_directory = poison_processes(repository.path());
        let cold = run_internal_web_check_with(
            repository.path(),
            &["--cache", "--cache-stats"],
            &process_directory,
        );
        write(
            repository.path().join("fensu.toml"),
            &template.replace("{}", "exclude = []\n"),
        );

        let warm = run_internal_web_check_with(
            repository.path(),
            &["--cache", "--cache-stats"],
            &process_directory,
        );

        assert_eq!(
            cold.status.code(),
            Some(test_case.expected_exit_code),
            "{}: {}",
            test_case.description,
            String::from_utf8_lossy(&cold.stderr)
        );
        assert_eq!(
            warm.status.code(),
            Some(test_case.expected_exit_code),
            "{}: {}",
            test_case.description,
            String::from_utf8_lossy(&warm.stderr)
        );
        assert!(
            String::from_utf8_lossy(&cold.stderr).contains(test_case.expected_cold_fragment),
            "{}",
            test_case.description
        );
        assert!(
            String::from_utf8_lossy(&warm.stderr).contains(test_case.expected_warm_fragment),
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_parser_and_framework_boundaries_when_checking_then_fail_closed_and_remain_analyzer_specific(
) {
    let test_cases = [
        WebSourcePurposeTestCase {
            description: "malformed direct TypeScript fails even without FWP001 selection",
            config: "[targets.web]\nanalyzer = \"typescript\"\nroots = [\"src\"]\ntests = []\ntooling = []\nselect = []\n[targets.web.cache]\nenabled = false\n",
            files: &[("src/broken.ts", "export const value: = 1;\n")],
            expected_exit_code: 1,
            expected_present: Some("FWP001"),
            expected_absent: None,
        },
        WebSourcePurposeTestCase {
            description: "generic TypeScript rejects Svelte resource policy",
            config: "[targets.web]\nanalyzer = \"typescript\"\nroots = [\"src\"]\ntests = []\ntooling = []\nselect = [\"FWV201\"]\n[targets.web.cache]\nenabled = false\n",
            files: &[(
                "src/lib/orders/main/read.ts",
                "export function read(): WebSocket { return new WebSocket('ws://localhost'); }\n",
            )],
            expected_exit_code: 2,
            expected_present: None,
            expected_absent: Some("FWV201"),
        },
        WebSourcePurposeTestCase {
            description: "nested UI-kit paths remain valid beneath a source root",
            config: "[targets.web]\nanalyzer = \"svelte\"\nframework = \"sveltekit\"\nroots = [\"src\"]\ntests = []\ntooling = []\nui_kit = \"src/lib/design/ui-kit\"\nselect = [\"FWU003\"]\n[targets.web.cache]\nenabled = false\n",
            files: &[(
                "src/lib/design/ui-kit/button/button.svelte",
                "<button><slot /></button>\n",
            )],
            expected_exit_code: 0,
            expected_present: None,
            expected_absent: Some("FWU003"),
        },
        WebSourcePurposeTestCase {
            description: "static trailing-slash endpoints require an exact OpenAPI path",
            config: "[targets.web]\nanalyzer = \"svelte\"\nframework = \"sveltekit\"\nroots = [\"src\"]\ntests = []\ntooling = []\nopenapi = \"openapi.json\"\nselect = [\"FWC201\"]\n[targets.web.cache]\nenabled = false\n",
            files: &[
                ("openapi.json", "{\"paths\":{\"/api/orders\":{}}}\n"),
                (
                    "src/lib/orders/_api/read.ts",
                    "export const endpoint = '/api/orders/';\n",
                ),
            ],
            expected_exit_code: 1,
            expected_present: Some("FWC201"),
            expected_absent: None,
        },
    ];
    for test_case in &test_cases {
        let repository = tempfile::tempdir().expect("web boundary repository");
        write(repository.path().join("fensu.toml"), test_case.config);
        for (path, content) in test_case.files {
            write(repository.path().join(path), content);
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
                .is_none_or(|value| stdout.contains(value)),
            "{}: {stdout}",
            test_case.description
        );
        assert!(
            test_case
                .expected_absent
                .is_none_or(|value| !stdout.contains(value)),
            "{}: {stdout}",
            test_case.description
        );
    }
}

#[cfg(unix)]
#[test]
fn given_python_custom_and_native_web_targets_when_checking_then_one_host_and_native_results_merge()
{
    let test_cases = [MixedWebExecutionTestCase {
        description: "mixed aggregate partitions Python hosting from native web evaluation",
        expected_exit_code: 1,
        expected_python_fault: "FFA001",
        expected_web_fault: "FWA102",
        expected_host_count_per_run: 1,
        expected_host_error: "fensu is not installed beside fensu-cli",
    }];
    let workspace_python =
        std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("../../.venv/bin/python");
    for test_case in &test_cases {
        assert!(workspace_python.is_file(), "workspace Python is required");
        let repository = tempfile::tempdir().expect("mixed analyzer repository");
        write(
            repository.path().join("fensu.toml"),
            "[targets.backend]\nanalyzer = \"python\"\nroots = [\"src/z-backend\"]\ntests = []\ntooling = []\nselect = [\"FFA001\", \"XMIX001\"]\nrule_paths = [\"rules/mixed.py\"]\n[targets.backend.evaluation]\nexclude = [\"src/z-backend/excluded.py\"]\n[targets.backend.cache]\nenabled = true\n[targets.frontend]\nanalyzer = \"svelte\"\nframework = \"sveltekit\"\nroots = [\"src/a-frontend\"]\ntests = []\ntooling = []\nselect = [\"FWA102\"]\n[targets.frontend.cache]\nenabled = true\n",
        );
        write(
            repository.path().join("src/z-backend/module.py"),
            "def untyped(value):\n    return value\n",
        );
        write(
            repository.path().join("src/z-backend/excluded.py"),
            "def excluded(value):\n    return value\n",
        );
        write(
            repository.path().join("rules/mixed.py"),
            "import ast\nimport os\nfrom pathlib import Path\nfrom fensu import Family, Fault, RuleContext, rule\nmarker = Path(os.environ['FENSU_HOST_MARKER'])\nmarker.write_text((marker.read_text() if marker.exists() else '') + 'x')\n@rule(code='XMIX001', family=Family.CUSTOM, slug='mixed', message='mixed')\ndef mixed(module: ast.Module, ctx: RuleContext) -> list[Fault]:\n    return []\n",
        );
        write(
            repository.path().join("src/a-frontend/Card.svelte"),
            "<script lang=\"ts\">const endpoint = '/api/orders';</script>\n",
        );
        let process_directory = poison_processes(repository.path());
        let host_marker = repository.path().join("host-count");

        let output = Command::new(env!("CARGO_BIN_EXE_fensu"))
            .args(["check", "--no-color", "--cache", "--cache-stats"])
            .current_dir(repository.path())
            .env("FENSU_PYTHON", &workspace_python)
            .env("FENSU_HOST_MARKER", &host_marker)
            .env(
                "FENSU_PROCESS_MARKER",
                repository.path().join("process-invoked"),
            )
            .env("PATH", &process_directory)
            .env("NO_COLOR", "1")
            .output()
            .expect("mixed check runs");
        let stdout = String::from_utf8_lossy(&output.stdout);
        let stderr = String::from_utf8_lossy(&output.stderr);

        assert_eq!(
            output.status.code(),
            Some(test_case.expected_exit_code),
            "{}: {stdout} {stderr}",
            test_case.description
        );
        assert!(stdout.contains(test_case.expected_python_fault));
        assert!(stdout.contains(test_case.expected_web_fault));
        assert!(
            stdout.find("src/a-frontend/Card.svelte") < stdout.find("src/z-backend/module.py"),
            "{}: {stdout}",
            test_case.description
        );
        assert_eq!(
            stdout.matches("Evaluation:").count(),
            1,
            "{}: {stdout}",
            test_case.description
        );
        assert_eq!(
            stderr.matches("Cache:").count(),
            1,
            "{}: {stderr}",
            test_case.description
        );
        assert_eq!(
            fs::read(&host_marker).expect("host marker").len(),
            test_case.expected_host_count_per_run
        );
        assert!(!repository.path().join("process-invoked").exists());

        let failed_host = Command::new(env!("CARGO_BIN_EXE_fensu"))
            .args(["check", "--no-color", "--no-cache"])
            .current_dir(repository.path())
            .env(
                "FENSU_PYTHON",
                repository.path().join("missing-python-host"),
            )
            .env("NO_COLOR", "1")
            .output()
            .expect("mixed check preserves native output when host fails");

        assert_eq!(
            failed_host.status.code(),
            Some(2),
            "{}",
            test_case.description
        );
        assert!(
            String::from_utf8_lossy(&failed_host.stdout).contains(test_case.expected_web_fault),
            "{}: {}",
            test_case.description,
            String::from_utf8_lossy(&failed_host.stdout)
        );
        assert!(
            String::from_utf8_lossy(&failed_host.stderr).contains(test_case.expected_host_error),
            "{}: {}",
            test_case.description,
            String::from_utf8_lossy(&failed_host.stderr)
        );
    }
}

#[cfg(unix)]
#[test]
fn given_target_local_dependency_symlink_when_checking_then_target_escape_fails_closed() {
    use std::os::unix::fs::symlink;

    let test_cases = [WebConfigFailureTestCase {
        description: "OpenAPI symlinks cannot escape the selected target root",
        files: &[("frontend/src/App.svelte", "<p>app</p>\n")],
        expected_error: "target-local web dependency escapes the target: contracts/openapi.json",
    }];
    for test_case in &test_cases {
        let repository = tempfile::tempdir().expect("target confinement repository");
        write(
            repository.path().join("fensu.toml"),
            "[targets.web]\nanalyzer = \"svelte\"\nroot = \"frontend\"\nframework = \"sveltekit\"\nroots = [\"src\"]\ntests = []\ntooling = []\nopenapi = \"contracts/openapi.json\"\nselect = [\"FWC201\"]\n",
        );
        for (path, content) in test_case.files {
            write(repository.path().join(path), content);
        }
        write(
            repository.path().join("outside/openapi.json"),
            "{\"paths\":{}}\n",
        );
        fs::create_dir_all(repository.path().join("frontend/contracts"))
            .expect("contracts directory");
        symlink(
            repository.path().join("outside/openapi.json"),
            repository.path().join("frontend/contracts/openapi.json"),
        )
        .expect("OpenAPI symlink");
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
