"""Semantic release version and metadata comparison."""

from __future__ import annotations

import copy
import json
import re
import tomllib
from typing import Any

from scripts.release_metadata.constants import (
    CARGO_LOCK_PATH,
    CLI_PROJECT_PATH,
    NORMALIZED_VERSION,
    OWNED_CARGO_PACKAGES,
    OWNED_UV_PACKAGES,
    RELEASE_MANIFEST_PATH,
    ROOT_PROJECT_PATH,
    SEMVER_PART_COUNT,
    UV_LOCK_PATH,
)
from scripts.release_metadata.models import ReleaseDelta


def is_forward_semver(*, old_version: str, new_version: str) -> bool:
    """Return whether two plain semantic versions form a forward transition."""

    old_semver: tuple[int, int, int] | None = _parse_semver(value=old_version)
    new_semver: tuple[int, int, int] | None = _parse_semver(value=new_version)
    return old_semver is not None and new_semver is not None and new_semver > old_semver


def version_file_is_valid(
    *,
    path: str,
    delta: ReleaseDelta,
    allow_stale_lockfiles: bool,
) -> bool:
    """Compare one parsed metadata file after normalizing owned version fields."""

    try:
        semantic_valid: bool
        if path == RELEASE_MANIFEST_PATH:
            semantic_valid = _release_manifest_is_valid(delta=delta, path=path)
            return semantic_valid and _version_text_is_valid(
                path=path,
                delta=delta,
                allow_stale_lockfiles=allow_stale_lockfiles,
            )
        base: dict[str, Any] = tomllib.loads(delta.base_files[path])
        head: dict[str, Any] = tomllib.loads(delta.head_files[path])
        if path == ROOT_PROJECT_PATH:
            semantic_valid = _root_project_is_valid(base=base, head=head, delta=delta)
        elif path == CLI_PROJECT_PATH:
            semantic_valid = _manifest_is_valid(
                base=base,
                head=head,
                section="project",
                delta=delta,
            )
        elif path.startswith("crates/"):
            semantic_valid = _manifest_is_valid(
                base=base,
                head=head,
                section="package",
                delta=delta,
            )
        elif path == CARGO_LOCK_PATH:
            semantic_valid = _lock_is_valid(
                base=base,
                head=head,
                owned_packages=OWNED_CARGO_PACKAGES,
                delta=delta,
                allow_old=allow_stale_lockfiles,
            )
        elif path == UV_LOCK_PATH:
            semantic_valid = _lock_is_valid(
                base=base,
                head=head,
                owned_packages=OWNED_UV_PACKAGES,
                delta=delta,
                allow_old=allow_stale_lockfiles,
            )
        else:
            return False
        return semantic_valid and _version_text_is_valid(
            path=path,
            delta=delta,
            allow_stale_lockfiles=allow_stale_lockfiles,
        )
    except (KeyError, TypeError, ValueError, tomllib.TOMLDecodeError):
        return False
    return False


def _parse_semver(*, value: str) -> tuple[int, int, int] | None:
    parts: list[str] = value.split(".")
    if len(parts) != SEMVER_PART_COUNT or any(not part.isdigit() for part in parts):
        return None
    return (int(parts[0]), int(parts[1]), int(parts[2]))


def _release_manifest_is_valid(*, delta: ReleaseDelta, path: str) -> bool:
    base: dict[str, Any] = json.loads(delta.base_files[path])
    head: dict[str, Any] = json.loads(delta.head_files[path])
    base_normalized: dict[str, Any] | None = _normalized_field(
        document=base,
        section=None,
        field=".",
        expected=delta.old_version,
    )
    head_normalized: dict[str, Any] | None = _normalized_field(
        document=head,
        section=None,
        field=".",
        expected=delta.new_version,
    )
    return base_normalized is not None and base_normalized == head_normalized


def _manifest_is_valid(
    *,
    base: dict[str, Any],
    head: dict[str, Any],
    section: str,
    delta: ReleaseDelta,
) -> bool:
    base_normalized: dict[str, Any] | None = _normalized_field(
        document=base,
        section=section,
        field="version",
        expected=delta.old_version,
    )
    head_normalized: dict[str, Any] | None = _normalized_field(
        document=head,
        section=section,
        field="version",
        expected=delta.new_version,
    )
    return base_normalized is not None and base_normalized == head_normalized


def _root_project_is_valid(
    *,
    base: dict[str, Any],
    head: dict[str, Any],
    delta: ReleaseDelta,
) -> bool:
    base_normalized: dict[str, Any] | None = _normalized_field(
        document=base,
        section="project",
        field="version",
        expected=delta.old_version,
    )
    head_normalized: dict[str, Any] | None = _normalized_field(
        document=head,
        section="project",
        field="version",
        expected=delta.new_version,
    )
    if base_normalized is None or head_normalized is None:
        return False
    base_normalized = _normalized_cli_dependency(
        document=base_normalized,
        version=delta.old_version,
    )
    head_normalized = _normalized_cli_dependency(
        document=head_normalized,
        version=delta.new_version,
    )
    return base_normalized is not None and base_normalized == head_normalized


def _normalized_field(
    *,
    document: dict[str, Any],
    section: str | None,
    field: str,
    expected: str,
) -> dict[str, Any] | None:
    normalized: dict[str, Any] = copy.deepcopy(document)
    target: dict[str, Any] = normalized if section is None else normalized[section]
    if target.get(field) != expected:
        return None
    target[field] = NORMALIZED_VERSION
    return normalized


