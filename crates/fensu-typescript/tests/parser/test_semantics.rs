//! RaceWatch-compatible owned semantic fact tests.

use fensu_typescript::{parse_typescript, ModelKind};

use crate::test_types;

#[test]
fn given_annotation_matrix_when_collecting_locals_then_preserves_expected_fwa003_semantics() {
    let test_cases = [test_types::LocalMatrixTestCase {
        description: "scalar and explicit contract forms pass while four inferred values fail",
        source: concat!(
            "interface Options { readonly enabled: boolean; }\n",
            "declare function buildValue(): string;\n",
            "declare function typedValue<T>(): T;\n",
            "export function run(): void {\n",
            "  const scalar = 1;\n",
            "  const signed = -1;\n",
            "  const label = `value ${scalar}`;\n",
            "  const explicit: string = buildValue();\n",
            "  const checked = { enabled: true } satisfies Options;\n",
            "  const generic = typedValue<string>();\n",
            "  const constructed = new Map<string, string>();\n",
            "  const inferred = buildValue();\n",
            "  const asserted = buildValue() as string;\n",
            "  const nullable = null;\n",
            "  const missing = undefined;\n",
            "  const { enabled } = checked;\n",
            "  for (const item of [1]) void item;\n",
            "  try { throw new Error(); } catch (error) { void error; }\n",
            "}\n",
        ),
        expected_failures: &[
            ("inferred", 12, 8),
            ("asserted", 13, 8),
            ("nullable", 14, 8),
            ("missing", 15, 8),
        ],
        expected_binding_count: 11,
    }];

    for test_case in &test_cases {
        let facts = parse_typescript(test_case.source.as_bytes()).expect("must parse");
        let failures: Vec<(&str, usize, usize)> = facts
            .local_bindings
            .iter()
            .filter(|binding| binding.requires_explicit_type())
            .map(|binding| {
                (
                    binding.name.as_str(),
                    binding.span.line,
                    binding.span.column,
                )
            })
            .collect();

        assert_eq!(
            failures, test_case.expected_failures,
            "{}",
            test_case.description
        );
        assert_eq!(
            facts.local_bindings.len(),
            test_case.expected_binding_count,
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_variable_function_when_collecting_then_does_not_leak_statement_context_into_loop() {
    let test_cases = [test_types::LocalMatrixTestCase {
        description: "a for binding inside a variable function remains outside FWA003 candidates",
        source: concat!(
            "declare function buildValue(): string;\n",
            "export const wrapped = (): void => {\n",
            "  for (const ignored of [1]) void ignored;\n",
            "  const nested = buildValue();\n",
            "};\n",
        ),
        expected_failures: &[("nested", 4, 8)],
        expected_binding_count: 1,
    }];

    for test_case in &test_cases {
        let facts = parse_typescript(test_case.source.as_bytes()).expect("must parse");
        let failures: Vec<(&str, usize, usize)> = facts
            .local_bindings
            .iter()
            .filter(|binding| binding.requires_explicit_type())
            .map(|binding| {
                (
                    binding.name.as_str(),
                    binding.span.line,
                    binding.span.column,
                )
            })
            .collect();

        assert_eq!(
            failures, test_case.expected_failures,
            "{}",
            test_case.description
        );
        assert_eq!(
            facts.local_bindings.len(),
            test_case.expected_binding_count,
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_model_declarations_when_collecting_then_matches_expected_immutable_semantics() {
    let test_cases = [test_types::ModelMatrixTestCase {
        description: "readonly properties reject mutable arrays and collection references",
        source: concat!(
            "export interface Immutable { readonly values: readonly string[]; }\n",
            "export interface MutableProperty { values: readonly string[]; }\n",
            "export interface MutableArray { readonly values: string[]; }\n",
            "export interface MutableCollection { readonly values: Map<string, string>; }\n",
            "export interface ReadonlyCollection { readonly values: ReadonlyMap<string, string>; }\n",
            "export type ImmutableAlias = { readonly value: string };\n",
            "export type PrimitiveAlias = string;\n",
        ),
        expected_models: &[
            ("Immutable", ModelKind::Interface, true),
            ("MutableProperty", ModelKind::Interface, false),
            ("MutableArray", ModelKind::Interface, false),
            ("MutableCollection", ModelKind::Interface, false),
            ("ReadonlyCollection", ModelKind::Interface, true),
            ("ImmutableAlias", ModelKind::TypeLiteralAlias, true),
        ],
    }];

    for test_case in &test_cases {
        let facts = parse_typescript(test_case.source.as_bytes()).expect("must parse");
        let models: Vec<(&str, ModelKind, bool)> = facts
            .models
            .iter()
            .map(|model| (model.name.as_str(), model.kind, model.readonly_shape))
            .collect();

        assert_eq!(
            models, test_case.expected_models,
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_runtime_classes_when_collecting_then_keeps_expected_top_level_export_intent() {
    let test_cases = [test_types::ClassMatrixTestCase {
        description: "ambient and nested classes are absent from top-level runtime class facts",
        source: concat!(
            "declare class Ambient {}\n",
            "class Internal {}\n",
            "export class PublicClass {}\n",
            "export default class DefaultClass {}\n",
            "function build(): void { class Nested {} void Nested; }\n",
        ),
        expected_classes: &[
            ("Internal", false, 2),
            ("PublicClass", true, 3),
            ("DefaultClass", true, 4),
        ],
    }];

    for test_case in &test_cases {
        let facts = parse_typescript(test_case.source.as_bytes()).expect("must parse");
        let classes: Vec<(&str, bool, usize)> = facts
            .classes
            .iter()
            .map(|class| (class.name.as_str(), class.exported, class.span.line))
            .collect();

        assert_eq!(
            classes, test_case.expected_classes,
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_policy_owned_top_level_declarations_when_collecting_then_retains_only_compact_facts() {
    let test_cases = [test_types::PolicyFactsTestCase {
        description: "policy facts retain declarations, exports, calls, and error ancestry",
        source: concat!(
            "export function run(): void {}\n",
            "export const value: number = 1;\n",
            "export class DomainError extends Error {}\n",
            "export enum State { Ready }\n",
            "export { external } from './external';\n",
            "export * from './all';\n",
            "initialize();\n",
        ),
        expected_public_exports: 6,
        expected_runtime_declarations: 4,
        expected_top_level_functions: 1,
        expected_re_exports: 2,
        expected_top_level_calls: 1,
        expected_call_name: "initialize",
        expected_error_class: true,
    }];
    for test_case in test_cases {
        let facts = parse_typescript(test_case.source.as_bytes()).expect("must parse");

        assert_eq!(
            facts.public_export_count, test_case.expected_public_exports,
            "{}",
            test_case.description
        );
        assert_eq!(
            facts.runtime_declaration_count, test_case.expected_runtime_declarations,
            "{}",
            test_case.description
        );
        assert_eq!(
            facts.top_level_function_count, test_case.expected_top_level_functions,
            "{}",
            test_case.description
        );
        assert_eq!(
            facts.re_exports.len(),
            test_case.expected_re_exports,
            "{}",
            test_case.description
        );
        assert_eq!(
            facts.top_level_calls.len(),
            test_case.expected_top_level_calls,
            "{}",
            test_case.description
        );
        assert_eq!(
            facts.top_level_calls[0].initializer_call.as_deref(),
            Some(test_case.expected_call_name),
            "{}",
            test_case.description
        );
        assert_eq!(
            facts.classes[0].error_class, test_case.expected_error_class,
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_import_matrix_when_collecting_then_counts_expected_bindings_and_kinds() {
    let test_cases = [test_types::ImportMatrixTestCase {
        description:
            "side-effect, default, namespace, named, combined, and type imports stay distinct",
        source: concat!(
            "import 'side-effect';\n",
            "import defaultName from 'default';\n",
            "import * as namespace from 'namespace';\n",
            "import { first, second as local } from 'named';\n",
            "import combined, { third } from 'combined';\n",
            "import type { Contract, Other as Alias } from 'types';\n",
            "import { type MixedType, runtime } from 'mixed';\n",
        ),
        expected_binding_count: 10,
        expected_imports: &[
            ("side-effect", 0, false, false),
            ("default", 1, false, false),
            ("namespace", 1, false, true),
            ("named", 2, false, false),
            ("combined", 2, false, false),
            ("types", 2, true, false),
            ("mixed", 2, false, false),
        ],
    }];

    for test_case in &test_cases {
        let facts = parse_typescript(test_case.source.as_bytes()).expect("must parse");
        let imports: Vec<(&str, usize, bool, bool)> = facts
            .imports
            .iter()
            .map(|imported| {
                (
                    imported.specifier.as_str(),
                    imported.binding_count,
                    imported.type_only,
                    imported.namespace,
                )
            })
            .collect();

        assert_eq!(
            facts.imported_binding_count, test_case.expected_binding_count,
            "{}",
            test_case.description
        );
        assert_eq!(
            imports, test_case.expected_imports,
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_functions_when_collecting_then_owns_expected_names_contracts_and_spans() {
    let test_cases = [test_types::FunctionMatrixTestCase {
        description:
            "declarations and variable functions retain names, exports, and type contracts",
        source: concat!(
            "export function run(value: string): boolean { return value.length > 0; }\n",
            "export const read = (value: number): string => String(value);\n",
            "const internal = function (value: unknown): void { void value; };\n",
        ),
        expected_functions: &[
            ("run", true, 1, true, Some("boolean"), 1, 0, 0),
            ("read", true, 1, true, Some("string"), 0, 1, 0),
            ("internal", false, 1, true, Some("void"), 1, 0, 0),
        ],
    }];

    for test_case in &test_cases {
        let facts = parse_typescript(test_case.source.as_bytes()).expect("must parse");
        let functions: Vec<test_types::FunctionExpectation<'_>> = facts
            .functions
            .iter()
            .map(|function| {
                (
                    function.name.as_str(),
                    function.exported,
                    function.parameter_count,
                    function.parameters_annotated,
                    function.return_type.as_deref(),
                    function.statement_count,
                    function.distinct_call_count,
                    function.local_count,
                )
            })
            .collect();

        assert_eq!(
            functions, test_case.expected_functions,
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_nested_functions_when_collecting_then_metrics_exclude_nested_bodies() {
    let test_cases = [test_types::FunctionMatrixTestCase {
        description:
            "parent metrics count its declarations and calls but not nested function bodies",
        source: concat!(
            "interface Context { readonly id: string; }\n",
            "declare function build(): string;\n",
            "export function outer(this: Context, value: string, ...rest: number[]): void {\n",
            "  const local = build();\n",
            "  helper();\n",
            "  nested.owner();\n",
            "  function nested(): void { const inner = build(); ignored(); }\n",
            "  const arrow = (): void => { const arrowLocal = build(); arrowCall(); };\n",
            "  void [value, rest, local, arrow];\n",
            "}\n",
        ),
        expected_functions: &[
            ("outer", true, 3, true, Some("void"), 5, 3, 2),
            ("nested", false, 0, true, Some("void"), 2, 2, 1),
            ("arrow", false, 0, true, Some("void"), 2, 2, 1),
        ],
    }];

    for test_case in &test_cases {
        let facts = parse_typescript(test_case.source.as_bytes()).expect("must parse");
        let functions: Vec<test_types::FunctionExpectation<'_>> = facts
            .functions
            .iter()
            .map(|function| {
                (
                    function.name.as_str(),
                    function.exported,
                    function.parameter_count,
                    function.parameters_annotated,
                    function.return_type.as_deref(),
                    function.statement_count,
                    function.distinct_call_count,
                    function.local_count,
                )
            })
            .collect();

        assert_eq!(
            functions, test_case.expected_functions,
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_parameterized_tests_when_collecting_then_facts_follow_syntax_nodes() {
    let test_cases = [
        test_types::ParameterizedTestFactTestCase {
            description: "syntax nodes distinguish a real typed table from marker text and delimiters",
            source: concat!(
                "interface Case { readonly description: string; readonly expectedValue: string; }\n",
                "const text = \"test.each<Case>([])('fake', () => {})\";\n",
                "test.each<Case>([{ description: 'comma, bracket ]', expectedValue: 'x' }])",
                "('$description', (testCase) => expect(testCase.expectedValue).toBe('x'));\n",
            ),
            expected_count: 1,
            expected_callback_name: "testCase",
            expected_valid_contract: true,
        },
        test_types::ParameterizedTestFactTestCase {
            description: "nested function behavior does not contribute callback metrics",
            source: concat!(
                "interface Case { readonly description: string; readonly expectedValue: string; }\n",
                "test.each<Case>([{ description: 'case', expectedValue: 'x' }])",
                "('$description', (testCase) => {\n",
                "  expect(testCase.expectedValue).toBe('x');\n",
                "  const nested = (): void => { if (testCase.expectedValue) { testCase.expectedValue = 'y'; } };\n",
                "  void nested;\n",
                "});\n",
            ),
            expected_count: 1,
            expected_callback_name: "testCase",
            expected_valid_contract: true,
        },
    ];
    for test_case in &test_cases {
        let facts =
            parse_typescript(test_case.source.as_bytes()).expect("parameterized test source");
        assert_eq!(
            facts.parameterized_tests.len(),
            test_case.expected_count,
            "{}",
            test_case.description
        );
        let test = &facts.parameterized_tests[0];
        for actual in [
            test.typed,
            test.local_case_type,
            test.local_readonly_case_type,
            test.has_description,
            test.has_expected,
            test.inline_cases,
            test.nonempty_cases,
            test.object_cases,
            test.title_uses_description,
            test.has_expectation,
            test.uses_expected,
        ] {
            assert_eq!(
                actual, test_case.expected_valid_contract,
                "{}",
                test_case.description
            );
        }
        assert_eq!(
            test.callback_name.as_deref(),
            Some(test_case.expected_callback_name),
            "{}",
            test_case.description
        );
        assert_eq!(
            test.has_branch, !test_case.expected_valid_contract,
            "{}",
            test_case.description
        );
        assert_eq!(
            test.mutates_case, !test_case.expected_valid_contract,
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_contract_syntax_when_collecting_then_json_and_public_any_facts_are_owned() {
    let test_cases = [test_types::ContractFactsTestCase {
        description: "JSON result flows and whitespace test calls remain independent syntax facts",
        source: concat!(
            "interface Props { value:\n any; }\n",
            "export async function run(firstResponse: Response, secondResponse: Response): Promise<Data> {\n",
            "  const first = await firstResponse.json (\n );\n",
            "  const firstAlias = first;\n",
            "  FirstSchema.safeParse(firstAlias);\n",
            "  const second = await secondResponse.json\n( );\n",
            "  Date.parse(second);\n",
            "  const asserted = second as Data;\n",
            "  return asserted;\n",
            "}\n",
            "declare const deferredResponse: Response;\n",
            "const deferred = (): Promise<unknown> => deferredResponse.json();\n",
            "DeferredSchema.parse(deferred);\n",
            "const text = \"test('bad name', () => {})\";\n",
            "// it('also bad', () => {});\n",
            "test\n( 'given input when read then returns output', () => {});\n",
            "it \n ( 'bad name', () => {});\n",
        ),
        expected_json_states: &[(false, true), (true, false), (false, false)],
        expected_test_names: &["given input when read then returns output", "bad name"],
        expected_public_any: 1,
    }];
    for test_case in &test_cases {
        let facts = parse_typescript(test_case.source.as_bytes()).expect("contract source");

        let json_states = facts
            .json_calls
            .iter()
            .map(|call| (call.asserted, call.schema_decoded))
            .collect::<Vec<_>>();
        let test_names = facts
            .test_calls
            .iter()
            .map(|call| call.name.as_str())
            .collect::<Vec<_>>();

        assert_eq!(
            json_states, test_case.expected_json_states,
            "{}",
            test_case.description
        );
        assert_eq!(
            test_names, test_case.expected_test_names,
            "{}",
            test_case.description
        );
        assert_eq!(
            facts.public_any.len(),
            test_case.expected_public_any,
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_class_and_object_methods_when_collecting_then_preserves_method_names() {
    let test_cases = [test_types::FunctionNameTestCase {
        description:
            "method names survive while nested declarations and arrow naming stay distinct",
        source: concat!(
            "class Service {\n",
            "  run(): void {\n",
            "    function nested(): void {}\n",
            "    const nestedArrow = (): void => {};\n",
            "  }\n",
            "}\n",
            "const handlers = {\n",
            "  load(): void {},\n",
            "  arrow: (): void => {},\n",
            "  nested: { save(): void {} },\n",
            "};\n",
        ),
        expected_names: &[
            "run",
            "nested",
            "nestedArrow",
            "load",
            "<anonymous>",
            "save",
        ],
    }];

    for test_case in &test_cases {
        let facts = parse_typescript(test_case.source.as_bytes()).expect("must parse");
        let names: Vec<&str> = facts
            .functions
            .iter()
            .map(|function| function.name.as_str())
            .collect();

        assert_eq!(names, test_case.expected_names, "{}", test_case.description);
    }
}

#[test]
fn given_destructured_top_level_binding_when_collecting_then_inspects_initializer_call() {
    let test_cases = [test_types::TopLevelBindingTestCase {
        description: "initializer calls are independent of whether the binding is an identifier",
        source: concat!(
            "declare function source(): { value: string };\n",
            "const { value } = source();\n",
            "const plain = source();\n",
        ),
        expected_bindings: &[("{ value }", Some("source")), ("plain", Some("source"))],
    }];

    for test_case in &test_cases {
        let facts = parse_typescript(test_case.source.as_bytes()).expect("must parse");
        let bindings: Vec<(&str, Option<&str>)> = facts
            .top_level_bindings
            .iter()
            .map(|binding| (binding.name.as_str(), binding.initializer_call.as_deref()))
            .collect();

        assert_eq!(
            bindings, test_case.expected_bindings,
            "{}",
            test_case.description
        );
    }
}
