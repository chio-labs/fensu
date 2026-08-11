struct WebRuleFixture {
    code: &'static str,
    failing: &'static [(&'static str, &'static str)],
    passing: &'static [(&'static str, &'static str)],
    near_miss: &'static [(&'static str, &'static str)],
    threshold: Option<(&'static str, u32)>,
}

#[test]
fn given_web_symbol_exception_when_checking_then_only_the_owned_function_is_suppressed() {
    let repository = tempfile::tempdir().expect("temporary repository");
    write(
        repository.path().join("fensu.toml"),
        "[targets.web]\nanalyzer = \"typescript\"\nrule_packs = [\"typescript\", \"sveltekit\"]\nroots = [\"src\"]\ntests = []\ntooling = []\nselect = [\"FPTSA003\"]\n[targets.web.cache]\nenabled = false\n[[targets.web.rule_exceptions]]\nrule = \"FPTSA003\"\npath = \"src/run.ts\"\nsymbols = [\"exempt\"]\nreason = \"External callback body.\"\n",
    );
    write(
        repository.path().join("src/run.ts"),
        "declare function build(): object;\nexport function exempt(): void { const first = build(); void first; }\nexport function retained(): void { const second = build(); void second; }\n",
    );
    let process_directory = poison_processes(repository.path());

    let output =
        run_internal_web_check_with(repository.path(), &["--no-cache"], &process_directory);
    let stdout = String::from_utf8_lossy(&output.stdout);

    assert_eq!(output.status.code(), Some(1));
    assert!(!stdout.contains("local variable 'first'"));
    assert!(stdout.contains("local variable 'second'"));
}

#[test]
fn given_effect_beyond_legacy_lifecycle_probe_when_checking_then_nested_effect_is_not_reported() {
    let test_cases = [WebPolicyCheckTestCase {
        description: "legacy lifecycle probe inspects at most one thousand characters",
        expected_exit_code: 0,
    }];
    for test_case in &test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        write(
            repository.path().join("fensu.toml"),
            "[targets.web]\nanalyzer = \"svelte\"\nrule_packs = [\"typescript\", \"sveltekit\"]\nroots = [\"src\"]\ntests = []\ntooling = []\nselect = [\"FPSKV107\"]\n[targets.web.cache]\nenabled = false\n",
        );
        let source = format!(
            "<script lang=\"ts\">import {{ onMount }} from 'svelte'; onMount(() => {{ const padding = '{}'; $effect(() => {{}}); }});</script>\n",
            "x".repeat(1_001)
        );
        write(repository.path().join("src/App.svelte"), &source);
        let process_directory = poison_processes(repository.path());

        let output =
            run_internal_web_check_with(repository.path(), &["--no-cache"], &process_directory);

        assert_eq!(
            output.status.code(),
            Some(test_case.expected_exit_code),
            "{}: {}",
            test_case.description,
            String::from_utf8_lossy(&output.stdout)
        );
    }
}

#[test]
fn given_every_retained_web_rule_when_checking_exact_fixtures_then_fail_pass_and_near_miss_are_distinct(
) {
    let test_cases = web_rule_fixtures();
    assert_eq!(test_cases.len(), 88);
    for test_case in test_cases {
        let failing = run_web_rule_fixture(&test_case, test_case.failing);
        let stdout = String::from_utf8_lossy(&failing.stdout);
        assert_eq!(failing.status.code(), Some(1), "{} failing", test_case.code);
        assert!(
            stdout.starts_with(&format!("{}  ", test_case.code)),
            "{} failing: {}",
            test_case.code,
            stdout
        );
        assert_eq!(
            stdout.matches(&format!("{}  ", test_case.code)).count(),
            1,
            "{}: {stdout}",
            test_case.code
        );
        assert_eq!(
            stdout.matches(" --> ").count(),
            1,
            "{}: {stdout}",
            test_case.code
        );
        assert!(stdout.ends_with("Found 1 fault\n"), "{}: {stdout}", test_case.code);
        assert!(failing.stderr.is_empty(), "{}: {}", test_case.code, String::from_utf8_lossy(&failing.stderr));
        for (label, files) in [
            ("passing", test_case.passing),
            ("near-miss", test_case.near_miss),
        ] {
            let output = run_web_rule_fixture(&test_case, files);
            assert_eq!(
                output.status.code(),
                Some(0),
                "{} {label}: {} {}",
                test_case.code,
                String::from_utf8_lossy(&output.stdout),
                String::from_utf8_lossy(&output.stderr)
            );
        }
    }
}

fn run_web_rule_fixture(
    test_case: &WebRuleFixture,
    files: &[(&str, &str)],
) -> std::process::Output {
    let repository = tempfile::tempdir().expect("temporary repository");
    let threshold = test_case.threshold.map_or_else(String::new, |(name, value)| {
        format!("[targets.web.thresholds]\n{name} = {value}\n")
    });
    write(
        repository.path().join("fensu.toml"),
        &format!(
            "[targets.web]\nanalyzer = \"{}\"\nrule_packs = [\"typescript\", \"sveltekit\"]\nroots = [\"src\"]\ntests = [\"tests\"]\ntooling = [\"tooling\"]\nselect = [\"{}\"]\n{}{}[targets.web.cache]\nenabled = false\n{threshold}",
            if files.iter().any(|(path, _)| path.ends_with(".svelte")) || svelte_rule(test_case.code) { "svelte" } else { "typescript" },
            test_case.code,
            if test_case.code.starts_with("FPSKU") { "ui_kit = \"src/ui-kit\"\n" } else { "" },
            if test_case.code == "FPSKC201" { "openapi = \"openapi.json\"\n" } else if test_case.code == "FPSKU001" { "shadcn = \"components.json\"\n" } else { "" }
        ),
    );
    for (path, source) in files {
        write(repository.path().join(path), source);
    }
    if !files.iter().any(|(path, _)| path.starts_with("src/")) {
        write(repository.path().join("src/anchor.ts"), VALUE);
    }
    let process_directory = poison_processes(repository.path());
    run_internal_web_check_with(repository.path(), &["--no-cache"], &process_directory)
}

