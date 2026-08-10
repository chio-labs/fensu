use std::fs;

use crate::analyzer::AnalyzerId;
use crate::check::_helpers::project as web;
use crate::models::ProjectInput;
use crate::tests::helpers::web_source;
use crate::tests::test_types::WebConfigInheritanceTestCase;
use crate::tests::test_types::WebTestSourceTestCase;
use crate::tests::test_types::{
    DynamicSvelteAliasTestCase, OptionalGeneratedConfigTestCase, SvelteKitAliasResolutionTestCase,
    WebDirectSourceTestCase, WebImportGraphTestCase, WebProjectPathTestCase,
    WebSymlinkResolutionTestCase,
};

#[test]
fn given_fresh_sveltekit_config_when_resolving_then_generated_extends_and_literal_aliases_are_static(
) {
    let test_cases = [SvelteKitAliasResolutionTestCase {
        description: "fresh generated extends and quoted/unquoted aliases resolve statically",
        expected_generated_present: false,
        expected_resolutions: &[
            ("$ui-kit/button", Some("src/ui-kit/button/index.ts")),
            ("plain/value", Some("src/plain/value.ts")),
        ],
    }];
    for test_case in &test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        let root = repository.path();
        fs::create_dir_all(root.join("src/ui-kit/button")).expect("UI-kit directory");
        fs::create_dir_all(root.join("src/plain")).expect("plain alias directory");
        fs::write(
            root.join("tsconfig.json"),
            "{ \"extends\": \"./.svelte-kit/tsconfig.json\" }\n",
        )
        .expect("fresh SvelteKit tsconfig");
        fs::write(
        root.join("svelte.config.js"),
        "const config = { kit: { alias: { '$ui-kit': 'src/ui-kit', plain: \"src/plain\" } } }; export default config;\n",
    )
    .expect("Svelte config");
        fs::write(
        root.join("src/App.svelte"),
        "<script lang=\"ts\">import { Button } from '$ui-kit/button'; import { value } from 'plain/value';</script>\n",
    )
    .expect("component");
        fs::write(
            root.join("src/ui-kit/button/index.ts"),
            "export const Button = 1;\n",
        )
        .expect("UI-kit module");
        fs::write(root.join("src/plain/value.ts"), "export const value = 1;\n")
            .expect("plain alias module");
        let config = crate::models::Config {
            analyzer: AnalyzerId::Svelte,
            framework: Some("sveltekit".to_owned()),
            ..crate::models::Config::default()
        };

        let inputs =
            web::discover_project_inputs(root, root, &config).expect("fresh project inputs");
        let generated = inputs
            .iter()
            .find(|input| input.target_path == ".svelte-kit/tsconfig.json")
            .expect("tracked generated config");
        let parsed = web::parse_sources(
            AnalyzerId::Svelte,
            root,
            vec![
                web_source(root, "src/App.svelte"),
                web_source(root, "src/ui-kit/button/index.ts"),
                web_source(root, "src/plain/value.ts"),
            ],
            &inputs,
            &["src".to_owned()],
        )
        .expect("static aliases resolve");

        assert_eq!(
            generated.present, test_case.expected_generated_present,
            "{}",
            test_case.description
        );
        assert_eq!(
            parsed[0]
                .imports
                .iter()
                .map(|fact| (fact.specifier.as_str(), fact.resolved_path.as_deref()))
                .collect::<Vec<_>>(),
            test_case.expected_resolutions,
            "{}",
            test_case.description
        );
    }
}

