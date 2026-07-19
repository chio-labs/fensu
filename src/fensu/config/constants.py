"""Shipped configuration defaults: thresholds, role vocabulary, and entry caps."""

from __future__ import annotations

from fensu.config.types import ContractBehavior, RuleSelector
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
}

DEFAULT_ROLE_FILE_NAMES: frozenset[str] = frozenset(
    {"models.py", "types.py", "constants.py", "exceptions.py"}
)

DEFAULT_TEST_PATHS: tuple[str, ...] = ("tests",)
DEFAULT_TOOLING_PATHS: tuple[str, ...] = ()
DEFAULT_SELECT: tuple[str, ...] = (RuleSelector.ALL,)
DEFAULT_WARN: tuple[str, ...] = ()
DEFAULT_IGNORE: tuple[str, ...] = ()
DEFAULT_CACHE_ENABLED: bool = True
CACHE_ENABLED_CONFIG_KEY: str = "enabled"
CACHE_REQUIRE_CACHEABLE_CONFIG_KEY: str = "require_cacheable"
DEFAULT_EXPERIMENTAL_MEMORY: bool = False
DEFAULT_MEMORY_TASKS_ARCHIVE_AFTER_DAYS: int = 7
EXPERIMENTAL_MEMORY_CONFIG_KEY: str = "memory"
MEMORY_TASKS_CONFIG_KEY: str = "tasks"
MEMORY_TASKS_ARCHIVE_AFTER_DAYS_CONFIG_KEY: str = "archive_after_days"
SKILLS_NAME_CONFIG_KEY: str = "name"
DEFAULT_CACHE_REQUIRE_CACHEABLE: bool = False

CONFIG_TOP_LEVEL_KEYS: frozenset[str] = frozenset(
    {
        "roots",
        "tests",
        "tooling",
        "select",
        "warn",
        "ignore",
        "rule_paths",
        "rule_modules",
        "thresholds",
        "roles",
        "contracts",
        "rule_exceptions",
        "threshold_overrides",
        "cache",
        "experimental",
        "memory",
        "evaluation",
        "skills",
    }
)
CONFIG_ROLE_NAMES: frozenset[str] = frozenset(RoleName)
CONTRACT_BEHAVIORS: frozenset[str] = frozenset(ContractBehavior)
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

MAX_ENTRY_PUBLIC_FUNCTIONS: int = 1
MAX_ENTRY_PRIVATE_FUNCTIONS: int = 2
PATH_SEPARATOR: str = "/"
DOUBLE_PATH_SEPARATOR: str = "//"
SINGLE_COMPONENT_GLOB: str = "*"
RECURSIVE_GLOB: str = "**"
THRESHOLD_OVERRIDE_KEYS: frozenset[str] = frozenset({"paths", "thresholds", "reason"})
EVALUATION_CONFIG_KEYS: frozenset[str] = frozenset({"include", "exclude"})
MEMORY_CONFIG_KEYS: frozenset[str] = frozenset({MEMORY_TASKS_CONFIG_KEY})
MEMORY_TASKS_CONFIG_KEYS: frozenset[str] = frozenset({MEMORY_TASKS_ARCHIVE_AFTER_DAYS_CONFIG_KEY})
SKILLS_CONFIG_KEYS: frozenset[str] = frozenset({SKILLS_NAME_CONFIG_KEY})
RULE_EXCEPTION_SYMBOLS_CONFIG_KEY: str = "symbols"