fn sveltekit_rule(code: &str) -> bool {
    matches!(
        code,
        "FPSKS103"
            | "FPSKA101"
            | "FPSKA102"
            | "FPSKA103"
            | "FPSKL104"
            | "FPSKL106"
            | "FPSKL107"
            | "FPSKU001"
            | "FPSKU002"
            | "FPSKU003"
            | "FPSKC201"
    )
}

fn svelte_rule(code: &str) -> bool {
    sveltekit_rule(code)
        || matches!(
            code,
            "FPSKR404"
            | "FPSKR405"
            | "FPSKS101"
            | "FPSKS102"
            | "FPSKS104"
            | "FPSKS107"
            | "FPSKS108"
            | "FPSKS109"
            | "FPSKV101"
            | "FPSKV102"
            | "FPSKV103"
            | "FPSKV104"
            | "FPSKV105"
            | "FPSKV106"
            | "FPSKV107"
            | "FPSKV201"
            | "FPSKV202"
        )
}

fn web_rule_fixtures() -> Vec<WebRuleFixture> {
    vec![
        fixture("FPTSP001", &[("src/bad.ts", "export const value: = 1;\n")], &[("src/good.ts", "export const value: number = 1;\n")], &[("src/near.ts", "export const value = 'type: value';\n")]),
        fixture("FPTSR001", &[("src/lib/orders/types.mjs", "export const value = 1;\n")], &[("src/lib/orders/types.mjs", "export {};\n")], &[("src/lib/orders/type.mjs", "export const value = 1;\n")]),
        fixture("FPTSR002", &[("src/lib/orders/constants.cjs", "function value() { return 1; }\n")], &[("src/lib/orders/constants.cjs", "const VALUE = 1;\n")], &[("src/lib/orders/constant.cjs", "function value() { return 1; }\n")]),
        fixture("FPTSR003", &[("src/lib/orders/errors.js", "export class Order extends Object {}\n")], &[("src/lib/orders/errors.js", "export class OrderError extends Error {}\n")], &[("src/lib/orders/error.js", "export class Order extends Object {}\n")]),
        fixture("FPTSR201", &[("src/lib/orders/_helpers/helpers.mjs", "export const value = 1;\n")], &[("src/lib/orders/_helpers/calculate-order.mjs", "export const value = 1;\n")], &[("src/lib/orders/_helpers/helper.mjs", "export const value = 1;\n")]),
        fixture("FPTSR204", &[("src/lib/common/main/run.ts", "export function run(): void {}\n")], &[("src/lib/orders/main/run.ts", "export function run(): void {}\n")], &[("src/lib/commonality/main/run.ts", "export function run(): void {}\n")]),
        role_fixture("FPTSR301", &[("src/lib/orders/main/one.ts", ENTRY), ("src/lib/orders/main/two.ts", ENTRY)], &[("src/lib/orders/main/one.ts", ENTRY)], &[("src/lib/orders/main/group/one.ts", ENTRY)], Some(("max_main_container_modules", 1))),
        fixture("FPTSR304", &[("src/lib/orders/loose.js", "export const value = 1;\n")], &[("src/lib/orders/models.mjs", "export {};\n")], &[("src/loose.cjs", "const value = 1;\n")]),
        role_fixture("FPTSR306", &[("src/lib/orders/main/run.ts", ENTRY), ("src/lib/orders/history/main/run.ts", ENTRY)], &[("src/lib/orders/main/run.ts", ENTRY), ("src/lib/orders/types.ts", "export type Value = string;\n")], &[("src/lib/orders/history/main/run.ts", ENTRY)], None),
        fixture("FPTSR309", &[("src/lib/orders/types.ts", "export type Value = string;\n")], &[("src/lib/orders/main/run.ts", ENTRY)], &[("src/lib/Counter.svelte", "<p>counter</p>\n")]),
        fixture("FPTSR310", &[("src/lib/orders/helpers/value.ts", "export const value = 1;\n")], &[("src/lib/orders/_helpers/value.ts", "export const value = 1;\n")], &[("src/lib/orders/helper/value.ts", "export const value = 1;\n")]),
        role_fixture("FPTSR311", &[("src/lib/orders/main/run.ts", ENTRY), ("src/lib/orders/types.ts", "")], &[("src/lib/orders/main/run.ts", ENTRY), ("src/lib/orders/_helpers/load.ts", ENTRY)], &[("src/lib/orders/main/run.ts", ENTRY), ("src/lib/orders/models.ts", "export interface Order { readonly id: string; }\n")], None),
        fixture("FPTSR401", &[("src/lib/orders/main/run.ts", "export function one(): void {}\nexport function two(): void {}\n")], &[("src/lib/orders/main/run.ts", ENTRY)], &[("src/lib/orders/main/run.ts", "function helper(): void {}\nexport function run(): void { helper(); }\n")]),
        fixture("FPTSR403", &[("src/lib/orders/main/index.ts", "export { value } from '../value';\n")], &[("src/lib/orders/main/index.ts", "export const value = 1;\n")], &[("src/lib/orders/main/index.ts", "import { value } from '../value'; export const result = value;\n")]),
        fixture("FPSKR404", &[("src/lib/orders/_state/order.ts", ENTRY)], &[("src/lib/orders/_state/order.state.svelte.ts", ENTRY)], &[("src/lib/orders/stateful/order.ts", ENTRY)]),
        fixture("FPSKR405", &[("src/lib/orders/_resources/order.ts", ENTRY)], &[("src/lib/orders/_resources/order.resource.ts", ENTRY)], &[("src/lib/orders/resourceful/order.ts", ENTRY)]),
        fixture("FPTSR501", &[("src/lib/orders/classes/wrong.ts", "export class OrderService {}\n")], &[("src/lib/orders/classes/order-service.ts", "export class OrderService {}\n")], &[("src/lib/orders/errors.ts", "export class OneError extends Error {} export class TwoError extends Error {}\n")]),
        import_fixture("FPTSL101", &[("src/lib/orders/_helpers/value.ts", VALUE), ("src/lib/payments/main/use.ts", "import { value } from '../../orders/_helpers/value'; export const used = value;\n")], &[("src/lib/orders/_helpers/value.ts", VALUE), ("src/lib/orders/main/use.ts", "import { value } from '../_helpers/value'; export const used = value;\n")], &[("src/lib/orders/_helper/value.ts", VALUE), ("src/lib/payments/main/use.ts", "import { value } from '../../orders/_helper/value'; export const used = value;\n")]),
        import_fixture("FPTSL102", &[("src/directory/index.mjs", VALUE), ("src/use.ts", "import { value } from './directory'; export const used = value;\n")], &[("src/directory/index.mjs", VALUE), ("src/use.ts", "import { value } from './directory/index.mjs'; export const used = value;\n")], &[("src/use.ts", "import { value } from './missing'; export const used = value;\n")]),
        import_fixture("FPTSL103", &[("src/value.ts", VALUE), ("src/use.ts", "import * as values from './value'; export const used = values.value;\n")], &[("src/value.ts", VALUE), ("src/use.ts", "import { value } from './value'; export const used = value;\n")], &[("src/use.ts", "import * as values from 'external'; export const used = values.value;\n")]),
        import_fixture("FPTSL105", &[("tests/value.ts", VALUE), ("src/use.ts", "import { value } from '../tests/value'; export const used = value;\n")], &[("src/value.ts", VALUE), ("tests/use.ts", "import { value } from '../src/value'; test('given value when used then works', () => expect(value).toBe(1));\n")], &[("src/use.ts", "import { value } from 'tests'; export const used = value;\n")]),
        import_fixture("FPTSL108", &[("src/lib/orders/main/_read.ts", ENTRY), ("src/lib/payments/main/use.ts", "import { run } from '../../orders/main/_read'; export const used = run;\n")], &[("src/lib/orders/main/_read.ts", ENTRY), ("src/lib/orders/_helpers/use.ts", "import { run } from '../main/_read'; export const used = run;\n")], &[("src/lib/orders/main/read.ts", ENTRY), ("src/lib/payments/main/use.ts", "import { run } from '../../orders/main/read'; export const used = run;\n")]),
        import_fixture("FPTSL109", &[("src/lib/orders/main/read.ts", ENTRY)], &[("src/lib/orders/main/read.ts", ENTRY), ("src/lib/payments/_helpers/use.ts", "import { run } from '../../orders/main/read'; export const used = run;\n")], &[("src/lib/orders/main/_read.ts", ENTRY)]),
        import_fixture("FPTSL201", &[("src/one.ts", "import { two } from './two'; export const one = two;\n"), ("src/two.ts", "import { one } from './one'; export const two = one;\n")], &[("src/one.ts", "import { two } from './two'; export const one = two;\n"), ("src/two.ts", VALUE)], &[("src/one.ts", "import { two } from './missing'; export const one = two;\n")]),
        shape_fixture("FPTSS001", "max_statements", &[("src/lib/orders/main/run.ts", TWO_STATEMENTS)], &[("src/lib/orders/main/run.ts", ONE_STATEMENT)], &[("src/lib/orders/_helpers/run.ts", TWO_STATEMENTS)]),
        shape_fixture("FPTSS002", "max_distinct_calls", &[("src/lib/orders/main/run.ts", TWO_CALLS)], &[("src/lib/orders/main/run.ts", ONE_CALL)], &[("src/lib/orders/main/run.ts", "declare function call(): void; export function run(): void { call(); call(); }\n")]),
        shape_fixture("FPTSS003", "max_locals", &[("src/lib/orders/main/run.ts", TWO_LOCALS)], &[("src/lib/orders/main/run.ts", ONE_LOCAL)], &[("src/lib/orders/main/run.ts", "export function run(first: string, second: string): void { void first; void second; }\n")]),
        shape_fixture("FPTSS010", "max_arguments", &[("src/run.ts", TWO_ARGUMENTS)], &[("src/run.ts", ONE_ARGUMENT)], &[("src/run.ts", "export function run({ first, second }: { first: string; second: string }): void { void first; void second; }\n")]),
        shape_fixture("FPTSS011", "max_statements_global", &[("src/run.ts", TWO_STATEMENTS)], &[("src/run.ts", ONE_STATEMENT)], &[("src/run.ts", "export function run(): void { /* call(); call(); */ }\n")]),
        shape_fixture("FPTSS105", "max_imported_bindings", &[("src/use.ts", "import { one, two } from './value'; export const used = one + two;\n"), ("src/value.ts", "export const one = 1; export const two = 2;\n")], &[("src/use.ts", "import { one } from './value'; export const used = one;\n"), ("src/value.ts", VALUE)], &[("src/use.ts", "import './value'; export const used = 1;\n"), ("src/value.ts", VALUE)]),
        shape_fixture("FPTSS106", "max_public_exports", &[("src/value.ts", "export const one = 1; export const two = 2;\n")], &[("src/value.ts", VALUE)], &[("src/value.ts", "const one = 1; const two = 2; export const value = one + two;\n")]),
        fixture("FPTSS201", &[("src/lib/orders/models.ts", "export interface Order { id: string; }\n")], &[("src/lib/orders/models.ts", "export interface Order { readonly id: string; }\n")], &[("src/lib/orders/order.ts", "export interface Order { id: string; }\n")]),
        shape_fixture("FPTSS601", "max_file_lines", &[("src/value.ts", "const one = 1;\nexport const two = 2;\n")], &[("src/value.ts", VALUE)], &[("src/value.ts", "export const value: { readonly text: string } = { text: 'a very long line' };\n")]),
        fixture("FPTSA001", &[("src/run.ts", "export function run(value): void { void value; }\n")], &[("src/run.ts", "export function run(value: string): void { void value; }\n")], &[("src/run.ts", "function run(value): void { void value; }\n")]),
        fixture("FPTSA002", &[("src/run.ts", "export function run() { return undefined; }\n")], &[("src/run.ts", "export function run(): void {}\n")], &[("src/run.ts", "function run() {}\n")]),
        fixture("FPTSA003", &[("src/run.ts", "declare function build(): object; export function run(): void { const value = build(); void value; }\n")], &[("src/run.ts", "declare function build(): object; export function run(): void { const value: object = build(); void value; }\n")], &[("src/run.ts", "export function run(): void { const value = 1; void value; }\n")]),
        fixture("FPTSH009", &[("src/run.ts", "initialize();\n")], &[("src/run.ts", "export function initialize(): void {}\n")], &[("tests/run.ts", "initialize();\n")]),
        fixture("FPTSC101", &[("src/run.ts", "export async function run(response: Response): Promise<unknown> { return response.json \n ( ); }\n")], &[("src/run.ts", "export async function run(response: Response): Promise<unknown> { return Schema.parse \n (await response.json ( )); }\n")], &[("tests/run.ts", "export async function run(response: Response): Promise<unknown> { return response.json(); }\n")]),
        fixture("FPTSC102", &[("src/run.ts", "export async function run(response: Response): Promise<Data> { return await response.json (\n ) as\n Data; }\n")], &[("src/run.ts", "export async function run(response: Response): Promise<Data> { return DataSchema.parse(await response.json()); }\n")], &[("src/run.ts", "export const text = '.json() as Data';\n")]),
        fixture("FPTSC103", &[("src/run.ts", "interface Props {\n  value:\n    any;\n}\n")], &[("src/run.ts", "export type WithoutChild<T> = T extends { child?: any } ? Omit<T, 'child'> : T;\n")], &[("src/run.ts", "function run(value: any): any { return value; }\n")]),
        test_fixture("FPTST001", &[("src/value.ts", VALUE), ("tests/value.test.ts", "test.skip('pending', () => {});\n")], &[("src/value.ts", VALUE), ("tests/value.test.ts", GOOD_TEST)], &[("src/value.ts", VALUE), ("tests/value.test.ts", "const text = 'test.skip('; test('given text when read then works', () => expect(text).toBe(text));\n")]),
        test_fixture("FPTST002", &[("src/lib/orders/value.ts", VALUE), ("tests/orphan/value.test.ts", GOOD_TEST)], &[("src/lib/orders/value.ts", VALUE), ("tests/lib/orders/value.test.ts", GOOD_TEST), ("tests/setup.ts", "setup();\n")], &[("src/value.ts", VALUE), ("src/value.test.ts", GOOD_TEST)]),
        test_fixture("FPTST003", &[("src/lib/orders/_state/order.state.svelte.ts", ENTRY)], &[("src/lib/orders/_state/order.state.svelte.ts", ENTRY), ("tests/lib/orders/_state/order.state.test.ts", GOOD_TEST)], &[("src/lib/orders/_helpers/order.ts", ENTRY)]),
        test_fixture("FPTST004", &[("src/lib/orders/_adapters/order.ts", ENTRY)], &[("src/lib/orders/_adapters/order.ts", ENTRY), ("tests/integration/lib/orders/_adapters/order.test.ts", GOOD_TEST)], &[("src/lib/orders/_helpers/order.ts", ENTRY)]),
        each_fixture("FPTST201", "interface Case { readonly expected: string; }", GOOD_INTERFACE, "interface Case { readonly description?: string; readonly expected: string; }"),
        each_fixture("FPTST202", "interface Case { readonly description: string; }", GOOD_INTERFACE, "interface Case { readonly description: string; readonly expectedly: string; }"),
        test_fixture("FPTST302", &[("src/value.ts", VALUE), ("tests/value.test.ts", "it \n ( 'returns value', () => {});\n")], &[("src/value.ts", VALUE), ("tests/value.test.ts", "test \n ( 'given value when read then works', () => {});\n")], &[("src/value.ts", VALUE), ("tests/value.test.ts", "const text = \"test('returns value', () => {})\"; // it('bad name', () => {});\nconst name = 'given value when read then works'; test(name, () => {});\n")]),
        test_fixture("FPTST401", &[("src/value.ts", VALUE), ("tests/value.test.ts", "interface Case { readonly description: string; readonly expected: string; } const cases: Case[] = []; test.each<Case>(cases)('$description', (testCase) => expect(testCase.expected).toBe(testCase.expected));\n")], &[("src/value.ts", VALUE), ("tests/value.test.ts", GOOD_EACH)], &[("src/value.ts", VALUE), ("tests/value.test.ts", GOOD_EACH_SATISFIES)]),
        each_source_fixture("FPTST402", GOOD_INTERFACE, "item", "$description", "expect(item.expected).toBe(item.expected);"),
        each_fixture("FPTST403", "interface Case { description: string; expected: string; }", GOOD_INTERFACE, "type Case = { readonly description: string; readonly expected: string; };"),
        each_source_fixture("FPTST404", GOOD_INTERFACE, "testCase", "$description", "expect(testCase.description).toBe('literal');"),
        each_source_fixture("FPTST405", GOOD_INTERFACE, "testCase", "$description", "if (testCase.expected) { expect(testCase.expected).toBe(testCase.expected); }"),
        each_source_fixture("FPTST406", GOOD_INTERFACE, "testCase", "case", "expect(testCase.expected).toBe(testCase.expected);"),
        each_source_fixture("FPTST410", GOOD_INTERFACE, "testCase", "$description", "testCase.expected = 'changed';"),
        test_fixture("FPTST411", &[("src/value.ts", VALUE), ("tests/value.test.ts", "interface Case { readonly description: string; readonly expected: string; } test.each<Case>([])('$description', (testCase) => expect(testCase.expected).toBe(testCase.expected));\n")], &[("src/value.ts", VALUE), ("tests/value.test.ts", GOOD_EACH)], &[("src/value.ts", VALUE), ("tests/value.test.ts", "test('given no table when testing then direct test works', () => {});\n")]),
        test_fixture("FPTST412", &[("src/value.ts", VALUE), ("tests/value.test.ts", "interface Case { readonly description: string; readonly expected: string; } test.each<Case>([['case', 'value']])('$description', (testCase) => expect(testCase.expected).toBe(testCase.expected));\n")], &[("src/value.ts", VALUE), ("tests/value.test.ts", GOOD_EACH)], &[("src/value.ts", VALUE), ("tests/value.test.ts", "test.each<Case>([{ description: 'case', expected: 'value' }] as const)('$description', (testCase) => expect(testCase.expected).toBe(testCase.expected)); interface Case { readonly description: string; readonly expected: string; }\n")]),
        fixture("FPTSN001", &[("src/run.ts", "export function shouldRun(): string { return 'yes'; }\n")], &[("src/run.ts", "export function shouldRun(): boolean { return true; }\n")], &[("src/run.ts", "export function issueReady(): string { return 'yes'; }\n")]),
        fixture("FPTSN002", &[("src/run.ts", "export function validateOrder(): string { return 'yes'; }\n")], &[("src/run.ts", "export function validateOrder(): void {}\n")], &[("src/run.ts", "export function revalidateOrder(): string { return 'yes'; }\n")]),
        fixture("FPTSN003", &[("src/run.ts", "export function getOrder(): void {}\n")], &[("src/run.ts", "export function getOrder(): string { return 'order'; }\n")], &[("src/run.ts", "export function targetOrder(): void {}\n")]),
        fixture("FPTSN004", &[("src/run.ts", "export function iterateOrders(): string[] { return []; }\n")], &[("src/run.ts", "export function iterateOrders(): Iterable<string> { return []; }\n")], &[("src/run.ts", "export function reiterateOrders(): string[] { return []; }\n")]),
        shape_fixture("FPSKS101", "max_state_lines", &[("src/lib/orders/_state/order.state.svelte.ts", "const one = 1;\nconst two = 2;\n")], &[("src/lib/orders/_state/order.state.svelte.ts", "const one = 1;\n")], &[("src/lib/orders/_state/order.ts", "const one = 1;\nconst two = 2;\n")]),
        fixture("FPSKS102", &[("src/lib/orders/_state/order.state.svelte.ts", "const value = $state(0);\n")], &[("src/lib/orders/_state/order.state.svelte.ts", "export function createOrderState(): object { const value = $state(0); return { value }; }\n")], &[("src/App.svelte", "<script lang=\"ts\">const value = $state(0);</script><p>{value}</p>\n")]),
        shape_fixture("FPSKS103", "max_route_script_lines", &[("src/routes/orders/+page.svelte", "<script lang=\"ts\">\nconst one = 1;\nconst two = 2;\n</script>\n")], &[("src/routes/orders/+page.svelte", "<script lang=\"ts\">const one = 1;</script>\n")], &[("src/routes/orders/+page.ts", "const one = 1;\nconst two = 2;\n")]),
        shape_fixture("FPSKS104", "max_component_script_lines", &[("src/lib/orders/components/Card.svelte", "<script lang=\"ts\">\nconst one = 1;\nconst two = 2;\n</script>\n")], &[("src/lib/orders/components/Card.svelte", "<script lang=\"ts\">const one = 1;</script>\n")], &[("src/lib/orders/components/card.ts", "const one = 1;\nconst two = 2;\n")]),
        shape_fixture("FPSKS107", "max_state_cells", &[("src/lib/orders/_state/order.state.svelte.ts", "export function createOrderState(): object { const one = $state(1); const two = $state(2); return { one, two }; }\n")], &[("src/lib/orders/_state/order.state.svelte.ts", "export function createOrderState(): object { const one = $state(1); return { one }; }\n")], &[("src/lib/orders/_state/order.state.ts", "export function createOrderState(): object { const one = 1; const two = 2; return { one, two }; }\n")]),
        shape_fixture("FPSKS108", "max_total_runes", &[("src/lib/orders/_state/order.state.svelte.ts", "export function createOrderState(): object { const one = $state(1); const text = '$derived(2)'; return { one, text }; }\n")], &[("src/lib/orders/_state/order.state.svelte.ts", "export function createOrderState(): object { const one = $state(1); return { one }; }\n")], &[("src/lib/orders/_state/order.state.svelte.ts", "export function createOrderState(): object { const one = $host(); const two = $host(); return { one, two }; }\n")]),
        shape_fixture("FPSKS109", "max_state_functions", &[("src/lib/orders/_state/order.state.svelte.ts", "function update(): void {} export function createOrderState(): object { return { update }; }\n")], &[("src/lib/orders/_state/order.state.svelte.ts", "export function createOrderState(): object { const one = (): void => {}; const two = (): void => {}; return { one, two }; }\n")], &[("src/lib/orders/_state/order.ts", "function update(): void {} export function createOrderState(): object { return { update }; }\n")]),
        shape_fixture("FPTSS110", "max_api_lines", &[("src/lib/orders/_api/order.ts", "const one = 1;\nconst two = 2;\n")], &[("src/lib/orders/_api/order.ts", "const one = 1;\n")], &[("src/lib/orders/api/order.ts", "const one = 1;\nconst two = 2;\n")]),
        shape_fixture("FPTSS111", "max_api_exports", &[("src/lib/orders/_api/order.ts", "export const one = 1; export const two = 2;\n")], &[("src/lib/orders/_api/order.ts", "export const one = 1;\n")], &[("src/lib/orders/api/order.ts", "export const one = 1; export const two = 2;\n")]),
        fixture("FPSKA101", &[("src/lib/orders/components/Card.svelte", "<script lang=\"ts\">fetch('/orders');</script>\n")], &[("src/lib/orders/_api/order.ts", "export function load(): Promise<Response> { return fetch('/orders'); }\n")], &[("src/lib/orders/components/Card.svelte", "<p>fetch('/orders')</p><!-- fetch('/orders') -->\n")]),
        fixture("FPSKA102", &[("src/lib/orders/components/Card.svelte", "<script lang=\"ts\">const id = '1'; const endpoint = `/api/orders/${id}`;</script>\n")], &[("src/lib/orders/_api/order.ts", "const id = '1'; export const endpoint = `/api/orders/${id}`;\n")], &[("src/lib/orders/components/Card.svelte", "<p>/api/orders</p><!-- `/api/orders/${id}` -->\n")]),
        fixture("FPSKA103", &[("src/lib/orders/components/Card.svelte", "<script lang=\"ts\">import { goto as navigate } from '$app/navigation'; navigate('/orders');</script>\n")], &[("src/routes/orders/+page.svelte", "<script lang=\"ts\">import { goto } from '$app/navigation'; goto('/orders');</script>\n")], &[("src/lib/orders/components/Card.svelte", "<script lang=\"ts\">function goto(path: string): void { void path; } goto('/orders');</script>\n")]),
        import_fixture("FPSKL104", &[("src/routes/orders/+page.ts", "import { value } from '../payments/+page'; export const used = value;\n"), ("src/routes/payments/+page.ts", VALUE)], &[("src/routes/orders/+page.ts", "import { value } from './value'; export const used = value;\n"), ("src/routes/orders/value.ts", VALUE)], &[("src/routes/orders/+page.ts", "import { value } from '$lib/orders/main/value'; export const used = value;\n")]),
        fixture("FPSKL106", &[("src/lib/orders/components/Card.svelte", "<script lang=\"ts\">import fs from 'node:fs'; void fs;</script>\n")], &[("src/routes/orders/+page.server.ts", "import fs from 'node:fs'; export const load = () => fs;\n")], &[("src/lib/orders/components/Card.svelte", "<script lang=\"ts\">import value from 'filesystem'; void value;</script>\n")]),
        import_fixture("FPSKL107", &[("src/routes/orders/+page.server.ts", "import Card from '$lib/orders/components/Card.svelte'; export const load = () => Card;\n"), ("src/lib/orders/components/Card.svelte", "<p>card</p>\n")], &[("src/routes/orders/+page.server.ts", "import type { Order } from '$lib/orders/types'; export const load = (): Order => ({ id: '1' });\n"), ("src/lib/orders/types.ts", "export interface Order { readonly id: string; }\n")], &[("src/routes/orders/+page.ts", "import Card from '$lib/orders/components/Card.svelte'; export const load = () => Card;\n"), ("src/lib/orders/components/Card.svelte", "<p>card</p>\n")]),
        fixture("FPSKV101", &[("src/value.ts", "export function create(): object { const value = $state(0); return { value }; }\n")], &[("src/value.svelte.ts", "export function create(): object { const value = $state(0); return { value }; }\n")], &[("src/value.ts", "export const text = '$state(0)'; // $state(1)\n")]),
        fixture("FPSKV102", &[("src/lib/orders/_state/order.state.svelte.ts", "export function create(): object { return {}; }\n")], &[("src/lib/orders/_state/order.state.svelte.ts", "export function createOrderState(): object { return {}; }\n")], &[("src/lib/orders/_helpers/order.svelte.ts", "export function create(): object { return {}; }\n")]),
        shape_fixture("FPSKV103", "max_state_public_members", &[("src/lib/orders/_state/order.state.svelte.ts", "export function createOrderState(): object { const one = 1; const two = 2; return { one, two }; } function unrelated(): object { return { one: 1 }; }\n")], &[("src/lib/orders/_state/order.state.svelte.ts", "export function createOrderState(): object { const one = 1; return { one }; } function unrelated(): object { return { one: 1, two: 2, three: 3 }; }\n")], &[("src/lib/orders/_state/order.state.svelte.ts", "export function createOrderState(): object { return { nested: { one: 1, two: 2 } }; }\n")]),
        import_fixture("FPSKV104", &[("src/state.ts", "export const state = { value: 1 };\n"), ("src/use.ts", "import { state } from './state'; state.value += 1;\n")], &[("src/state.ts", "export const state = { value: 1, update(): void {} };\n"), ("src/use.ts", "import { state } from './state'; state.update();\n")], &[("src/use.ts", "const state = { value: 1 }; state.value += 1;\n")]),
        fixture("FPSKV105", &[("src/value.svelte.ts", "export function create(): object { const value = $derived(() => 1); return { value }; }\n")], &[("src/value.svelte.ts", "export function create(): object { const value = $derived.by(() => 1); return { value }; }\n")], &[("src/value.svelte.ts", "export function create(): object { const value = $derived(1 + 1); return { value }; }\n")]),
        fixture("FPSKV106", &[("src/value.svelte.ts", "export function create(): void { $effect(() => { fetch('/orders'); }); }\n")], &[("src/value.svelte.ts", "export function create(): void { fetch('/orders'); $effect(() => {}); }\n")], &[("src/value.svelte.ts", "export function create(): void { $effect(() => { const text = 'fetch()'; }); }\n")]),
        fixture("FPSKV107", &[("src/App.svelte", "<script lang=\"ts\">import { onMount } from 'svelte'; onMount(() => { $effect(() => {}); $effect(() => {}); });</script>\n")], &[("src/App.svelte", "<script lang=\"ts\">import { onMount } from 'svelte'; $effect(() => {}); onMount(() => {});</script>\n")], &[("src/App.svelte", "<p>onMount and $effect are lifecycle names</p>\n")]),
        fixture("FPSKV201", &[("src/lib/orders/main/open.ts", "export function open(): WebSocket { return new WebSocket('ws://x'); }\n")], &[("src/lib/orders/components/Card.svelte", "<script lang=\"ts\">import { onMount } from 'svelte'; function later(): void { setTimeout(() => {}, 1); } onMount(() => {});</script><p>card</p>\n")], &[("src/lib/orders/components/Card.svelte", "<p>new WebSocket('ws://x')</p><!-- new WebSocket('ws://x') -->\n")]),
        fixture("FPSKV202", &[("src/lib/orders/_resources/socket.resource.ts", "export function open(): WebSocket { return new WebSocket('ws://one'); }\n")], &[("src/lib/orders/_resources/create-debounce.resource.ts", "export function debounce(): void { const timeout = setTimeout(() => {}, 1); clearTimeout(timeout); }\n")], &[("src/lib/orders/_resources/socket.resource.ts", "export function stop(): void { clearInterval(1); }\n")]),
        fixture("FPSKU001", &[("components.json", "{\"aliases\":{\"ui\":\"$ui-kit\",\"utils\":\"$lib/utils\"}}\n")], &[("components.json", "{\"aliases\":{\"ui\":\"$ui-kit\",\"utils\":\"$ui-kit/utils\"}}\n")], &[("components.json", "{\"aliases\":{\"ui\":\"$ui-kit\",\"utils\":\"$ui-kit/utils\"}}\n"), ("src/value.ts", "export const text = '$ui-kit $ui-kit/utils';\n")]),
        import_fixture("FPSKU002", &[("src/lib/orders/main/value.ts", VALUE), ("src/ui-kit/button/button.ts", "import { value } from '$lib/orders/main/value'; export const button = value;\n")], &[("src/ui-kit/utils.ts", VALUE), ("src/ui-kit/button/button.ts", "import { value } from '../utils'; export const button = value;\n")], &[("src/ui-kit/button/button.ts", "import { value } from 'external'; export const button = value;\n")]),
        fixture("FPSKU003", &[("src/ui-kit/button/nested/button.svelte", "<button>bad</button>\n")], &[("src/ui-kit/button/button.svelte", "<button>good</button>\n")], &[("src/ui-kit/utils.ts", VALUE)]),
        fixture("FPSKC201", &[("openapi.json", "{\"paths\":{\"/api/orders/{id}/summary\":{}}}\n"), ("src/lib/orders/_api/order.ts", "const id = '1'; export const dynamic = `/api/orders/${id}/details`;\n")], &[("openapi.json", "{\"paths\":{\"/api/known/\":{},\"/api/orders/{id}/details\":{}}}\n"), ("src/lib/orders/_api/order.ts", "const id = '1'; export const dynamic = `/api/orders/${id}/details`; export const trailing = '/api/known/';\n")], &[("openapi.json", "{\"paths\":{}}\n"), ("src/lib/orders/_api/order.ts", "export const endpoint = '/health';\n")]),
    ]
}