#[cfg(unix)]
#[test]
fn given_symlinked_web_roots_when_resolving_then_internal_targets_work_and_escapes_fail() {
    use std::os::unix::fs::symlink;

    let test_cases = [WebSymlinkResolutionTestCase {
        description: "canonical source roots resolve internal aliases and reject external roots",
        expected_resolutions: &[
            ("$lib/value", Some("real/src/lib/value.ts")),
            ("$shared/value", Some("real/src/lib/value.ts")),
            ("@/lib/value", Some("real/src/lib/value.ts")),
        ],
        expected_source_escape_error: "Web source root escapes the target: escaped.",
        expected_alias_escape_error: "Web import candidate escapes the target:",
        expected_base_url_escape_error: "Web import candidate escapes the target:",
    }];
    for test_case in &test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        let external = tempfile::tempdir().expect("external source root");
        let root = repository.path();
        fs::create_dir_all(root.join("real/src/lib")).expect("real source root");
        fs::write(
            root.join("real/src/App.svelte"),
            "<script lang=\"ts\">import lib from '$lib/value'; import shared from '$shared/value'; import alias from '@/lib/value';</script>\n",
        )
        .expect("component");
        fs::write(root.join("real/src/lib/value.ts"), "export default 1;\n")
            .expect("library module");
        fs::write(
            root.join("real/src/AliasEscape.svelte"),
            "<script lang=\"ts\">import value from '@escape/value';</script>\n",
        )
        .expect("path alias escape importer");
        fs::write(
            root.join("real/src/BaseEscape.svelte"),
            "<script lang=\"ts\">import value from 'value';</script>\n",
        )
        .expect("base URL escape importer");
        fs::write(external.path().join("value.ts"), "export default 1;\n")
            .expect("external module");
        fs::write(
            root.join("tsconfig.json"),
            "{ \"compilerOptions\": { \"baseUrl\": \".\", \"paths\": { \"@/*\": [\"src/*\"] } } }\n",
        )
        .expect("TypeScript config");
        fs::write(
            root.join("svelte.config.js"),
            "export default { kit: { alias: { '$shared': 'src/lib' } } };\n",
        )
        .expect("Svelte config");
        symlink(root.join("real/src"), root.join("src")).expect("internal source alias");
        symlink(external.path(), root.join("escaped")).expect("external source alias");
        symlink(external.path(), root.join("outside")).expect("external import alias");
        let inputs = web::discover_project_inputs(root, root, &crate::models::Config::default())
            .expect("project inputs");

        let parsed = web::parse_sources(
            AnalyzerId::Svelte,
            root,
            vec![
                web_source(root, "real/src/App.svelte"),
                web_source(root, "real/src/lib/value.ts"),
            ],
            &inputs,
            &["src".to_owned()],
        )
        .expect("internal symlink aliases resolve");
        let source_escape = web::parse_sources(
            AnalyzerId::Svelte,
            root,
            Vec::new(),
            &inputs,
            &["escaped".to_owned()],
        )
        .expect_err("external source root is rejected");
        fs::write(
            root.join("tsconfig.json"),
            "{ \"compilerOptions\": { \"baseUrl\": \".\", \"paths\": { \"@escape/*\": [\"outside/*\"] } } }\n",
        )
        .expect("escaping path alias config");
        let alias_inputs =
            web::discover_project_inputs(root, root, &crate::models::Config::default())
                .expect("path alias project inputs");
        let alias_escape = web::parse_sources(
            AnalyzerId::Svelte,
            root,
            vec![web_source(root, "real/src/AliasEscape.svelte")],
            &alias_inputs,
            &["src".to_owned()],
        )
        .expect_err("external path alias is rejected");
        fs::write(
            root.join("tsconfig.json"),
            "{ \"compilerOptions\": { \"baseUrl\": \"outside\" } }\n",
        )
        .expect("escaping base URL config");
        let base_inputs =
            web::discover_project_inputs(root, root, &crate::models::Config::default())
                .expect("base URL project inputs");
        let base_url_escape = web::parse_sources(
            AnalyzerId::Svelte,
            root,
            vec![web_source(root, "real/src/BaseEscape.svelte")],
            &base_inputs,
            &["src".to_owned()],
        )
        .expect_err("external base URL is rejected");

        assert_eq!(
            parsed[0]
                .imports
                .iter()
                .map(|fact| (fact.specifier.as_str(), fact.resolved_path.as_deref()))
                .collect::<Vec<_>>(),
            test_case.expected_resolutions,
            "{}",
            test_case.description
        );
        assert_eq!(
            source_escape, test_case.expected_source_escape_error,
            "{}",
            test_case.description
        );
        assert!(
            alias_escape.contains(test_case.expected_alias_escape_error),
            "{}: {alias_escape}",
            test_case.description
        );
        assert!(
            base_url_escape.contains(test_case.expected_base_url_escape_error),
            "{}: {base_url_escape}",
            test_case.description
        );
    }
}

