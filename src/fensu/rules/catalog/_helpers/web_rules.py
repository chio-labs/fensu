"""Native web rule catalogue and complete legacy-policy migration inventory."""

from __future__ import annotations

from collections.abc import Mapping
from operator import itemgetter

from fensu.config.types import AnalyzerId
from fensu.rules.authoring.models import RuleConstraint, RuleSpec
from fensu.rules.authoring.types import ExecutionOwner, Family, Threshold

type _WebRuleMigration = tuple[str, str, bool, str]

_GENERIC_REASON: str = "Framework-independent TypeScript/JavaScript architecture policy."
_SVELTE_REASON: str = "Requires Svelte component or rune semantics."
_SVELTEKIT_REASON: str = "Requires SvelteKit route, loader, server, or browser/runtime semantics."
_RACEWATCH_REASON: str = "Depends on RaceWatch UI-kit, API, OpenAPI, or adapter conventions."

_WEB_RULE_MIGRATION: tuple[_WebRuleMigration, ...] = (
    (
        "FWP001",
        "generic-typescript",
        True,
        "Direct and project-support syntax is parsed natively; trusted parse failures emit "
        "FWP001, while evaluation-excluded and generated sources stay diagnostic-silent.",
    ),
    ("FWR201", "generic-typescript", True, _GENERIC_REASON),
    ("FWR204", "generic-typescript", True, _GENERIC_REASON),
    ("FWR306", "generic-typescript", True, _GENERIC_REASON),
    ("FWR301", "generic-typescript", True, _GENERIC_REASON),
    ("FWR309", "generic-typescript", True, _GENERIC_REASON),
    ("FWR310", "generic-typescript", True, _GENERIC_REASON),
    ("FWR311", "generic-typescript", True, _GENERIC_REASON),
    ("FWR403", "generic-typescript", True, _GENERIC_REASON),
    ("FWU001", "racewatch-specific/deferred", False, _RACEWATCH_REASON),
    ("FWU002", "racewatch-specific/deferred", False, _RACEWATCH_REASON),
    ("FWU003", "racewatch-specific/deferred", False, _RACEWATCH_REASON),
    ("FWL101", "generic-typescript", True, _GENERIC_REASON),
    ("FWL108", "generic-typescript", True, _GENERIC_REASON),
    ("FWL109", "generic-typescript", True, _GENERIC_REASON),
    ("FWS001", "generic-typescript", True, _GENERIC_REASON),
    ("FWS002", "generic-typescript", True, _GENERIC_REASON),
    ("FWS003", "generic-typescript", True, _GENERIC_REASON),
    ("FWS010", "generic-typescript", True, _GENERIC_REASON),
    ("FWS011", "generic-typescript", True, _GENERIC_REASON),
    ("FWS601", "generic-typescript", True, _GENERIC_REASON),
    ("FWS110", "racewatch-specific/deferred", False, _RACEWATCH_REASON),
    ("FWS111", "racewatch-specific/deferred", False, _RACEWATCH_REASON),
    ("FWS101", "svelte", False, _SVELTE_REASON),
    ("FWS102", "svelte", False, _SVELTE_REASON),
    ("FWS103", "sveltekit", False, _SVELTEKIT_REASON),
    ("FWS104", "svelte", False, _SVELTE_REASON),
    ("FWS105", "generic-typescript", True, _GENERIC_REASON),
    ("FWS106", "generic-typescript", True, _GENERIC_REASON),
    ("FWA101", "sveltekit", False, _SVELTEKIT_REASON),
    ("FWA001", "generic-typescript", True, _GENERIC_REASON),
    ("FWA002", "generic-typescript", True, _GENERIC_REASON),
    ("FWA003", "generic-typescript", True, _GENERIC_REASON),
    ("FWA102", "sveltekit", False, _SVELTEKIT_REASON),
    ("FWR001", "generic-typescript", True, _GENERIC_REASON),
    ("FWR002", "generic-typescript", True, _GENERIC_REASON),
    ("FWR003", "generic-typescript", True, _GENERIC_REASON),
    ("FWR304", "generic-typescript", True, _GENERIC_REASON),
    ("FWR401", "generic-typescript", True, _GENERIC_REASON),
    (
        "FWR404",
        "svelte",
        True,
        "The explicit state-role filename contract is retained for both web analyzers.",
    ),
    (
        "FWR405",
        "svelte",
        True,
        "The explicit resource-role filename contract is retained for both web analyzers.",
    ),
    ("FWR501", "generic-typescript", True, _GENERIC_REASON),
    ("FWL102", "generic-typescript", True, _GENERIC_REASON),
    ("FWL103", "generic-typescript", True, _GENERIC_REASON),
    ("FWL104", "sveltekit", False, _SVELTEKIT_REASON),
    ("FWL105", "generic-typescript", True, _GENERIC_REASON),
    ("FWL106", "sveltekit", False, _SVELTEKIT_REASON),
    ("FWL107", "sveltekit", False, _SVELTEKIT_REASON),
    ("FWL201", "generic-typescript", True, _GENERIC_REASON),
    ("FWV101", "svelte", False, _SVELTE_REASON),
    ("FWV102", "svelte", False, _SVELTE_REASON),
    ("FWV103", "svelte", False, _SVELTE_REASON),
    ("FWV104", "svelte", False, _SVELTE_REASON),
    ("FWV105", "svelte", False, _SVELTE_REASON),
    ("FWV106", "svelte", False, _SVELTE_REASON),
    ("FWV107", "svelte", False, _SVELTE_REASON),
    ("FWV201", "svelte", False, _SVELTE_REASON),
    ("FWV202", "svelte", False, _SVELTE_REASON),
    ("FWH009", "generic-typescript", True, _GENERIC_REASON),
    ("FWC101", "generic-typescript", True, _GENERIC_REASON),
    ("FWC102", "generic-typescript", True, _GENERIC_REASON),
    ("FWC103", "generic-typescript", True, _GENERIC_REASON),
    ("FWC201", "racewatch-specific/deferred", False, _RACEWATCH_REASON),
    ("FWT001", "generic-typescript", True, _GENERIC_REASON),
    ("FWT201", "generic-typescript", True, _GENERIC_REASON),
    ("FWT202", "generic-typescript", True, _GENERIC_REASON),
    ("FWT401", "generic-typescript", True, _GENERIC_REASON),
    ("FWT402", "generic-typescript", True, _GENERIC_REASON),
    ("FWT403", "generic-typescript", True, _GENERIC_REASON),
    ("FWT406", "generic-typescript", True, _GENERIC_REASON),
    ("FWT410", "generic-typescript", True, _GENERIC_REASON),
    ("FWT411", "generic-typescript", True, _GENERIC_REASON),
    ("FWT412", "generic-typescript", True, _GENERIC_REASON),
    ("FWT405", "generic-typescript", True, _GENERIC_REASON),
    ("FWT404", "generic-typescript", True, _GENERIC_REASON),
    ("FWN001", "generic-typescript", True, _GENERIC_REASON),
    ("FWN002", "generic-typescript", True, _GENERIC_REASON),
    ("FWN003", "generic-typescript", True, _GENERIC_REASON),
    ("FWN004", "generic-typescript", True, _GENERIC_REASON),
    ("FWS107", "svelte", False, _SVELTE_REASON),
    ("FWS108", "svelte", False, _SVELTE_REASON),
    ("FWS109", "svelte", False, _SVELTE_REASON),
    ("FWS201", "generic-typescript", True, _GENERIC_REASON),
    ("FWT002", "generic-typescript", True, _GENERIC_REASON),
    ("FWT302", "generic-typescript", True, _GENERIC_REASON),
    ("FWA103", "sveltekit", False, _SVELTEKIT_REASON),
    ("FWT003", "generic-typescript", True, _GENERIC_REASON),
    ("FWT004", "generic-typescript", True, _GENERIC_REASON),
)