const VALUE: &str = "export const value = 1;\n";
const ENTRY: &str = "export function run(): void {}\n";
const ONE_STATEMENT: &str = "export function run(): void { call(); }\n";
const TWO_STATEMENTS: &str = "export function run(): void { call(); call(); }\n";
const ONE_CALL: &str = "declare function one(): void; export function run(): void { one(); }\n";
const TWO_CALLS: &str = "declare function one(): void; declare function two(): void; export function run(): void { one(); two(); }\n";
const ONE_LOCAL: &str = "export function run(): void { const one = 1; void one; }\n";
const TWO_LOCALS: &str = "export function run(): void { const one = 1; const two = 2; void one; void two; }\n";
const ONE_ARGUMENT: &str = "export function run(value: string): void { void value; }\n";
const TWO_ARGUMENTS: &str = "export function run(first: string, second: string): void { void first; void second; }\n";
const GOOD_TEST: &str = "test('given value when read then returns value', () => expect(1).toBe(1));\n";
const GOOD_INTERFACE: &str = "interface Case { readonly description: string; readonly expected: string; }";
const GOOD_EACH: &str = "interface Case { readonly description: string; readonly expected: string; } test.each<Case>([{ description: 'case', expected: 'value' }])('$description', (testCase) => expect(testCase.expected).toBe(testCase.expected));\n";
const GOOD_EACH_SATISFIES: &str = "interface Case { readonly description: string; readonly expected: string; } test.each([{ description: 'case', expected: 'value' }] satisfies readonly Case[])('$description', (testCase) => expect(testCase.expected).toBe(testCase.expected));\n";