#[test]
fn given_nested_sveltekit_target_when_resolving_then_filesystem_and_reported_paths_stay_separate() {
    let test_cases = [WebProjectPathTestCase {
        description: "nested generated config and aliases retain target-relative POSIX identities",
        expected_repository_path: "apps/site/.svelte-kit/tsconfig.json",
        expected_target_path: ".svelte-kit/tsconfig.json",
        expected_resolutions: &[
            ("$lib/value", Some("src/lib/value.ts")),
            ("$ui/button", Some("src/ui/button.ts")),
            ("@/value", Some("src/value.ts")),
        ],
    }];
    for test_case in &test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        let project_root = repository.path().join("apps/site");
        fs::create_dir_all(project_root.join("src/lib")).expect("library directory");
        fs::create_dir_all(project_root.join("src/ui")).expect("UI directory");
        fs::write(
            project_root.join("tsconfig.json"),
            "{ \"extends\": \"./.svelte-kit/tsconfig.json\", \"compilerOptions\": { \"baseUrl\": \".\", \"paths\": { \"@/*\": [\"src/*\"] } } }\n",
        )
        .expect("nested TypeScript config");
        fs::write(
            project_root.join("svelte.config.js"),
            "export default { kit: { alias: { '$ui': 'src/ui' } } };\n",
        )
        .expect("nested Svelte config");
        fs::write(
            project_root.join("src/App.svelte"),
            "<script lang=\"ts\">import button from '$ui/button'; import value from '@/value'; import lib from '$lib/value';</script>\n",
        )
        .expect("component");
        fs::write(project_root.join("src/ui/button.ts"), "export default 1;\n").expect("UI module");
        fs::write(project_root.join("src/value.ts"), "export default 1;\n")
            .expect("aliased module");
        fs::write(project_root.join("src/lib/value.ts"), "export default 1;\n")
            .expect("library module");
        let config = crate::models::Config {
            analyzer: AnalyzerId::Svelte,
            framework: Some("sveltekit".to_owned()),
            ..crate::models::Config::default()
        };

        let inputs = web::discover_project_inputs(repository.path(), &project_root, &config)
            .expect("nested project inputs");
        let generated = inputs
            .iter()
            .find(|input| !input.present)
            .expect("missing generated input");
        let parsed = web::parse_sources(
            AnalyzerId::Svelte,
            &project_root,
            vec![
                web_source(&project_root, "src/App.svelte"),
                web_source(&project_root, "src/ui/button.ts"),
                web_source(&project_root, "src/value.ts"),
                web_source(&project_root, "src/lib/value.ts"),
            ],
            &inputs,
            &["src".to_owned()],
        )
        .expect("nested aliases resolve");

        assert_eq!(
            generated.repository_path, test_case.expected_repository_path,
            "{}",
            test_case.description
        );
        assert_eq!(
            generated.target_path, test_case.expected_target_path,
            "{}",
            test_case.description
        );
        assert_eq!(
            parsed[0]
                .imports
                .iter()
                .map(|fact| (fact.specifier.as_str(), fact.resolved_path.as_deref()))
                .collect::<Vec<_>>(),
            test_case.expected_resolutions,
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_dynamic_sveltekit_alias_when_resolution_needs_it_then_error_requires_literal_value() {
    let test_cases = [DynamicSvelteAliasTestCase {
        description: "a referenced dynamic alias value fails with literal remediation",
        expected_error_fragments: &[
            "uses a dynamic value required to resolve import \"$ui-kit/button\"",
            "use a literal kit.alias value",
        ],
    }];
    for test_case in &test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        let root = repository.path();
        fs::create_dir_all(root.join("src")).expect("source directory");
        fs::write(
        root.join("svelte.config.ts"),
        "const target = 'src/ui-kit'; export default { kit: { alias: { '$ui-kit': target } } };\n",
    )
    .expect("dynamic Svelte config");
        fs::write(
            root.join("src/App.svelte"),
            "<script>import value from '$ui-kit/button';</script>\n",
        )
        .expect("component");
        let inputs = web::discover_project_inputs(root, root, &crate::models::Config::default())
            .expect("project inputs");

        let error = web::parse_sources(
            AnalyzerId::Svelte,
            root,
            vec![web_source(root, "src/App.svelte")],
            &inputs,
            &["src".to_owned()],
        )
        .expect_err("dynamic alias is required");

        assert!(
            test_case
                .expected_error_fragments
                .iter()
                .all(|fragment| error.contains(fragment)),
            "{}: {error}",
            test_case.description
        );
    }
}

#[test]
fn given_optional_generated_config_when_it_appears_then_project_input_presence_changes() {
    let test_cases = [OptionalGeneratedConfigTestCase {
        description: "generated config appearance changes tracked project input identity",
        expected_missing_present: false,
        expected_generated_present: true,
    }];
    for test_case in &test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        let root = repository.path();
        fs::write(
            root.join("tsconfig.json"),
            "{ \"extends\": \"./.svelte-kit/tsconfig.json\" }\n",
        )
        .expect("fresh SvelteKit tsconfig");
        let config = crate::models::Config {
            analyzer: AnalyzerId::Svelte,
            framework: Some("sveltekit".to_owned()),
            ..crate::models::Config::default()
        };
        let missing =
            web::discover_project_inputs(root, root, &config).expect("missing generated input");
        fs::create_dir_all(root.join(".svelte-kit")).expect("generated directory");
        fs::write(root.join(".svelte-kit/tsconfig.json"), "{}\n").expect("generated config");

        let present =
            web::discover_project_inputs(root, root, &config).expect("present generated input");

        assert_eq!(
            missing.iter().all(|input| input.present),
            test_case.expected_missing_present,
            "{}",
            test_case.description
        );
        assert_eq!(
            present.iter().all(|input| input.present),
            test_case.expected_generated_present,
            "{}",
            test_case.description
        );
        assert_ne!(
            missing
                .iter()
                .find(|input| input.target_path == ".svelte-kit/tsconfig.json")
                .map(|input| input.fingerprint.as_str()),
            present
                .iter()
                .find(|input| input.target_path == ".svelte-kit/tsconfig.json")
                .map(|input| input.fingerprint.as_str()),
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_multiple_source_roots_when_resolving_lib_then_each_importer_uses_its_own_root() {
    let test_cases = [WebImportGraphTestCase {
        description: "$lib resolution remains relative to each importing source root",
        expected_import_count: 1,
        expected_resolutions: &[
            ("first root", Some("apps/one/src/lib/value.ts")),
            ("second root", Some("apps/two/src/lib/value.ts")),
        ],
    }];
    for test_case in &test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        let root = repository.path();
        for source_root in ["apps/one/src", "apps/two/src"] {
            fs::create_dir_all(root.join(source_root).join("lib")).expect("source root");
            fs::write(
                root.join(source_root).join("feature.ts"),
                "import { value } from '$lib/value'; export const result = value;\n",
            )
            .expect("importer");
            fs::write(
                root.join(source_root).join("lib/value.ts"),
                "export const value: number = 1;\n",
            )
            .expect("library module");
        }
        let sources = [
            "apps/one/src/feature.ts",
            "apps/one/src/lib/value.ts",
            "apps/two/src/feature.ts",
            "apps/two/src/lib/value.ts",
        ]
        .iter()
        .map(|path| web_source(root, path))
        .collect();

        let parsed = web::parse_sources(
            AnalyzerId::TypeScript,
            root,
            sources,
            &[],
            &["apps/one/src".to_owned(), "apps/two/src".to_owned()],
        )
        .expect("multi-root TypeScript parse");

        for (index, (_, expected)) in test_case.expected_resolutions.iter().enumerate() {
            let importer = &parsed[index * 2];
            assert_eq!(
                importer.imports.len(),
                test_case.expected_import_count,
                "{}",
                test_case.description
            );
            assert_eq!(
                importer.imports[0].resolved_path.as_deref(),
                *expected,
                "{}",
                test_case.description
            );
        }
    }
}

#[test]
fn given_relative_lib_and_tsconfig_imports_when_parsing_then_graph_resolves_project_support_files()
{
    let test_cases = [WebImportGraphTestCase {
        description: "resolver honors TS candidate and alias precedence without near matches",
        expected_import_count: 12,
        expected_resolutions: &[
            ("./lib/value", Some("src/lib/value.ts")),
            ("./lib/value.js", Some("src/lib/value.ts")),
            ("$lib/value", Some("src/lib/value.ts")),
            ("$lib", Some("src/lib/index.ts")),
            ("$libfoo", None),
            ("@/lib/value", Some("src/lib/value.ts")),
            ("src/lib/value", Some("src/lib/value.ts")),
            ("@near/lib/value", None),
            ("./lib/not-alias", Some("src/lib/not-alias.ts")),
            ("./directory", Some("src/directory/index.cts")),
            ("./esm.mjs", Some("src/esm.mts")),
            ("./common.cjs", Some("src/common.cts")),
        ],
    }];
    for test_case in &test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        let root = repository.path();
        let feature = root.join("src/feature.ts");
        fs::create_dir_all(root.join("src/lib")).expect("source directory");
        fs::write(
            &feature,
            "import { value as relativeValue } from './lib/value';\nimport { value as relativeJs } from './lib/value.js';\nimport { value as libValue } from '$lib/value';\nimport { rootValue } from '$lib';\nimport { invalidLib } from '$libfoo';\nimport { value as aliasValue } from '@/lib/value';\nimport { value as bareValue } from 'src/lib/value';\nimport { missing } from '@near/lib/value';\nimport { wrong } from './lib/not-alias';\nimport { indexed } from './directory';\nimport { esm } from './esm.mjs';\nimport { common } from './common.cjs';\nexport const total: number = relativeValue + relativeJs + libValue + rootValue + aliasValue + bareValue + indexed + esm + common;\n",
        )
        .expect("feature source");
        fs::write(
            root.join("src/lib/value.ts"),
            "export const value: number = 1;\n",
        )
        .expect("support source");
        fs::write(
            root.join("src/lib/index.ts"),
            "export const rootValue: number = 1;\n",
        )
        .expect("$lib index source");
        fs::write(
            root.join("src/lib/foo.ts"),
            "export const invalidLib: number = 1;\n",
        )
        .expect("$lib near-match source");
        fs::write(
            root.join("src/lib/not-alias.ts"),
            "export const wrong: number = 1;\n",
        )
        .expect("relative near-miss source");
        fs::create_dir_all(root.join("src/directory")).expect("index source directory");
        fs::write(
            root.join("src/directory/index.cts"),
            "export const indexed: number = 1;\n",
        )
        .expect("index source");
        fs::write(root.join("src/esm.mts"), "export const esm: number = 1;\n")
            .expect("ES module source");
        fs::write(
            root.join("src/common.cts"),
            "export const common: number = 1;\n",
        )
        .expect("CommonJS source");
        fs::create_dir_all(root.join("src/wrong/lib")).expect("generic alias directory");
        fs::write(
            root.join("src/wrong/lib/value.ts"),
            "export const value: number = 99;\n",
        )
        .expect("generic alias source");
        let sources = vec![
            web_source(root, "src/feature.ts"),
            web_source(root, "src/lib/value.ts"),
            web_source(root, "src/lib/index.ts"),
            web_source(root, "src/lib/foo.ts"),
            web_source(root, "src/lib/not-alias.ts"),
            web_source(root, "src/directory/index.cts"),
            web_source(root, "src/esm.mts"),
            web_source(root, "src/common.cts"),
            web_source(root, "src/wrong/lib/value.ts"),
        ];
        let config = br#"{"compilerOptions":{"baseUrl":".","paths":{"@/*":["src/wrong/*"],"@/lib/*":["src/lib/*"],"./lib/*":["src/wrong/*"]}}}"#;
        fs::write(root.join("jsconfig.json"), config).expect("JavaScript config");
        let inputs = vec![ProjectInput {
            path: root.join("jsconfig.json"),
            extended_configs: Vec::new(),
            repository_path: "jsconfig.json".to_owned(),
            target_path: "jsconfig.json".to_owned(),
            content: config.to_vec(),
            fingerprint: "config-fingerprint".to_owned(),
            present: true,
        }];

        let parsed = web::parse_sources(
            AnalyzerId::TypeScript,
            root,
            sources,
            &inputs,
            &["src".to_owned()],
        )
        .expect("native TypeScript parse");

        assert_eq!(
            parsed[0].imports.len(),
            test_case.expected_import_count,
            "{}",
            test_case.description
        );
        for (specifier, expected) in test_case.expected_resolutions {
            let actual = parsed[0]
                .imports
                .iter()
                .find(|fact| fact.specifier == *specifier)
                .and_then(|fact| fact.resolved_path.as_deref());
            assert_eq!(actual, *expected, "{}: {specifier}", test_case.description);
        }
    }
}

#[test]
fn given_recursive_jsonc_config_when_resolving_then_child_compiler_options_override_parents() {
    let test_cases = [WebConfigInheritanceTestCase {
        description: "recursive JSONC inheritance tracks inputs and applies child options",
        expected_input_count: 3,
        expected_resolutions: &[
            ("@replace/value", Some("src/new/value.ts")),
            ("@base/value", None),
            ("src/new/value", Some("src/new/value.ts")),
        ],
    }];
    for test_case in &test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        let root = repository.path();
        fs::create_dir_all(root.join("src/new")).expect("source directory");
        fs::create_dir_all(root.join("config")).expect("config directory");
        fs::write(
            root.join("src/feature.ts"),
            "import { value as replacement } from '@replace/value';\nimport { value as inherited } from '@base/value';\nimport { value as bare } from 'src/new/value';\nexport const total: number = replacement + bare;\n",
        )
        .expect("feature source");
        fs::write(
            root.join("src/new/value.ts"),
            "export const value: number = 1;\n",
        )
        .expect("resolved source");
        fs::write(
            root.join("tsconfig.json"),
            "{\n // child wins\n \"extends\": \"./config/middle\",\n \"compilerOptions\": {\n  \"baseUrl\": \".\",\n  \"paths\": { \"@replace/*\": [\"src/new/*\"], },\n },\n}\n",
        )
        .expect("root config");
        fs::write(
            root.join("config/middle.json"),
            "{ \"extends\": \"./base\", }\n",
        )
        .expect("middle config");
        fs::write(
            root.join("config/base.json"),
            "{ \"compilerOptions\": { \"baseUrl\": \"../parent\", \"paths\": { \"@base/*\": [\"src/base/*\"] } } }\n",
        )
        .expect("base config");
        let inputs = web::discover_project_inputs(root, root, &crate::models::Config::default())
            .expect("recursive config inputs");
        let sources = vec![
            web_source(root, "src/feature.ts"),
            web_source(root, "src/new/value.ts"),
        ];

        let parsed = web::parse_sources(
            AnalyzerId::TypeScript,
            root,
            sources,
            &inputs,
            &["src".to_owned()],
        )
        .expect("native TypeScript parse");

        assert_eq!(
            inputs.len(),
            test_case.expected_input_count,
            "{}",
            test_case.description
        );
        for (specifier, expected) in test_case.expected_resolutions {
            let actual = parsed[0]
                .imports
                .iter()
                .find(|fact| fact.specifier == *specifier)
                .and_then(|fact| fact.resolved_path.as_deref());
            assert_eq!(actual, *expected, "{}: {specifier}", test_case.description);
        }
    }
}

