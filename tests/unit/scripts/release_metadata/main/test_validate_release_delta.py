"""Generated release metadata validation behavior."""

from __future__ import annotations

import pytest

from scripts.release_metadata.constants import CHANGELOG_PATH, VERSION_PATHS
from scripts.release_metadata.main.validate_release_delta import get_release_delta_errors
from scripts.release_metadata.models import ReleaseDelta
from tests.unit.scripts.release_metadata.main._test_types import ReleaseDeltaTestCase

OLD_VERSION: str = "0.11.0"
NEW_VERSION: str = "0.12.0"
BASE_FILES: dict[str, str] = {
    ".release-please-manifest.json": f'{{".": "{OLD_VERSION}"}}',
    "pyproject.toml": (
        f'[project]\nname = "fensu"\nversion = "{OLD_VERSION}"\n'
        f'dependencies = ["fensu-cli=={OLD_VERSION}", "third-party=={OLD_VERSION}"]\n'
    ),
    "packages/fensu-cli/pyproject.toml": (
        f'[project]\nname = "fensu-cli"\nversion = "{OLD_VERSION}" # x-release-please-version\n'
    ),
    "crates/fensu-cli/Cargo.toml": (f'[package]\nname = "fensu-cli"\nversion = "{OLD_VERSION}"\n'),
    "crates/fensu-policy/Cargo.toml": (
        f'[package]\nname = "fensu-policy"\nversion = "{OLD_VERSION}"\n'
    ),
    "uv.lock": (
        "version = 1\n"
        f'[[package]]\nname = "fensu"\nversion = "{OLD_VERSION}"\n'
        f'[[package]]\nname = "fensu-cli"\nversion = "{OLD_VERSION}"\n'
        f'[[package]]\nname = "third-party"\nversion = "{OLD_VERSION}"\n'
    ),
    "Cargo.lock": (
        "version = 4\n"
        f'[[package]]\nname = "fensu-cli"\nversion = "{OLD_VERSION}"\n'
        f'[[package]]\nname = "fensu-policy"\nversion = "{OLD_VERSION}"\n'
        f'[[package]]\nname = "third-party"\nversion = "{OLD_VERSION}"\n'
    ),
    CHANGELOG_PATH: "# Changelog\n\n## [0.11.0]\n",
}
VALID_HEAD_FILES: dict[str, str] = {
    ".release-please-manifest.json": f'{{".": "{NEW_VERSION}"}}',
    "pyproject.toml": BASE_FILES["pyproject.toml"]
    .replace(f'version = "{OLD_VERSION}"', f'version = "{NEW_VERSION}"', 1)
    .replace(f"fensu-cli=={OLD_VERSION}", f"fensu-cli=={NEW_VERSION}"),
    "packages/fensu-cli/pyproject.toml": BASE_FILES["packages/fensu-cli/pyproject.toml"].replace(
        OLD_VERSION, NEW_VERSION
    ),
    "crates/fensu-cli/Cargo.toml": BASE_FILES["crates/fensu-cli/Cargo.toml"].replace(
        OLD_VERSION, NEW_VERSION
    ),
    "crates/fensu-policy/Cargo.toml": BASE_FILES["crates/fensu-policy/Cargo.toml"].replace(
        OLD_VERSION, NEW_VERSION
    ),
    "uv.lock": BASE_FILES["uv.lock"]
    .replace(
        f'name = "fensu"\nversion = "{OLD_VERSION}"', f'name = "fensu"\nversion = "{NEW_VERSION}"'
    )
    .replace(
        f'name = "fensu-cli"\nversion = "{OLD_VERSION}"',
        f'name = "fensu-cli"\nversion = "{NEW_VERSION}"',
    ),
    "Cargo.lock": BASE_FILES["Cargo.lock"]
    .replace(
        f'name = "fensu-cli"\nversion = "{OLD_VERSION}"',
        f'name = "fensu-cli"\nversion = "{NEW_VERSION}"',
    )
    .replace(
        f'name = "fensu-policy"\nversion = "{OLD_VERSION}"',
        f'name = "fensu-policy"\nversion = "{NEW_VERSION}"',
    ),
    CHANGELOG_PATH: "# Changelog\n\n## [0.12.0]\n\n## [0.11.0]\n",
}


