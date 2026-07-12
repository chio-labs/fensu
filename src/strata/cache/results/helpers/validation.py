"""Validate persistent evaluation-result record values."""

from __future__ import annotations

import re
from pathlib import PurePosixPath
from typing import cast

from strata.analysis.types import ProjectDependencyKind
from strata.cache.fingerprints.models import CacheFingerprint
from strata.cache.results.constants import (
    CORE_RULE_CODE_PATTERN,
    CUSTOM_RULE_CODE_PATTERN,
    PARENT_PATH_PART,
    REPOSITORY_ROOT_PATH,
    RULE_EXCEPTION_SYMBOL_PATTERN,
    SHA256_HEX_DIGITS,
    SHA256_HEX_LENGTH,
    WINDOWS_PATH_SEPARATOR,
)
from strata.cache.results.models import DependencyObservation


def is_fingerprint(value: object) -> bool:
    """Return whether a value is a canonical lowercase SHA-256 identity."""

    return (
        isinstance(value, str)
        and len(value) == SHA256_HEX_LENGTH
        and all(character in SHA256_HEX_DIGITS for character in value)
    )


def fingerprint_or_none(value: object) -> CacheFingerprint | None:
    """Return a typed fingerprint only for a canonical SHA-256 identity."""

    return CacheFingerprint(value=cast(str, value)) if is_fingerprint(value) else None


def is_relative_path(*, value: object, allow_root: bool = False) -> bool:
    """Return whether a value is a normalized repository-relative POSIX path."""

    if not isinstance(value, str) or not value or WINDOWS_PATH_SEPARATOR in value:
        return False
    path: PurePosixPath = PurePosixPath(value)
    if path.is_absolute() or PARENT_PATH_PART in path.parts or path.as_posix() != value:
        return False
    return allow_root or value != REPOSITORY_ROOT_PATH


def is_rule_code(value: object) -> bool:
    """Return whether a value is one exact core or custom rule code."""

    return isinstance(value, str) and (
        re.fullmatch(CORE_RULE_CODE_PATTERN, value) is not None
        or re.fullmatch(CUSTOM_RULE_CODE_PATTERN, value) is not None
    )


def is_rule_exception_symbol(value: object) -> bool:
    """Return whether a value is a supported qualified exception symbol."""

    return isinstance(value, str) and re.fullmatch(RULE_EXCEPTION_SYMBOL_PATTERN, value) is not None


def is_dependency_observation(observation: DependencyObservation) -> bool:
    """Return whether an observation carries the answer required by its query kind."""

    if not (
        is_relative_path(value=observation.requester_path)
        and is_relative_path(value=observation.query_path, allow_root=True)
        and is_relative_path(value=observation.dependency_path, allow_root=True)
    ):
        return False
    if observation.kind is ProjectDependencyKind.GLOB:
        if not observation.pattern:
            return False
    elif observation.pattern is not None or observation.recursive:
        return False
    if observation.kind is ProjectDependencyKind.SOURCE:
        return observation.answer is None or is_fingerprint(observation.answer)
    if observation.kind in {
        ProjectDependencyKind.EXISTS,
        ProjectDependencyKind.IS_FILE,
        ProjectDependencyKind.IS_DIR,
    }:
        return type(observation.answer) is bool
    if not isinstance(observation.answer, tuple):
        return False
    return all(is_relative_path(value=path, allow_root=True) for path in observation.answer)
