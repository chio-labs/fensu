"""Build the isolated repository and harness-owned evaluation config."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path, PurePosixPath

from strata.config.main.build_config import build_config
from strata.config.models import Config
from strata.discovery.types import ScopeName
from strata.rules.testing._helpers.validation import resolved_scope_root, scope_name
from strata.rules.testing.constants import (
    FALLBACK_RUNTIME_ROOT,
    MINIMUM_SOURCE_PATH_PARTS,
    SOURCE_PATH_PART,
    TEST_PATH_PART,
    TOOLING_PATH_PART,
)
from strata.rules.testing.exceptions import RuleHarnessError
from strata.rules.testing.models import RuleCase, RuleFile


def build_harness_config(*, test_case: RuleCase) -> Config:
    """Merge meaningful case config into deterministic harness-owned roots and selection."""

    runtime_roots, test_roots, tooling_roots = _scope_roots(test_case=test_case)
    raw: dict[str, object] = {
        "roots": list(runtime_roots),
        "tests": list(test_roots),
        "tooling": list(tooling_roots),
        "evaluation": {"include": [test_case.path]},
    }
    if test_case.config is not None:
        raw.update(_plain_mapping(value=test_case.config))
    return build_config(raw)


def write_harness_repository(*, repo_root: Path, test_case: RuleCase, config: Config) -> None:
    """Write configured roots plus primary and support sources in deterministic path order."""

    configured_roots: tuple[str, ...] = (*config.roots, *config.tests, *config.tooling)
    for configured_root in configured_roots:
        (repo_root / configured_root).mkdir(parents=True, exist_ok=True)
    sources: list[tuple[str, str]] = [(test_case.path, test_case.source)]
    sources.extend((support.path, support.source) for support in test_case.files)
    for relative_path, source in sorted(sources):
        path: Path = repo_root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding="utf-8")


def _scope_roots(
    *, test_case: RuleCase
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    primary_root: str = resolved_scope_root(test_case=test_case).as_posix()
    primary_scope: ScopeName = scope_name(test_case.scope)
    roots_by_scope: dict[ScopeName, set[str]] = {scope: set() for scope in ScopeName}
    roots_by_scope[primary_scope].add(primary_root)
    for support_file in test_case.files:
        support_path: PurePosixPath = PurePosixPath(support_file.path)
        if support_path.is_relative_to(PurePosixPath(primary_root)):
            continue
        support_scope, support_root = _support_scope_root(support_file=support_file)
        roots_by_scope[support_scope].add(support_root)
    if not roots_by_scope[ScopeName.ROOT]:
        roots_by_scope[ScopeName.ROOT].add(FALLBACK_RUNTIME_ROOT)
    _validate_root_ownership(roots_by_scope=roots_by_scope)
    return (
        tuple(sorted(roots_by_scope[ScopeName.ROOT])),
        tuple(sorted(roots_by_scope[ScopeName.TEST])),
        tuple(sorted(roots_by_scope[ScopeName.TOOLING])),
    )


def _support_scope_root(*, support_file: RuleFile) -> tuple[ScopeName, str]:
    path: PurePosixPath = PurePosixPath(support_file.path)
    if path.parts[0] == TEST_PATH_PART:
        return ScopeName.TEST, path.parts[0]
    if path.parts[0] == TOOLING_PATH_PART:
        return ScopeName.TOOLING, path.parts[0]
    if len(path.parts) >= MINIMUM_SOURCE_PATH_PARTS and path.parts[0] == SOURCE_PATH_PART:
        return ScopeName.ROOT, PurePosixPath(*path.parts[:2]).as_posix()
    return ScopeName.ROOT, path.parts[0]


def _validate_root_ownership(*, roots_by_scope: dict[ScopeName, set[str]]) -> None:
    owners: dict[str, ScopeName] = {}
    for scope in ScopeName:
        for root in roots_by_scope[scope]:
            existing: ScopeName | None = owners.get(root)
            if existing is not None and existing is not scope:
                raise RuleHarnessError(
                    f"Harness scope root {root} cannot belong to both {existing.value} and "
                    f"{scope.value}."
                )
            owners[root] = scope


def _plain_mapping(*, value: Mapping[str, object]) -> dict[str, object]:
    return {key: _plain_value(value=item) for key, item in value.items()}


def _plain_value(*, value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): _plain_value(value=item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_plain_value(value=item) for item in value]
    return value
