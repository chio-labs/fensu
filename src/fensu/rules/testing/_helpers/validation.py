"""Validate public custom-rule harness inputs."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import PurePosixPath

from fensu.discovery.types import ScopeName
from fensu.rules.testing.constants import (
    CURRENT_PATH_PART,
    MINIMUM_SOURCE_PATH_PARTS,
    PARENT_PATH_PART,
    PYTHON_FILE_SUFFIX,
    SOURCE_PATH_PART,
    WINDOWS_PATH_SEPARATOR,
)
from fensu.rules.testing.exceptions import RuleHarnessError
from fensu.rules.testing.models import RuleCase, RuleFile

_allowed_config_keys: frozenset[str] = frozenset(
    {"contracts", "roles", "rule_exceptions", "threshold_overrides", "thresholds"}
)


def validate_rule_case(*, test_case: RuleCase) -> None:
    """Reject malformed or harness-conflicting case inputs."""

    if not isinstance(test_case, RuleCase):
        raise RuleHarnessError("test_case must be a RuleCase instance.")
    if not isinstance(test_case.description, str) or not test_case.description.strip():
        raise RuleHarnessError("RuleCase description must be a non-empty string.")
    if not isinstance(test_case.source, str):
        raise RuleHarnessError("RuleCase source must be a string.")
    if type(test_case.expected_fault_count) is not int or test_case.expected_fault_count < 0:
        raise RuleHarnessError("RuleCase expected_fault_count must be a non-negative integer.")
    _ = scope_name(test_case.scope)
    primary_path: PurePosixPath = python_path(value=test_case.path, owner="RuleCase path")
    scope_root: PurePosixPath = resolved_scope_root(test_case=test_case)
    if not primary_path.is_relative_to(scope_root):
        raise RuleHarnessError(
            f"RuleCase path must be contained by scope_root {scope_root.as_posix()}."
        )
    if primary_path == scope_root:
        raise RuleHarnessError(
            "RuleCase scope_root must be a directory containing the primary file."
        )
    support_paths: set[PurePosixPath] = set()
    for support_file in test_case.files:
        if not isinstance(support_file, RuleFile):
            raise RuleHarnessError("RuleCase files must contain only RuleFile instances.")
        if not isinstance(support_file.source, str):
            raise RuleHarnessError("RuleFile source must be a string.")
        support_path: PurePosixPath = python_path(value=support_file.path, owner="RuleFile path")
        if support_path == primary_path:
            raise RuleHarnessError(
                f"RuleFile path collides with the primary RuleCase path: {support_file.path}."
            )
        if support_path in support_paths:
            raise RuleHarnessError(f"Duplicate RuleFile path: {support_file.path}.")
        support_paths.add(support_path)
    validate_config_fragment(config=test_case.config)


def scope_name(value: object) -> ScopeName:
    """Return one supported scope name or raise a harness error."""

    try:
        return ScopeName(value)
    except (TypeError, ValueError) as error:
        supported: str = ", ".join(scope.value for scope in ScopeName)
        raise RuleHarnessError(f"RuleCase scope must be one of: {supported}.") from error


def resolved_scope_root(*, test_case: RuleCase) -> PurePosixPath:
    """Return the explicit or conventionally inferred primary scope root."""

    if test_case.scope_root is not None:
        return directory_path(value=test_case.scope_root, owner="RuleCase scope_root")
    path: PurePosixPath = python_path(value=test_case.path, owner="RuleCase path")
    scope: ScopeName = scope_name(test_case.scope)
    if (
        scope is ScopeName.ROOT
        and len(path.parts) >= MINIMUM_SOURCE_PATH_PARTS
        and path.parts[0] == SOURCE_PATH_PART
    ):
        return PurePosixPath(*path.parts[:2])
    return PurePosixPath(path.parts[0])


def python_path(*, value: object, owner: str) -> PurePosixPath:
    """Validate one exact repository-relative POSIX Python path."""

    path: PurePosixPath = _repository_path(value=value, owner=owner)
    if path.suffix != PYTHON_FILE_SUFFIX:
        raise RuleHarnessError(f"{owner} must end in .py: {value}.")
    return path


def directory_path(*, value: object, owner: str) -> PurePosixPath:
    """Validate one repository-relative POSIX directory path."""

    return _repository_path(value=value, owner=owner)


def validate_config_fragment(*, config: Mapping[str, object] | None) -> None:
    """Allow only config values that ordinary rule evaluation can meaningfully consume."""

    if config is None:
        return
    if not isinstance(config, Mapping):
        raise RuleHarnessError("RuleCase config must be a mapping.")
    invalid_keys: set[str] = set(config) - _allowed_config_keys
    if invalid_keys:
        names: str = ", ".join(sorted(str(key) for key in invalid_keys))
        raise RuleHarnessError(
            "RuleCase config cannot override harness-owned or unsupported key(s): " + names + "."
        )


def _repository_path(*, value: object, owner: str) -> PurePosixPath:
    if not isinstance(value, str) or not value:
        raise RuleHarnessError(f"{owner} must be a non-empty string.")
    path: PurePosixPath = PurePosixPath(value)
    if (
        path.is_absolute()
        or WINDOWS_PATH_SEPARATOR in value
        or value != path.as_posix()
        or any(part in {CURRENT_PATH_PART, PARENT_PATH_PART} for part in path.parts)
    ):
        raise RuleHarnessError(
            f"{owner} must be a normalized repository-relative POSIX path: {value}."
        )
    return path
