use crate::helpers::{
    poison_processes, run_internal_web_check_with, run_with_internal_web_gate, write,
};
use crate::test_types::{
    HostedWebPolicyTestCase, InternalGateCommandTestCase, WebCacheCheckTestCase,
    WebConfigFailureTestCase, WebParseDiagnosticTestCase,
};

const CONFIG: &str = "[targets.a_typescript]\nanalyzer = \"typescript\"\nroots = [\"src\"]\ntests = []\ntooling = []\nselect = []\n\n[targets.a_typescript.cache]\nenabled = true\n\n[targets.a_typescript.evaluation]\nexclude = [\"src/lib/value.ts\"]\n\n[targets.b_svelte]\nanalyzer = \"svelte\"\nroots = [\"src\"]\ntests = []\ntooling = []\nselect = []\n\n[targets.b_svelte.cache]\nenabled = true\n";
const VALID_COMPONENT: &str = "<script lang=\"ts\">\nimport { value } from '$lib/value';\nconst doubled: number = value * 2;\n</script>\n<p>{doubled}</p>\n";
const VALID_TYPESCRIPT: &str = "export const value: number = 2;\n";

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
                .contains("Evaluation: 8 of 9 source files (1 excluded by config)"),
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
fn given_malformed_web_sources_when_checking_then_diagnostics_name_repository_path_line_and_column()
{
    let test_cases = [WebParseDiagnosticTestCase {
        description: "malformed native web sources report repository positions without hosts",
        expected_svelte: "Could not parse Svelte source: src/App.svelte:2:",
        expected_typescript: "Could not parse TypeScript source: src/lib/value.ts:1:",
    }];
    for test_case in &test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        write(repository.path().join("fensu.toml"), CONFIG);
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
            Some(2),
            "{}",
            test_case.description
        );
        assert!(
            String::from_utf8_lossy(&malformed_svelte.stderr).contains(test_case.expected_svelte),
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
            Some(2),
            "{}",
            test_case.description
        );
        assert!(
            String::from_utf8_lossy(&malformed_typescript.stderr)
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
fn given_internal_check_gate_when_running_other_commands_then_backends_remain_unavailable() {
    let test_cases = [
        InternalGateCommandTestCase {
            description: "rule capability remains unavailable",
            arguments: &["rule", "FFA001", "--target", "a_typescript"],
            expected_error: "Known analyzer backend unavailable: typescript",
        },
        InternalGateCommandTestCase {
            description: "map capability remains unavailable",
            arguments: &["map", "symbol", "--target", "a_typescript", "--no-cache"],
            expected_error: "Known analyzer backend unavailable: typescript",
        },
        InternalGateCommandTestCase {
            description: "skills capability remains unavailable",
            arguments: &["skills", "--config-target", "a_typescript", "--check"],
            expected_error: "Known analyzer backend unavailable: typescript",
        },
    ];
    for test_case in &test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        write(repository.path().join("fensu.toml"), CONFIG);
        write(repository.path().join("src/value.ts"), VALID_TYPESCRIPT);

        let output = run_with_internal_web_gate(repository.path(), test_case.arguments);

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
fn given_hosted_policy_and_malformed_web_source_when_checking_then_native_parser_still_owns_failure(
) {
    let test_cases = [HostedWebPolicyTestCase {
        description: "hosted policy cannot bypass native TypeScript parsing",
        config: "[targets.web]\nanalyzer = \"typescript\"\nroots = [\"src\"]\ntests = []\ntooling = []\nselect = []\nrule_paths = [\"rules/custom.py\"]\n",
        expected_error: "Could not parse TypeScript source: src/malformed.ts:1:",
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
