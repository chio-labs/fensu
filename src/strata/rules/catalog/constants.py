"""Rule catalogue constants."""

from __future__ import annotations

from strata.rules.annotations.constants import SFA_RULES
from strata.rules.authoring.models import RuleSpec
from strata.rules.hygiene.constants import SFH_RULES
from strata.rules.layers.constants import SFL_RULES
from strata.rules.naming.constants import SFN_RULES
from strata.rules.roles.constants import SFR_RULES
from strata.rules.shape.constants import SFS_RULES
from strata.rules.tests.constants import SFT_RULES

CORE_RULES: tuple[RuleSpec, ...] = (
    *SFA_RULES,
    *SFL_RULES,
    *SFH_RULES,
    *SFS_RULES,
    *SFT_RULES,
    *SFR_RULES,
    *SFN_RULES,
)
STRATA_PACKAGE_NAME: str = "strata"
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
