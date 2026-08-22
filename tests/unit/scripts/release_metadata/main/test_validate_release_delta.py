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
    **{path: f'name = "fixture"\nversion = "{OLD_VERSION}"\n' for path in VERSION_PATHS},
    CHANGELOG_PATH: "# Changelog\n\n## [0.11.0]\n",
}
VALID_HEAD_FILES: dict[str, str] = {
    **{path: content.replace(OLD_VERSION, NEW_VERSION) for path, content in BASE_FILES.items()},
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
    ],
    ids=lambda case: case.description,
)
def test_given_release_delta_when_validating_then_returns_expected_errors(
    test_case: ReleaseDeltaTestCase,
) -> None:
    assert get_release_delta_errors(test_case.delta) == test_case.expected_errors


if __name__ == "__main__":
    pytest.main([__file__, "-vv"])
