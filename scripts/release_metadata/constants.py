"""Files permitted to change on a generated release branch."""

CHANGELOG_PATH: str = "CHANGELOG.md"
VERSION_PATHS: tuple[str, ...] = (
    ".release-please-manifest.json",
    "pyproject.toml",
    "packages/fensu-cli/pyproject.toml",
    "crates/fensu-cli/Cargo.toml",
    "crates/fensu-policy/Cargo.toml",
    "crates/fensu-structure-checker/Cargo.toml",
    "uv.lock",
    "Cargo.lock",
)
ALLOWED_PATHS: frozenset[str] = frozenset((*VERSION_PATHS, CHANGELOG_PATH))