#[test]
fn given_ordered_extends_array_when_resolving_then_later_bases_precede_child_overrides() {
    let test_cases = [WebConfigInheritanceTestCase {
        description: "TypeScript 5 extends arrays merge bases in order before the child",
        expected_input_count: 3,
        expected_resolutions: &[
            ("@pick/value", Some("two/src/value.ts")),
            ("src/child", Some("src/child.ts")),
        ],
    }];
    for test_case in &test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        let root = repository.path();
        fs::create_dir_all(root.join("config")).expect("config directory");
        fs::create_dir_all(root.join("one/src")).expect("first base directory");
        fs::create_dir_all(root.join("two/src")).expect("second base directory");
        fs::create_dir_all(root.join("src")).expect("child source directory");
        fs::write(
            root.join("tsconfig.json"),
            "{ \"extends\": [\"./config/one\", \"./config/two\"], \"compilerOptions\": { \"baseUrl\": \".\" } }\n",
        )
        .expect("root config");
        fs::write(
            root.join("config/one.json"),
            "{ \"compilerOptions\": { \"baseUrl\": \"../one\", \"paths\": { \"@pick/*\": [\"src/*\"] } } }\n",
        )
        .expect("first base config");
        fs::write(
            root.join("config/two.json"),
            "{ \"compilerOptions\": { \"baseUrl\": \"../two\", \"paths\": { \"@pick/*\": [\"src/*\"] } } }\n",
        )
        .expect("second base config");
        fs::write(
            root.join("src/feature.ts"),
            "import { value } from '@pick/value';\nimport { child } from 'src/child';\nexport const total: number = value + child;\n",
        )
        .expect("feature source");
        fs::write(
            root.join("one/src/value.ts"),
            "export const value: number = 1;\n",
        )
        .expect("first base source");
        fs::write(
            root.join("two/src/value.ts"),
            "export const value: number = 2;\n",
        )
        .expect("second base source");
        fs::write(
            root.join("src/child.ts"),
            "export const child: number = 1;\n",
        )
        .expect("child source");
        let inputs = web::discover_project_inputs(root, root, &crate::models::Config::default())
            .expect("ordered config inputs");
        let sources = vec![
            web_source(root, "src/feature.ts"),
            web_source(root, "one/src/value.ts"),
            web_source(root, "two/src/value.ts"),
            web_source(root, "src/child.ts"),
        ];

        let parsed = web::parse_sources(
            AnalyzerId::TypeScript,
            root,
            sources,
            &inputs,
            &["src".to_owned()],
        )
        .expect("native TypeScript parse");

        assert_eq!(
            inputs.len(),
            test_case.expected_input_count,
            "{}",
            test_case.description
        );
        for (specifier, expected) in test_case.expected_resolutions {
            let actual = parsed[0]
                .imports
                .iter()
                .find(|fact| fact.specifier == *specifier)
                .and_then(|fact| fact.resolved_path.as_deref());
            assert_eq!(actual, *expected, "{}: {specifier}", test_case.description);
        }
    }
}

