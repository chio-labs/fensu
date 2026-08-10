"""Shipped configuration defaults: thresholds, role vocabulary, and entry caps."""

from __future__ import annotations

import re

from fensu.config.types import AnalyzerId, ContractBehavior, RuleSelector, TestLayout
from fensu.discovery.types import RoleName
from fensu.rules.authoring.types import Threshold

DEFAULT_THRESHOLDS: dict[Threshold, int] = {
    Threshold.MAX_STATEMENTS: 40,
    Threshold.MAX_DISTINCT_CALLS: 20,
    Threshold.MAX_LOCALS: 20,
    Threshold.MAX_FILE_LINES: 2000,
    Threshold.MAX_HELPERS_CONTAINER_MODULES: 10,
    Threshold.MAX_MAIN_CONTAINER_MODULES: 20,
    Threshold.MAX_ROLE_DEPTH: 1,
    Threshold.MAX_POSITIONAL_ARGS: 1,
    Threshold.MAX_ARGUMENTS: 10,
    Threshold.MAX_STATEMENTS_GLOBAL: 70,
    Threshold.MAX_SCRIPT_ENTRYPOINT_LINES: 80,
    Threshold.MIN_SHARED_DOMAIN_PREFIX_PACKAGES: 2,
    Threshold.MIN_CUSTOM_RULE_TEST_CASES: 1,
    Threshold.MAX_IMPORTED_BINDINGS: 20,
    Threshold.MAX_PUBLIC_EXPORTS: 20,
    Threshold.MAX_ROUTE_SCRIPT_LINES: 200,
    Threshold.MAX_COMPONENT_SCRIPT_LINES: 250,
    Threshold.MAX_STATE_LINES: 300,
    Threshold.MAX_STATE_PUBLIC_MEMBERS: 20,
    Threshold.MAX_STATE_CELLS: 15,
    Threshold.MAX_TOTAL_RUNES: 20,
    Threshold.MAX_STATE_FUNCTIONS: 15,
    Threshold.MAX_RESOURCE_FAMILIES: 1,
    Threshold.MAX_API_LINES: 200,
    Threshold.MAX_API_EXPORTS: 3,
}
MAX_THRESHOLD_VALUE: int = 2**32 - 1

DEFAULT_ROLE_FILE_NAMES: frozenset[str] = frozenset(
    {"models.py", "types.py", "constants.py", "exceptions.py"}
)

DEFAULT_TEST_PATHS: tuple[str, ...] = ("tests",)
DEFAULT_TEST_SCOPES: tuple[str, ...] = ("unit", "integration", "e2e")
DEFAULT_TEST_LAYOUT: TestLayout = TestLayout.MIRRORED
TEST_SCOPE_PATTERN: re.Pattern[str] = re.compile(r"^[a-z][a-z0-9]*(?:[_-][a-z0-9]+)*$")
DEFAULT_TOOLING_PATHS: tuple[str, ...] = ()
DEFAULT_SELECT: tuple[str, ...] = (RuleSelector.ALL,)
DEFAULT_WEB_SELECT: tuple[str, ...] = ("FW",)
DEFAULT_WARN: tuple[str, ...] = ()
DEFAULT_IGNORE: tuple[str, ...] = ()
DEFAULT_CACHE_ENABLED: bool = True
CACHE_ENABLED_CONFIG_KEY: str = "enabled"
CACHE_REQUIRE_CACHEABLE_CONFIG_KEY: str = "require_cacheable"
SKILLS_NAME_CONFIG_KEY: str = "name"
DEFAULT_CACHE_REQUIRE_CACHEABLE: bool = False
PYTHON_ANALYZER: AnalyzerId = AnalyzerId.PYTHON
DEFAULT_TARGET_ROOT: str = "."
TARGET_CONFIG_KEYS: frozenset[str] = frozenset({"analyzer", "root"})
TARGETS_CONFIG_KEY: str = "targets"
SELECT_CONFIG_KEY: str = "select"

CONFIG_TOP_LEVEL_KEYS: frozenset[str] = frozenset(
    {
        "roots",
        "tests",
        "test_scopes",
        "test_layout",
        "tooling",
        "generated",
        "select",
        "warn",
        "ignore",
        "rule_paths",
        "rule_modules",
        "rule_packs",
        "rule_options",
        "thresholds",
        "roles",
        "contracts",
        "ui_kit",
        "framework",
        "shadcn",
        "openapi",
        "rule_exceptions",
        "rule_ignores",
        "threshold_overrides",
        "cache",
        "evaluation",
        "skills",
    }
)
CONFIG_ROLE_NAMES: frozenset[str] = frozenset(RoleName)
CONTRACT_BEHAVIORS: frozenset[str] = frozenset(ContractBehavior)
RULE_CONFIGURATION_INPUTS: frozenset[str] = frozenset(
    {
        "contracts",
        "framework",
        "generated",
        "openapi",
        "roots",
        "shadcn",
        "tests",
        "test_scopes",
        "test_layout",
        "tooling",
        "ui_kit",
    }
)
DEFAULT_CONTRACTS: dict[str, str] = {
    "validate_*": ContractBehavior.NO_RETURN,
    "enforce_*": ContractBehavior.NO_RETURN,
    "is_*": ContractBehavior.RETURNS_BOOL,
    "has_*": ContractBehavior.RETURNS_BOOL,
    "can_*": ContractBehavior.RETURNS_BOOL,
    "supports_*": ContractBehavior.RETURNS_BOOL,
    "get_*": ContractBehavior.RETURNS_VALUE,
    "to_*": ContractBehavior.RETURNS_VALUE,
    "as_*": ContractBehavior.RETURNS_VALUE,
    "iter_*": ContractBehavior.RETURNS_ITERATOR,
}
WEB_DEFAULT_CONTRACTS: dict[str, str] = {
    "should_*": ContractBehavior.RETURNS_BOOL,
    "iterate_*": ContractBehavior.RETURNS_ITERATOR,
}

MAX_ENTRY_PUBLIC_FUNCTIONS: int = 1
MAX_ENTRY_PRIVATE_FUNCTIONS: int = 2
PATH_SEPARATOR: str = "/"
DOUBLE_PATH_SEPARATOR: str = "//"
INVALID_UI_KIT_PATH_PARTS: frozenset[str] = frozenset({"", ".", ".."})
DEFAULT_WEB_FRAMEWORK: str = "sveltekit"
SINGLE_COMPONENT_GLOB: str = "*"
RECURSIVE_GLOB: str = "**"
THRESHOLD_OVERRIDE_KEYS: frozenset[str] = frozenset({"paths", "thresholds", "reason"})
RULE_IGNORE_KEYS: frozenset[str] = frozenset({"rules", "paths", "reason"})
EVALUATION_CONFIG_KEYS: frozenset[str] = frozenset({"include", "exclude"})
SKILLS_CONFIG_KEYS: frozenset[str] = frozenset({SKILLS_NAME_CONFIG_KEY})
RULE_EXCEPTION_SYMBOLS_CONFIG_KEY: str = "symbols"