fn fixture(code: &'static str, failing: &'static [(&'static str, &'static str)], passing: &'static [(&'static str, &'static str)], near_miss: &'static [(&'static str, &'static str)]) -> WebRuleFixture {
    WebRuleFixture { code, failing, passing, near_miss, threshold: None }
}

fn role_fixture(code: &'static str, failing: &'static [(&'static str, &'static str)], passing: &'static [(&'static str, &'static str)], near_miss: &'static [(&'static str, &'static str)], threshold: Option<(&'static str, u32)>) -> WebRuleFixture {
    WebRuleFixture { code, failing, passing, near_miss, threshold }
}

fn import_fixture(code: &'static str, failing: &'static [(&'static str, &'static str)], passing: &'static [(&'static str, &'static str)], near_miss: &'static [(&'static str, &'static str)]) -> WebRuleFixture {
    fixture(code, failing, passing, near_miss)
}

fn shape_fixture(code: &'static str, threshold: &'static str, failing: &'static [(&'static str, &'static str)], passing: &'static [(&'static str, &'static str)], near_miss: &'static [(&'static str, &'static str)]) -> WebRuleFixture {
    role_fixture(code, failing, passing, near_miss, Some((threshold, 1)))
}

fn test_fixture(code: &'static str, failing: &'static [(&'static str, &'static str)], passing: &'static [(&'static str, &'static str)], near_miss: &'static [(&'static str, &'static str)]) -> WebRuleFixture {
    fixture(code, failing, passing, near_miss)
}

fn each_fixture(code: &'static str, failing_interface: &'static str, passing_interface: &'static str, near_interface: &'static str) -> WebRuleFixture {
    each_source_fixture(code, failing_interface, "testCase", "$description", "expect(testCase.expected).toBe(testCase.expected);").with_passing_interfaces(passing_interface, near_interface)
}

fn each_source_fixture(code: &'static str, interface: &'static str, callback: &'static str, title: &'static str, body: &'static str) -> WebRuleFixture {
    let failing = Box::leak(format!("{interface} test.each<Case>([{{ description: 'case', expected: 'value' }}])('{title}', ({callback}) => {{ {body} }});\n").into_boxed_str());
    WebRuleFixture { code, failing: Box::leak(vec![("tests/value.test.ts", failing as &str), ("src/value.ts", VALUE)].into_boxed_slice()), passing: &[("src/value.ts", VALUE), ("tests/value.test.ts", GOOD_EACH)], near_miss: &[("src/value.ts", VALUE), ("tests/value.test.ts", GOOD_EACH_SATISFIES)], threshold: None }
}

trait WithPassingInterfaces {
    fn with_passing_interfaces(self, passing: &'static str, near: &'static str) -> Self;
}

impl WithPassingInterfaces for WebRuleFixture {
    fn with_passing_interfaces(mut self, passing: &'static str, near: &'static str) -> Self {
        let passing_source = Box::leak(format!("{passing} test.each<Case>([{{ description: 'case', expected: 'value' }}])('$description', (testCase) => expect(testCase.expected).toBe(testCase.expected));\n").into_boxed_str());
        let near_source = Box::leak(format!("{near} test.each<Case>([{{ description: 'case', expected: 'value' }}])('$description', (testCase) => expect(testCase.expected).toBe(testCase.expected));\n").into_boxed_str());
        self.passing = Box::leak(vec![("src/value.ts", VALUE), ("tests/value.test.ts", passing_source as &str)].into_boxed_slice());
        self.near_miss = Box::leak(vec![("src/value.ts", VALUE), ("tests/value.test.ts", near_source as &str)].into_boxed_slice());
        self
    }
}