#[test]
fn given_svelte_target_when_classifying_sources_then_scripts_are_support_only() {
    let test_cases = [
        WebDirectSourceTestCase {
            description: "Svelte components are direct targets",
            path: "src/App.svelte",
            analyzer: AnalyzerId::Svelte,
            expected_discovered: true,
            expected_direct: true,
            expected_source_kind: None,
        },
        WebDirectSourceTestCase {
            description: "TypeScript modules support Svelte project analysis",
            path: "src/lib/value.ts",
            analyzer: AnalyzerId::Svelte,
            expected_discovered: true,
            expected_direct: false,
            expected_source_kind: Some(fensu_typescript::SourceKind::TypeScript),
        },
        WebDirectSourceTestCase {
            description: "ES module TypeScript is a direct TypeScript target",
            path: "src/value.mts",
            analyzer: AnalyzerId::TypeScript,
            expected_discovered: true,
            expected_direct: true,
            expected_source_kind: Some(fensu_typescript::SourceKind::TypeScriptModule),
        },
        WebDirectSourceTestCase {
            description: "CommonJS TypeScript is a direct TypeScript target",
            path: "src/value.cts",
            analyzer: AnalyzerId::TypeScript,
            expected_discovered: true,
            expected_direct: true,
            expected_source_kind: Some(fensu_typescript::SourceKind::TypeScriptCommonJs),
        },
        WebDirectSourceTestCase {
            description: "ES module JavaScript is a direct TypeScript target",
            path: "src/value.mjs",
            analyzer: AnalyzerId::TypeScript,
            expected_discovered: true,
            expected_direct: true,
            expected_source_kind: Some(fensu_typescript::SourceKind::JavaScriptModule),
        },
        WebDirectSourceTestCase {
            description: "CommonJS JavaScript is a direct TypeScript target",
            path: "src/value.cjs",
            analyzer: AnalyzerId::TypeScript,
            expected_discovered: true,
            expected_direct: true,
            expected_source_kind: Some(fensu_typescript::SourceKind::JavaScriptCommonJs),
        },
        WebDirectSourceTestCase {
            description: "ES module declarations are TypeScript support",
            path: "src/value.d.mts",
            analyzer: AnalyzerId::TypeScript,
            expected_discovered: true,
            expected_direct: false,
            expected_source_kind: Some(fensu_typescript::SourceKind::TypeScriptModuleDefinition),
        },
        WebDirectSourceTestCase {
            description: "CommonJS declarations are TypeScript support",
            path: "src/value.d.cts",
            analyzer: AnalyzerId::TypeScript,
            expected_discovered: true,
            expected_direct: false,
            expected_source_kind: Some(fensu_typescript::SourceKind::TypeScriptCommonJsDefinition),
        },
        WebDirectSourceTestCase {
            description: "legacy declarations are TypeScript support",
            path: "src/value.d.ts",
            analyzer: AnalyzerId::TypeScript,
            expected_discovered: true,
            expected_direct: false,
            expected_source_kind: Some(fensu_typescript::SourceKind::TypeScriptDefinition),
        },
        WebDirectSourceTestCase {
            description: "Svelte files are not TypeScript analyzer sources",
            path: "src/App.svelte",
            analyzer: AnalyzerId::TypeScript,
            expected_discovered: false,
            expected_direct: true,
            expected_source_kind: None,
        },
    ];
    for test_case in &test_cases {
        assert_eq!(
            web::is_web_source(std::path::Path::new(test_case.path), test_case.analyzer),
            test_case.expected_discovered,
            "{}",
            test_case.description
        );
        assert_eq!(
            web::is_direct_source(std::path::Path::new(test_case.path), test_case.analyzer),
            test_case.expected_direct,
            "{}",
            test_case.description
        );
        assert_eq!(
            web::source_kind(std::path::Path::new(test_case.path)),
            test_case.expected_source_kind,
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_web_filename_when_classifying_colocated_tests_then_only_test_and_spec_suffixes_match() {
    let test_cases = [
        WebTestSourceTestCase {
            description: "test suffix is recognized",
            path: "src/setup.test.ts",
            expected_test: true,
        },
        WebTestSourceTestCase {
            description: "spec suffix is recognized",
            path: "scripts/setup.spec.js",
            expected_test: true,
        },
        WebTestSourceTestCase {
            description: "arbitrary runtime setup module is not a test",
            path: "src/setup.ts",
            expected_test: false,
        },
        WebTestSourceTestCase {
            description: "setupTests near miss is not a test",
            path: "src/setupTests.ts",
            expected_test: false,
        },
        WebTestSourceTestCase {
            description: "declaration near miss is not a test",
            path: "src/setup.test.d.ts",
            expected_test: false,
        },
    ];
    for test_case in test_cases {
        assert_eq!(
            web::is_web_test_source(std::path::Path::new(test_case.path)),
            test_case.expected_test,
            "{}",
            test_case.description
        );
    }
}
