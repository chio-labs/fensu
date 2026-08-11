"""Rule catalogue constants."""

from __future__ import annotations

from fensu.rules.annotations.constants import FFA_RULES
from fensu.rules.authoring.models import RuleSpec
from fensu.rules.catalog._helpers.web_rules import (
    sveltekit_rules,
    typescript_rules,
    web_rule_migration,
)
from fensu.rules.dagster.constants import FPDG_RULES
from fensu.rules.hygiene.constants import FFH_RULES
from fensu.rules.layers.constants import FFL_RULES
from fensu.rules.naming.constants import FFN_RULES
from fensu.rules.roles.constants import FFR_RULES
from fensu.rules.shape.constants import FFS_RULES
from fensu.rules.tests.constants import FFT_RULES

WEB_RULE_MIGRATION: tuple[tuple[str, str, bool, str], ...] = web_rule_migration()
FPTS_RULES: tuple[RuleSpec, ...] = typescript_rules()
FPSK_RULES: tuple[RuleSpec, ...] = sveltekit_rules()

CORE_RULES: tuple[RuleSpec, ...] = (
    *FFA_RULES,
    *FFL_RULES,
    *FFH_RULES,
    *FFS_RULES,
    *FFT_RULES,
    *FFR_RULES,
    *FFN_RULES,
)
SHIPPED_RULES: tuple[RuleSpec, ...] = (*CORE_RULES, *FPDG_RULES, *FPTS_RULES, *FPSK_RULES)
FENSU_PACKAGE_NAME: str = "fensu"
TRACKED_FACADE_ATTRIBUTE: str = "project"
MODULE_PARAMETER_NAME: str = "module"
CACHEABLE_ALLOWED_IMPORT_ROOTS: frozenset[str] = frozenset(
    {
        "__future__",
        "abc",
        "ast",
        "bisect",
        "collections",
        "copy",
        "dataclasses",
        "decimal",
        "enum",
        "fractions",
        "functools",
        "graphlib",
        "heapq",
        "itertools",
        "keyword",
        "math",
        "numbers",
        "operator",
        "pathlib",
        "re",
        "statistics",
        "string",
        "textwrap",
        "types",
        "typing",
        "unicodedata",
    }
)
CACHEABLE_BANNED_BUILTIN_CALLS: frozenset[str] = frozenset(
    {"__import__", "eval", "exec", "input", "open"}
)
CACHEABLE_UNTRACKED_OPERATION_ATTRIBUTES: frozenset[str] = frozenset(
    {
        "absolute",
        "chmod",
        "cwd",
        "exists",
        "expanduser",
        "glob",
        "hardlink_to",
        "home",
        "is_dir",
        "is_file",
        "is_mount",
        "is_symlink",
        "iterdir",
        "lstat",
        "mkdir",
        "open",
        "owner",
        "read_bytes",
        "read_text",
        "readlink",
        "rename",
        "resolve",
        "rglob",
        "rmdir",
        "samefile",
        "stat",
        "symlink_to",
        "touch",
        "unlink",
        "walk",
        "write_bytes",
        "write_text",
    }
)