_RULE_DETAILS: tuple[tuple[str, Family, str, str, str], ...] = (
    (
        "FWP001",
        Family.PARSING,
        "source-files-must-be-parseable",
        "source files must be parseable",
        "Correct the syntax error so architecture facts can be extracted reliably.",
    ),
    (
        "FWR001",
        Family.ROLES,
        "types-only-types",
        "type roles contain only type declarations",
        "Move runtime declarations into the main, helper, schema, or constant role that owns them.",
    ),
    (
        "FWR002",
        Family.ROLES,
        "constants-no-behavior",
        "constant roles contain no behavior",
        "Move functions and classes out of constants.ts into their owning role.",
    ),
    (
        "FWR003",
        Family.ROLES,
        "errors-only-errors",
        "error roles contain only error declarations",
        "Keep typed errors in errors.ts and move other declarations to their owning role.",
    ),
    (
        "FWR201",
        Family.ROLES,
        "generic-filenames",
        "generic filenames must not hide ownership",
        "Rename the module after the operation or concept it owns.",
    ),
    (
        "FWR204",
        Family.ROLES,
        "generic-owner-names",
        "generic owner names must not organize application code",
        "Move the code beneath the named business or technical capability that owns it.",
    ),
    (
        "FWR301",
        Family.ROLES,
        "role-container-layout",
        "role containers remain bounded and flat or grouped",
        "Keep main and _helpers flat, or group every module into shallow specifically "
        "named buckets.",
    ),
    (
        "FWR304",
        Family.ROLES,
        "explicit-role-placement",
        "owner modules live beneath explicit roles",
        "Move the module under main, an internal role, components, or a fixed role file.",
    ),
    (
        "FWR306",
        Family.ROLES,
        "owner-leaf-or-branch",
        "owners must be either leaves or branches",
        "Keep roles directly in a leaf owner, or move all work into named subdomains.",
    ),
    (
        "FWR309",
        Family.ROLES,
        "leaf-main-boundary",
        "every leaf capability exposes a main boundary",
        "Add a focused main entry, or move passive declarations to the capability whose "
        "behavior owns them.",
    ),
    (
        "FWR310",
        Family.ROLES,
        "internal-role-prefix",
        "owner-internal role directories require an underscore prefix",
        "Prefix the internal role with an underscore so its privacy is visible in the path.",
    ),
    (
        "FWR311",
        Family.ROLES,
        "no-main-only-capability",
        "runtime capabilities must not consist only of main entries",
        "Collapse the entry into the capability that owns its inputs or output; do not add "
        "placeholder roles to preserve a main-only owner.",
    ),
    (
        "FWR401",
        Family.ROLES,
        "main-entry-shape",
        "main entries expose one focused public function",
        "Keep one public operation and move detailed phases into owner-internal modules.",
    ),
    (
        "FWR403",
        Family.ROLES,
        "no-reexports",
        "application modules must not re-export declarations",
        "Import the defining module directly and remove the re-export or barrel.",
    ),
    (
        "FWR404",
        Family.ROLES,
        "state-file-suffix",
        "state role files use the state suffix",
        "Rename the file to <capability>.state.svelte.ts and expose one state factory.",
    ),
    (
        "FWR405",
        Family.ROLES,
        "resource-file-suffix",
        "resource role files use the resource suffix",
        "Rename the file to <capability>.resource.svelte.ts when runes are needed, or "
        ".resource.ts otherwise.",
    ),
    (
        "FWR501",
        Family.ROLES,
        "one-runtime-class",
        "runtime class modules expose one filename-aligned public class",
        "Keep one exported runtime class per module and name its file after that class; keep "
        "related error classes in errors.ts.",
    ),
    (
        "FWL101",
        Family.LAYERS,
        "no-cross-owner-internals",
        "cross-owner imports must not enter internal roles",
        "Expose the capability through its public main, component, type, schema, or constant "
        "module.",
    ),
    (
        "FWL102",
        Family.LAYERS,
        "no-directory-imports",
        "directory imports must not resolve through index files",
        "Import the concrete module that defines the symbol.",
    ),
    (
        "FWL103",
        Family.LAYERS,
        "no-namespace-imports",
        "namespace imports hide defining modules",
        "Import the required declarations directly from their defining modules.",
    ),
    (
        "FWL105",
        Family.LAYERS,
        "runtime-no-test-tooling-imports",
        "runtime source must not import tests or tooling",
        "Move reusable runtime behavior into src and keep test/tooling dependencies one-way.",
    ),
    (
        "FWL108",
        Family.LAYERS,
        "private-main-local",
        "private main entries remain inside their capability",
        "Remove the leading underscore to publish the entry, or call it through a public "
        "main entry.",
    ),
    (
        "FWL109",
        Family.LAYERS,
        "public-main-used",
        "public main entries have an external consumer",
        "Prefix the entry filename with _ until another capability, route, or tooling consumer "
        "imports it.",
    ),
    (
        "FWL201",
        Family.LAYERS,
        "acyclic-imports",
        "project imports must remain acyclic",
        "Break the cycle by moving the shared contract or reversing the dependency through a "
        "public entry.",
    ),
    (
        "FWS001",
        Family.SHAPE,
        "entry-statements",
        "entry functions remain phase-shaped",
        "Extract cohesive phases into internal helpers and keep the entry as a short ordered flow.",
    ),
    (
        "FWS002",
        Family.SHAPE,
        "entry-calls",
        "entry functions coordinate a bounded number of calls",
        "Group related calls behind named phase helpers with explicit results.",
    ),
    (
        "FWS003",
        Family.SHAPE,
        "entry-locals",
        "entry functions keep a bounded number of locals",
        "Move intermediate state into cohesive phase helpers that return structured results.",
    ),
    (
        "FWS010",
        Family.SHAPE,
        "max-arguments",
        "functions keep a bounded argument list",
        "Reduce the responsibility or group cohesive inputs into a typed object.",
    ),
    (
        "FWS011",
        Family.SHAPE,
        "max-function-statements",
        "runtime functions remain below the statement budget",
        "Split the function at a meaningful behavior or phase boundary.",
    ),
    (
        "FWS105",
        Family.SHAPE,
        "max-imported-bindings",
        "modules must stay within the imported-binding budget",
        "Split the module at a cohesive responsibility boundary.",
    ),
    (
        "FWS106",
        Family.SHAPE,
        "max-public-exports",
        "modules must stay within the public-export budget",
        "Split the public surface into focused defining modules.",
    ),
    (
        "FWS201",
        Family.SHAPE,
        "immutable-models",
        "models role value contracts are immutable",
        "Mark every model property readonly and use readonly arrays, tuples, or collection "
        "wrappers.",
    ),
    (
        "FWS601",
        Family.SHAPE,
        "max-file-lines",
        "source modules remain below the configured line budget",
        "Split the module by a cohesive role or concern rather than arbitrary numbered fragments.",
    ),
    (
        "FWA001",
        Family.ANNOTATIONS,
        "public-parameter-annotations",
        "public functions annotate every parameter",
        "Annotate each public parameter with the accepted value type.",
    ),
    (
        "FWA002",
        Family.ANNOTATIONS,
        "public-return-annotations",
        "public functions declare return types",
        "Declare the public return type so the capability contract is explicit.",
    ),
    (
        "FWA003",
        Family.ANNOTATIONS,
        "local-binding-annotations",
        "non-scalar local bindings declare their types",
        "Annotate the first non-scalar local binding, use satisfies for a checked value "
        "contract, or provide an explicit generic type argument.",
    ),
    (
        "FWH009",
        Family.HYGIENE,
        "no-import-time-initialization",
        "runtime modules avoid import-time initialization",
        "Export a factory and expose explicit initialization instead of constructing a "
        "singleton during import.",
    ),
    (
        "FWC101",
        Family.CONTRACTS,
        "json-runtime-decoding",
        "JSON responses require runtime decoding",
        "Parse unknown response data through an approved runtime schema before returning or "
        "storing it.",
    ),
    (
        "FWC102",
        Family.CONTRACTS,
        "json-no-assertion",
        "JSON responses must not bypass decoding with assertions",
        "Replace the assertion with runtime schema parsing.",
    ),
    (
        "FWC103",
        Family.CONTRACTS,
        "no-public-any",
        "public contracts must not expose explicit any",
        "Replace any with a precise public type or unknown plus validation.",
    ),
    (
        "FWT001",
        Family.TESTS,
        "no-skipped-tests",
        "committed tests must not be skipped or empty",
        "Implement the behavior or remove the placeholder test.",
    ),
    (
        "FWT002",
        Family.TESTS,
        "test-layout",
        "tests follow the configured layout",
        "Move the test beside its source or into the configured mirrored test path.",
    ),
    (
        "FWT003",
        Family.TESTS,
        "critical-role-tests",
        "critical internal roles require focused tests",
        "Add a focused test for the state, API, resource, or adapter boundary.",
    ),
    (
        "FWT004",
        Family.TESTS,
        "imperative-adapter-integration-tests",
        "imperative adapters require an integration or browser test",
        "Add an integration or e2e test for the adapter boundary.",
    ),
    (
        "FWT201",
        Family.TESTS,
        "case-description",
        "parameterized test cases define description and expected fields",
        "Use a readonly local case interface with description and expected* fields.",
    ),
    (
        "FWT202",
        Family.TESTS,
        "case-expected",
        "parameterized test cases define expected fields",
        "Define at least one readonly expected* field on the inline test case type.",
    ),
    (
        "FWT302",
        Family.TESTS,
        "given-when-then",
        "test names describe given, when, and then",
        "Rename the test to state its precondition, action, and expected outcome.",
    ),
    (
        "FWT401",
        Family.TESTS,
        "inline-typed-cases",
        "parameterized cases remain inline and typed",
        "Pass an inline object array to test.each<TestCase> beside the behavior.",
    ),
    (
        "FWT402",
        Family.TESTS,
        "test-case-parameter",
        "parameterized callbacks accept testCase",
        "Name the typed behavior-case parameter testCase and read inputs and expectations from it.",
    ),
    (
        "FWT403",
        Family.TESTS,
        "readonly-local-case",
        "parameterized cases use an owner-local readonly interface",
        "Define a readonly case interface in the test module or its owner-local _test role.",
    ),
    (
        "FWT404",
        Family.TESTS,
        "expected-field-assertions",
        "parameterized assertions use expected case fields",
        "Compare outcomes with a testCase.expected* field instead of embedding an expectation.",
    ),
    (
        "FWT405",
        Family.TESTS,
        "branch-free-tests",
        "test bodies avoid outcome-dependent control flow",
        "Separate success and error behavior tables so each test body is branch-free.",
    ),
    (
        "FWT406",
        Family.TESTS,
        "description-test-title",
        "parameterized test titles use case descriptions",
        "Use $description as the test.each title so failures identify the behavior case.",
    ),
    (
        "FWT410",
        Family.TESTS,
        "immutable-cases",
        "parameterized tests do not mutate case data",
        "Treat testCase and its nested values as immutable test declarations.",
    ),
    (
        "FWT411",
        Family.TESTS,
        "nonempty-cases",
        "parameterized case arrays are nonempty",
        "Add at least one behavior case or remove the empty test declaration.",
    ),
    (
        "FWT412",
        Family.TESTS,
        "object-cases",
        "parameterized cases use object values",
        "Replace positional tuple cases with typed objects whose fields name each input and "
        "expectation.",
    ),
    (
        "FWN001",
        Family.NAMING,
        "predicate-return",
        "predicate names declare boolean returns",
        "Return boolean or rename the function to describe the value it returns.",
    ),
    (
        "FWN002",
        Family.NAMING,
        "validator-return",
        "validator names declare no meaningful return",
        "Return void and throw a typed error, or rename the function as a value-producing query.",
    ),
    (
        "FWN003",
        Family.NAMING,
        "value-return",
        "value-producing names declare a returned value",
        "Return the queried value or rename the function to describe its side effect.",
    ),
    (
        "FWN004",
        Family.NAMING,
        "iterator-return",
        "iterator names declare an iterable result",
        "Return an Iterator, Iterable, or generator, or rename the eager collection operation.",
    ),
)

