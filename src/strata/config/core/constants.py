"""Shipped configuration defaults: thresholds, role vocabulary, and entry caps."""

from __future__ import annotations

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
}

DEFAULT_ROLE_DIR_NAMES: frozenset[str] = frozenset({"main", "helpers", "classes"})
DEFAULT_ROLE_FILE_NAMES: frozenset[str] = frozenset(
    {"models.py", "types.py", "constants.py", "exceptions.py"}
)

DEFAULT_TEST_PATHS: tuple[str, ...] = ("tests",)
DEFAULT_TOOLING_PATHS: tuple[str, ...] = ()
DEFAULT_SELECT: tuple[str, ...] = ("SF",)
DEFAULT_IGNORE: tuple[str, ...] = ()

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
    }
)
CONFIG_ROLE_NAMES: frozenset[str] = frozenset(
    {"entry", "main", "helpers", "classes", "models", "types", "constants", "exceptions"}
)
CONTRACT_BEHAVIORS: frozenset[str] = frozenset({"no-return"})
DEFAULT_CONTRACTS: dict[str, str] = {"validate_*": "no-return", "enforce_*": "no-return"}

MAX_ENTRY_PUBLIC_FUNCTIONS: int = 1
MAX_ENTRY_PRIVATE_FUNCTIONS: int = 2