@pytest.mark.parametrize(
    "test_case",
    [
        ReleaseDeltaTestCase(
            description="generated version and changelog metadata",
            delta=ReleaseDelta(
                old_version=OLD_VERSION,
                new_version=NEW_VERSION,
                changed_paths=frozenset((*VERSION_PATHS, CHANGELOG_PATH)),
                base_files=BASE_FILES,
                head_files=VALID_HEAD_FILES,
            ),
            expected_errors=[],
        ),
        ReleaseDeltaTestCase(
            description="manifest dependency tampering",
            delta=ReleaseDelta(
                old_version=OLD_VERSION,
                new_version=NEW_VERSION,
                changed_paths=frozenset((*VERSION_PATHS, CHANGELOG_PATH)),
                base_files=BASE_FILES,
                head_files={
                    **VALID_HEAD_FILES,
                    "pyproject.toml": VALID_HEAD_FILES["pyproject.toml"]
                    + 'dependencies = ["unreviewed"]\n',
                },
            ),
            expected_errors=[
                "pyproject.toml contains changes beyond the release version substitution"
            ],
        ),
        ReleaseDeltaTestCase(
            description="release annotation removal",
            delta=ReleaseDelta(
                old_version=OLD_VERSION,
                new_version=NEW_VERSION,
                changed_paths=frozenset((*VERSION_PATHS, CHANGELOG_PATH)),
                base_files=BASE_FILES,
                head_files={
                    **VALID_HEAD_FILES,
                    "packages/fensu-cli/pyproject.toml": VALID_HEAD_FILES[
                        "packages/fensu-cli/pyproject.toml"
                    ].replace(" # x-release-please-version", ""),
                },
            ),
            expected_errors=[
                "packages/fensu-cli/pyproject.toml contains changes beyond the release version substitution"
            ],
        ),
        ReleaseDeltaTestCase(
            description="lockfile dependency tampering",
            delta=ReleaseDelta(
                old_version=OLD_VERSION,
                new_version=NEW_VERSION,
                changed_paths=frozenset((*VERSION_PATHS, CHANGELOG_PATH)),
                base_files=BASE_FILES,
                head_files={
                    **VALID_HEAD_FILES,
                    "Cargo.lock": VALID_HEAD_FILES["Cargo.lock"]
                    + 'name = "unreviewed"\nversion = "9.9.9"\n',
                },
            ),
            expected_errors=["Cargo.lock contains changes beyond the release version substitution"],
        ),
        ReleaseDeltaTestCase(
            description="unexpected executable file",
            delta=ReleaseDelta(
                old_version=OLD_VERSION,
                new_version=NEW_VERSION,
                changed_paths=frozenset((*VERSION_PATHS, CHANGELOG_PATH, "src/fensu/backdoor.py")),
                base_files=BASE_FILES,
                head_files=VALID_HEAD_FILES,
            ),
            expected_errors=["unexpected release files: src/fensu/backdoor.py"],
        ),
        ReleaseDeltaTestCase(
            description="version downgrade",
            delta=ReleaseDelta(
                old_version=NEW_VERSION,
                new_version=OLD_VERSION,
                changed_paths=frozenset((*VERSION_PATHS, CHANGELOG_PATH)),
                base_files=VALID_HEAD_FILES,
                head_files={
                    **BASE_FILES,
                    CHANGELOG_PATH: ("# Changelog\n\n## [0.11.0]\n\n## [0.12.0]\n\n## [0.11.0]\n"),
                },
            ),
            expected_errors=["release version must be a forward MAJOR.MINOR.PATCH transition"],
        ),
        ReleaseDeltaTestCase(
            description="stale lockfiles before trusted refresh",
            delta=ReleaseDelta(
                old_version=OLD_VERSION,
                new_version=NEW_VERSION,
                changed_paths=frozenset(
                    path
                    for path in (*VERSION_PATHS, CHANGELOG_PATH)
                    if path not in {"uv.lock", "Cargo.lock"}
                ),
                base_files=BASE_FILES,
                head_files={
                    **VALID_HEAD_FILES,
                    "uv.lock": BASE_FILES["uv.lock"],
                    "Cargo.lock": BASE_FILES["Cargo.lock"],
                },
            ),
            expected_errors=[],
            allow_stale_lockfiles=True,
        ),
        ReleaseDeltaTestCase(
            description="stale lockfiles after trusted refresh",
            delta=ReleaseDelta(
                old_version=OLD_VERSION,
                new_version=NEW_VERSION,
                changed_paths=frozenset(
                    path
                    for path in (*VERSION_PATHS, CHANGELOG_PATH)
                    if path not in {"uv.lock", "Cargo.lock"}
                ),
                base_files=BASE_FILES,
                head_files={
                    **VALID_HEAD_FILES,
                    "uv.lock": BASE_FILES["uv.lock"],
                    "Cargo.lock": BASE_FILES["Cargo.lock"],
                },
            ),
            expected_errors=[
                "uv.lock contains changes beyond the release version substitution",
                "Cargo.lock contains changes beyond the release version substitution",
            ],
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_release_delta_when_validating_then_returns_expected_errors(
    test_case: ReleaseDeltaTestCase,
) -> None:
    assert (
        get_release_delta_errors(
            delta=test_case.delta,
            allow_stale_lockfiles=test_case.allow_stale_lockfiles,
        )
        == test_case.expected_errors
    )


if __name__ == "__main__":
    pytest.main([__file__, "-vv"])
