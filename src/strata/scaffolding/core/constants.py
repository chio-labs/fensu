"""Names and path policies used by deterministic layout detection."""

from __future__ import annotations

PYPROJECT_FILE_NAME: str = "pyproject.toml"
PYTHON_FILE_SUFFIX: str = ".py"
PACKAGE_MARKER_FILE_NAME: str = "__init__.py"
PARENT_PATH_PART: str = ".."
CURRENT_PATH_TEXT: str = "."
WORKSPACE_WILDCARD: str = "*"
DEFAULT_TEST_PATH: str = "tests"
CONFIG_FILE_NAME: str = "strata.toml"
CONFIG_TEMP_PREFIX: str = ".strata.toml."
CONFIG_TEMP_SUFFIX: str = ".tmp"
GITIGNORE_FILE_NAME: str = ".gitignore"
POSIX_PATH_SEPARATOR: str = "/"
GLOBSTAR_PATTERN: str = "**"
DEFAULT_SOURCE_PATH: str = "src"
ADOPTION_LINK: str = "docs.stratalint.com/adoption"
MAX_INVALID_ATTEMPTS: int = 3
YES_RESPONSE: str = "y"
NO_RESPONSE: str = "n"
EDIT_RESPONSE: str = "e"
END_OF_INPUT: str = ""
END_OF_INPUT_LABEL: str = "<EOF>"
TEST_MARKER_PATH: str = "tests/.gitkeep"
CANDIDATE_PATH_WIDTH: int = 14
DRIFT_FAMILY_NAME_WIDTH: int = 11
FULL_SELECT: tuple[str, ...] = ("SF",)
GRADUAL_SELECT: tuple[str, ...] = ("SFL", "SFX", "SFA", "SFN")
FAMILY_LABELS: tuple[tuple[str, str], ...] = (
    ("SFA", "annotations"),
    ("SFL", "layers"),
    ("SFX", "hygiene"),
    ("SFN", "naming"),
    ("SFR", "roles"),
    ("SFS", "shape"),
    ("SFT", "tests"),
)
TEST_DIRECTORY_NAMES: tuple[str, ...] = ("tests", "test")
TOOLING_DIRECTORY_NAMES: tuple[str, ...] = ("scripts", "tools", "bin", "tasks")
SOURCE_CONTAINER_NAMES: tuple[str, ...] = ("src", "lib", "libs", "python")
EXCLUDED_DIRECTORY_NAMES: frozenset[str] = frozenset(
    {
        ".cache",
        ".git",
        ".hg",
        ".mypy_cache",
        ".nox",
        ".pytest_cache",
        ".ruff_cache",
        ".svn",
        ".tox",
        ".venv",
        "__pycache__",
        "bin",
        "build",
        "dist",
        "docs",
        "env",
        "examples",
        "htmlcov",
        "node_modules",
        "scripts",
        "site-packages",
        "tasks",
        "test",
        "tests",
        "tools",
        "venv",
    }
)