def _normalized_cli_dependency(
    *,
    document: dict[str, Any],
    version: str,
) -> dict[str, Any] | None:
    requirement: str = f"fensu-cli=={version}"
    dependencies: list[Any] = document["project"].get("dependencies", [])
    if dependencies.count(requirement) != 1:
        return None
    normalized: dict[str, Any] = copy.deepcopy(document)
    normalized["project"]["dependencies"] = [
        "fensu-cli==0.0.0" if item == requirement else item for item in dependencies
    ]
    return normalized


def _lock_is_valid(
    *,
    base: dict[str, Any],
    head: dict[str, Any],
    owned_packages: frozenset[str],
    delta: ReleaseDelta,
    allow_old: bool,
) -> bool:
    base_normalized: dict[str, Any] | None = _normalized_lock(
        document=base,
        owned_packages=owned_packages,
        allowed_versions=frozenset({delta.old_version}),
    )
    allowed_head: frozenset[str] = frozenset(
        {delta.old_version, delta.new_version} if allow_old else {delta.new_version}
    )
    head_normalized: dict[str, Any] | None = _normalized_lock(
        document=head,
        owned_packages=owned_packages,
        allowed_versions=allowed_head,
    )
    return base_normalized is not None and base_normalized == head_normalized


def _normalized_lock(
    *,
    document: dict[str, Any],
    owned_packages: frozenset[str],
    allowed_versions: frozenset[str],
) -> dict[str, Any] | None:
    normalized: dict[str, Any] = copy.deepcopy(document)
    found: set[str] = set()
    for package in normalized.get("package", []):
        if package.get("name") not in owned_packages:
            continue
        found.add(package["name"])
        if package.get("version") not in allowed_versions:
            return None
        package["version"] = NORMALIZED_VERSION
    return normalized if found == owned_packages else None


def _version_text_is_valid(
    *,
    path: str,
    delta: ReleaseDelta,
    allow_stale_lockfiles: bool,
) -> bool:
    base: str = delta.base_files[path]
    if path == RELEASE_MANIFEST_PATH:
        expected: str | None = _replace_once(
            value=base,
            pattern=rf'("\."\s*:\s*"){re.escape(delta.old_version)}(")',
            replacement=rf"\g<1>{delta.new_version}\g<2>",
        )
    elif path == ROOT_PROJECT_PATH:
        expected = _replace_manifest_version(
            value=base,
            section="project",
            old_version=delta.old_version,
            new_version=delta.new_version,
        )
        if expected is not None:
            expected = _replace_once(
                value=expected,
                pattern=re.escape(f"fensu-cli=={delta.old_version}"),
                replacement=f"fensu-cli=={delta.new_version}",
            )
    elif path == CLI_PROJECT_PATH:
        expected = _replace_manifest_version(
            value=base,
            section="project",
            old_version=delta.old_version,
            new_version=delta.new_version,
        )
    elif path.startswith("crates/"):
        expected = _replace_manifest_version(
            value=base,
            section="package",
            old_version=delta.old_version,
            new_version=delta.new_version,
        )
    elif path == CARGO_LOCK_PATH:
        expected = _replace_lock_versions(
            value=base,
            owned_packages=OWNED_CARGO_PACKAGES,
            old_version=delta.old_version,
            new_version=delta.new_version,
        )
    elif path == UV_LOCK_PATH:
        expected = _replace_lock_versions(
            value=base,
            owned_packages=OWNED_UV_PACKAGES,
            old_version=delta.old_version,
            new_version=delta.new_version,
        )
    else:
        return False
    if expected is None:
        return False
    head: str = delta.head_files[path]
    return head == expected or (
        allow_stale_lockfiles and path in {CARGO_LOCK_PATH, UV_LOCK_PATH} and head == base
    )


def _replace_manifest_version(
    *,
    value: str,
    section: str,
    old_version: str,
    new_version: str,
) -> str | None:
    return _replace_once(
        value=value,
        pattern=(
            rf'(?ms)(^\[{re.escape(section)}\]\s*$.*?^version\s*=\s*")'
            rf"{re.escape(old_version)}"
            r'("[^\n]*$)'
        ),
        replacement=rf"\g<1>{new_version}\g<2>",
    )


def _replace_lock_versions(
    *,
    value: str,
    owned_packages: frozenset[str],
    old_version: str,
    new_version: str,
) -> str | None:
    blocks: list[str] = re.split(r"(?=^\[\[package\]\]\s*$)", value, flags=re.MULTILINE)
    found: set[str] = set()
    for index, block in enumerate(blocks):
        name_match: re.Match[str] | None = re.search(r'^name\s*=\s*"([^"]+)"', block, re.MULTILINE)
        if name_match is None or name_match.group(1) not in owned_packages:
            continue
        found.add(name_match.group(1))
        replaced: str | None = _replace_once(
            value=block,
            pattern=rf'(?m)(^version\s*=\s*"){re.escape(old_version)}("[^\n]*$)',
            replacement=rf"\g<1>{new_version}\g<2>",
        )
        if replaced is None:
            return None
        blocks[index] = replaced
    return "".join(blocks) if found == owned_packages else None


def _replace_once(*, value: str, pattern: str, replacement: str) -> str | None:
    replaced, count = re.subn(pattern, replacement, value, count=1)
    return replaced if count == 1 else None
