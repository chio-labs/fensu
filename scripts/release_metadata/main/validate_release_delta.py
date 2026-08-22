"""Validate that a release branch contains generated version metadata only."""

from scripts.release_metadata.constants import ALLOWED_PATHS, CHANGELOG_PATH, VERSION_PATHS
from scripts.release_metadata.models import ReleaseDelta


def get_release_delta_errors(delta: ReleaseDelta) -> list[str]:
    """Return every unsafe or inconsistent release delta."""

    errors: list[str] = []
    unexpected: list[str] = sorted(delta.changed_paths - ALLOWED_PATHS)
    if unexpected:
        errors.append(f"unexpected release files: {', '.join(unexpected)}")
    if delta.old_version == delta.new_version:
        errors.append("release version did not change")
    for path in VERSION_PATHS:
        expected: str = delta.base_files[path].replace(delta.old_version, delta.new_version)
        if delta.head_files[path] != expected:
            errors.append(f"{path} contains changes beyond the release version substitution")
    changelog: str = delta.head_files[CHANGELOG_PATH]
    base_history: str = delta.base_files[CHANGELOG_PATH].partition("\n\n")[2]
    if not changelog.startswith("# Changelog\n\n") or base_history not in changelog:
        errors.append("CHANGELOG.md rewrites existing release history")
    if f"## [{delta.new_version}]" not in changelog:
        errors.append(f"CHANGELOG.md has no {delta.new_version} release heading")
    return errors
