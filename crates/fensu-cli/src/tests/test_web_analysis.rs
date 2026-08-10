use std::fs;

use crate::analyzer::AnalyzerId;
use crate::check::_helpers::project as web;
use crate::models::ProjectInput;
use crate::tests::helpers::web_source;
use crate::tests::test_types::WebConfigInheritanceTestCase;
use crate::tests::test_types::{WebDirectSourceTestCase, WebImportGraphTestCase};

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
        let inputs = web::discover_project_inputs(root, root).expect("recursive config inputs");
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
        let inputs = web::discover_project_inputs(root, root).expect("ordered config inputs");
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
