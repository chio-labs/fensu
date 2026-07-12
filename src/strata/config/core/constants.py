"""Shipped configuration defaults: thresholds, role vocabulary, and entry caps."""

from __future__ import annotations

from strata.config.core.types import ContractBehavior, RuleSelector
from strata.discovery.core.types import RoleName
from strata.rules.authoring.types import Threshold

DEFAULT_THRESHOLDS: dict[Threshold, int] = {
    Threshold.MAX_STATEMENTS: 40,
    Threshold.MAX_DISTINCT_CALLS: 20,
    Threshold.MAX_LOCALS: 20,
    Threshold.MAX_FILE_LINES: 2000,
    Threshold.MAX_FLAT_HELPER_MODULES: 10,
    Threshold.MAX_FLAT_MAIN_MODULES: 20,
    Threshold.MAX_POSITIONAL_ARGS: 0,
    Threshold.MAX_ARGUMENTS: 10,
    Threshold.MAX_STATEMENTS_GLOBAL: 70,
    Threshold.MAX_SCRIPT_ENTRYPOINT_LINES: 80,
}

DEFAULT_ROLE_DIR_NAMES: frozenset[str] = frozenset(
    {RoleName.MAIN, RoleName.HELPERS, RoleName.CLASSES}
)
DEFAULT_ROLE_FILE_NAMES: frozenset[str] = frozenset(
    {"models.py", "types.py", "constants.py", "exceptions.py"}
)

DEFAULT_TEST_PATHS: tuple[str, ...] = ("tests",)
DEFAULT_TOOLING_PATHS: tuple[str, ...] = ()
DEFAULT_SELECT: tuple[str, ...] = (RuleSelector.ALL,)
DEFAULT_IGNORE: tuple[str, ...] = ()
DEFAULT_CACHE_ENABLED: bool = True
CACHE_ENABLED_CONFIG_KEY: str = "enabled"

CONFIG_TOP_LEVEL_KEYS: frozenset[str] = frozenset(
    {
        "roots",
        "tests",
        "tooling",
        "select",
        "ignore",
        "rule_paths",
        "rule_modules",
        "thresholds",
        "roles",
        "contracts",
        "rule_exceptions",
        "cache",
    }
)
CONFIG_ROLE_NAMES: frozenset[str] = frozenset(RoleName)
CONTRACT_BEHAVIORS: frozenset[str] = frozenset(ContractBehavior)
DEFAULT_CONTRACTS: dict[str, str] = {
    "validate_*": ContractBehavior.NO_RETURN,
    "enforce_*": ContractBehavior.NO_RETURN,
}

MAX_ENTRY_PUBLIC_FUNCTIONS: int = 1
MAX_ENTRY_PRIVATE_FUNCTIONS: int = 2