_THRESHOLDS: dict[str, tuple[Threshold, ...]] = {
    "FWR301": (
        Threshold.MAX_MAIN_CONTAINER_MODULES,
        Threshold.MAX_HELPERS_CONTAINER_MODULES,
        Threshold.MAX_ROLE_DEPTH,
    ),
    "FWS001": (Threshold.MAX_STATEMENTS,),
    "FWS002": (Threshold.MAX_DISTINCT_CALLS,),
    "FWS003": (Threshold.MAX_LOCALS,),
    "FWS010": (Threshold.MAX_ARGUMENTS,),
    "FWS011": (Threshold.MAX_STATEMENTS_GLOBAL,),
    "FWS105": (Threshold.MAX_IMPORTED_BINDINGS,),
    "FWS106": (Threshold.MAX_PUBLIC_EXPORTS,),
    "FWS601": (Threshold.MAX_FILE_LINES,),
}
_PROJECT_RULES: frozenset[str] = frozenset(
    {
        "FWR204",
        "FWR301",
        "FWR306",
        "FWR309",
        "FWR311",
        "FWL109",
        "FWL201",
        "FWT003",
        "FWT004",
    }
)
_ANALYZERS: tuple[AnalyzerId, ...] = (AnalyzerId.TYPESCRIPT, AnalyzerId.SVELTE)
_CONSTRAINTS: dict[str, tuple[RuleConstraint, ...]] = {
    "FWR201": (
        RuleConstraint(
            name="forbidden module filenames",
            description="Generic module filenames that do not identify ownership",
            values=("common.ts", "helpers.ts", "services.ts", "store.ts", "utils.ts"),
        ),
    ),
    "FWR204": (
        RuleConstraint(
            name="forbidden owner names",
            description="Generic package names that do not identify a producer",
            values=(
                "common",
                "components",
                "composables",
                "config",
                "core",
                "data",
                "domains",
                "features",
                "misc",
                "platform",
                "schemas",
                "services",
                "shared",
                "stores",
                "types",
                "utils",
            ),
        ),
    ),
    "FWR301": (
        RuleConstraint(
            name="bounded role containers",
            description="Role containers governed by flat-or-grouped layout limits",
            values=("main", "_helpers"),
        ),
    ),
    "FWR304": (
        RuleConstraint(
            name="recognized direct role files",
            description="Role filenames allowed directly beneath a capability owner",
            values=("constants.ts", "errors.ts", "models.ts", "schemas.ts", "types.ts"),
        ),
    ),
    "FWR306": (
        RuleConstraint(
            name="leaf role boundaries",
            description="Directories and files that establish direct leaf-role content",
            values=(
                "main",
                "components",
                "schemas",
                "types",
                "_api",
                "_adapters",
                "_components",
                "_helpers",
                "_resources",
                "_state",
                "_test",
                "constants.ts",
                "errors.ts",
                "models.ts",
                "schemas.ts",
                "types.ts",
            ),
        ),
    ),
    "FWR310": (
        RuleConstraint(
            name="reserved internal role names",
            description="Internal role names that require a leading underscore",
            values=("api", "helpers", "resources", "state", "test"),
        ),
    ),
    "FWR403": (
        RuleConstraint(
            name="exempt configured surfaces",
            description="Configured UI-kit modules may provide deliberate re-export surfaces",
            values=("ui_kit",),
        ),
    ),
    "FWR404": (
        RuleConstraint(
            name="state module suffixes",
            description="Accepted state-role module suffixes",
            values=(".state.svelte.ts", ".state.svelte.js"),
        ),
    ),
    "FWR405": (
        RuleConstraint(
            name="resource module suffixes",
            description="Accepted resource-role module suffixes",
            values=(
                ".resource.ts",
                ".resource.js",
                ".resource.svelte.ts",
                ".resource.svelte.js",
            ),
        ),
    ),
    "FWT003": (
        RuleConstraint(
            name="critical tested roles",
            description="Internal roles that require focused tests",
            values=("_state", "_api", "_resources", "_adapters"),
        ),
    ),
    "FWT004": (
        RuleConstraint(
            name="integration test scopes",
            description="Test path scopes accepted as integration or browser coverage",
            values=("integration", "e2e"),
        ),
    ),
    "FWN004": (
        RuleConstraint(
            name="iterator return types",
            description="Return type families accepted for iterator naming contracts",
            values=("Iterator", "Iterable", "Generator"),
        ),
    ),
}
_UI_KIT_CONFIGURATION_RULES: frozenset[str] = frozenset(
    {
        "FWA003",
        "FWL102",
        "FWL103",
        "FWR001",
        "FWR002",
        "FWR003",
        "FWR201",
        "FWR304",
        "FWR310",
        "FWR401",
        "FWR403",
        "FWR404",
        "FWR405",
        "FWR501",
        "FWS106",
    }
)
_NAMING_RULES: frozenset[str] = frozenset({"FWN001", "FWN002", "FWN003", "FWN004"})
_BASE_CONFIGURATION_INPUTS: tuple[str, ...] = ("generated", "roots", "tests", "tooling")
_NAMING_CONFIGURATION_INPUTS: tuple[str, ...] = ("contracts", *_BASE_CONFIGURATION_INPUTS)
_UI_KIT_CONFIGURATION_INPUTS: tuple[str, ...] = (*_BASE_CONFIGURATION_INPUTS, "ui_kit")
_NAMING_UI_KIT_CONFIGURATION_INPUTS: tuple[str, ...] = (
    "contracts",
    *_BASE_CONFIGURATION_INPUTS,
    "ui_kit",
)
_RETAINED_RULE_CODES: tuple[str, ...] = tuple(map(itemgetter(0), _RULE_DETAILS))
_CONFIGURATION_INPUTS: Mapping[str, tuple[str, ...]] = (
    dict.fromkeys(_RETAINED_RULE_CODES, _BASE_CONFIGURATION_INPUTS)
    | dict.fromkeys(_NAMING_RULES, _NAMING_CONFIGURATION_INPUTS)
    | dict.fromkeys(_UI_KIT_CONFIGURATION_RULES, _UI_KIT_CONFIGURATION_INPUTS)
    | dict.fromkeys(
        _NAMING_RULES & _UI_KIT_CONFIGURATION_RULES,
        _NAMING_UI_KIT_CONFIGURATION_INPUTS,
    )
)
_CONTRACT_BEHAVIORS: dict[str, tuple[str, ...]] = {
    "FWN001": ("returns-bool",),
    "FWN002": ("no-return",),
    "FWN003": ("returns-value",),
    "FWN004": ("returns-iterator",),
}


def _web_rules() -> tuple[RuleSpec, ...]:
    return tuple(
        RuleSpec(
            code=code,
            family=family,
            slug=slug,
            message=message,
            remediation=remediation,
            analyzers=_ANALYZERS,
            execution_owner=(
                ExecutionOwner.PROJECT if code in _PROJECT_RULES else ExecutionOwner.FILE
            ),
            thresholds=_THRESHOLDS.get(code, ()),
            constraints=_CONSTRAINTS.get(code, ()),
            configuration_inputs=_CONFIGURATION_INPUTS[code],
            contract_behaviors=_CONTRACT_BEHAVIORS.get(code, ()),
        )
        for code, family, slug, message, remediation in _RULE_DETAILS
    )


def web_rule_migration() -> tuple[_WebRuleMigration, ...]:
    """Return the complete immutable legacy web-policy classification."""

    return _WEB_RULE_MIGRATION


def web_rules() -> tuple[RuleSpec, ...]:
    """Return retained native web catalogue entries."""

    return _web_rules()
