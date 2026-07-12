"""Helpers for persistent result-cache integration tests."""

import ast
import sqlite3
from pathlib import Path

import pytest

import strata.evaluation.core.helpers.file_evaluation as file_evaluation_module
from strata.analysis.core.models import ProjectDependency
from strata.analysis.core.types import ProjectDependencyKind
from strata.cache.results.classes.result_cache import ResultCache
from strata.cache.results.models import CacheStats
from strata.cache.storage.classes.cache_store import CacheStore
from strata.cache.storage.constants import CACHE_DATABASE_RELATIVE_PATH
from strata.cache.storage.exceptions import CacheRecordError
from strata.cache.storage.models import CacheMutationOutcome, CacheRead, CacheWrite
from strata.cache.storage.types import CacheMutator
from strata.config.core.models import Config, RuleExceptionEntry
from strata.discovery.core.main.discover_files import discover_files
from strata.discovery.core.models import DiscoveredTree
from strata.evaluation.core.models import FileEvaluation
from strata.rules.authoring.models import Fault, RuleSpec
from strata.rules.authoring.types import Family, RuleContext, RuleKind


def file_evaluation(
    *,
    repo_root: Path,
    relative_path: str,
    fault_message: str = "missing annotation",
) -> FileEvaluation:
    """Return one deterministic runtime file evaluation."""

    path: Path = repo_root / relative_path
    return FileEvaluation(
        path=path,
        source_fingerprint="b" * 64,
        faults=(
            Fault(
                code="SFA001",
                path=path,
                message=fault_message,
                line=1,
                column=0,
            ),
        ),
        applied_exception_keys=(),
        dependencies=(
            ProjectDependency(
                requester=path,
                query_path=repo_root / "src/pkg/dependency.py",
                dependency=repo_root / "src/pkg/dependency.py",
                kind=ProjectDependencyKind.EXISTS,
                answer=False,
            ),
        ),
    )


def external_dependency_evaluation(*, repo_root: Path, relative_path: str) -> FileEvaluation:
    """Return a runtime result whose resolved dependency leaves the repository."""

    path: Path = repo_root / relative_path
    return FileEvaluation(
        path=path,
        source_fingerprint="b" * 64,
        faults=(),
        applied_exception_keys=(),
        dependencies=(
            ProjectDependency(
                requester=path,
                query_path=repo_root / "src/pkg/link.py",
                dependency=repo_root.parent / "external.py",
                kind=ProjectDependencyKind.SOURCE,
                answer="c" * 64,
            ),
        ),
    )


def install_cache_write_failure(
    *,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reject one complete cache publication transaction."""

    def write_batch(
        store: CacheStore,
        *,
        writes: tuple[CacheWrite, ...],
    ) -> bool:
        del store, writes
        return False

    def mutate_batch(
        store: CacheStore,
        *,
        reads: tuple[CacheRead, ...],
        mutate: CacheMutator,
    ) -> CacheMutationOutcome:
        del store, reads, mutate
        return CacheMutationOutcome(published=False, mutation=None)

    monkeypatch.setattr(CacheStore, "write_batch", write_batch)
    monkeypatch.setattr(CacheStore, "mutate_batch", mutate_batch)


def result_record_keys(*, repo_root: Path) -> tuple[str, ...]:
    """Return sorted persisted result record keys for sweep assertions."""

    database: Path = repo_root / CACHE_DATABASE_RELATIVE_PATH
    with sqlite3.connect(database) as connection:
        rows: list[tuple[str]] = connection.execute(
            "SELECT key FROM records WHERE key LIKE 'results/%'"
        ).fetchall()
    return tuple(sorted(row[0] for row in rows))


def write_project_sources(
    *,
    repo_root: Path,
    files: tuple[tuple[str, str], ...],
) -> None:
    """Write source files for cached evaluation integration tests."""

    for relative_path, source in files:
        path: Path = repo_root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding="utf-8")


def discover_project(*, repo_root: Path) -> tuple[Config, DiscoveredTree]:
    """Return one configured and discovered runtime project."""

    config: Config = Config(roots=("src/pkg",), tests=())
    return config, discover_files(config, repo_root=repo_root)


def source_fault_rule(*, kind: RuleKind = RuleKind.CORE, cacheable: bool = False) -> RuleSpec:
    """Return a deterministic rule reporting the complete stripped source."""

    def check(module: ast.Module, ctx: RuleContext) -> list[Fault]:
        del module
        return [ctx.path_fault(message=ctx.source.strip())]

    return RuleSpec(
        code="XCR001",
        family=Family.CUSTOM,
        slug="cache-reuse",
        message="cache reuse",
        check=check,
        kind=kind,
        cacheable=cacheable,
    )


def dependency_fault_rule() -> RuleSpec:
    """Return a rule whose diagnostic consumes one negative existence query."""

    def check(module: ast.Module, ctx: RuleContext) -> list[Fault]:
        del module
        exists: bool = ctx._project.exists(
            requester=ctx.path,
            path=ctx.repo_root / "dependency.py",
        )
        return [ctx.path_fault(message="present" if exists else "missing")]

    return RuleSpec(
        code="XCR002",
        family=Family.CUSTOM,
        slug="cache-dependency",
        message="cache dependency",
        check=check,
    )


def exception_fault_rule() -> RuleSpec:
    """Return a function-owned fault suitable for exception suppression."""

    def check(module: ast.Module, ctx: RuleContext) -> list[Fault]:
        return [ctx.fault(module.body[0])]

    return RuleSpec(
        code="XCR003",
        family=Family.CUSTOM,
        slug="cache-exception",
        message="cache exception",
        check=check,
    )


def exception_config(*, relative_path: str) -> Config:
    """Return config with one exact exception for the cached fault rule."""

    return Config(
        roots=("src/pkg",),
        tests=(),
        rule_exceptions=(
            RuleExceptionEntry(
                rule="XCR003",
                path=relative_path,
                symbols=("build",),
                reason="cached exception proof",
            ),
        ),
    )


def invalid_fault_rule() -> RuleSpec:
    """Return a rule emitting a fault position the cache schema rejects."""

    def check(module: ast.Module, ctx: RuleContext) -> list[Fault]:
        del module
        return [
            Fault(
                code="XCR005",
                path=ctx.path,
                message="invalid position",
                line=0,
                column=0,
            )
        ]

    return RuleSpec(
        code="XCR005",
        family=Family.CUSTOM,
        slug="cache-invalid-fault",
        message="cache invalid fault",
        check=check,
    )


def install_publish_error(*, monkeypatch: pytest.MonkeyPatch) -> None:
    """Fail every typed cache publication with an internal record error."""

    def raise_publish(cache: ResultCache, **kwargs: object) -> CacheStats:
        del cache, kwargs
        raise CacheRecordError("publication rejected")

    monkeypatch.setattr(ResultCache, "publish", raise_publish)


def failing_rule() -> RuleSpec:
    """Return a deterministic rule that aborts evaluation."""

    def check(module: ast.Module, ctx: RuleContext) -> list[Fault]:
        del module, ctx
        raise AssertionError("evaluation failed")

    return RuleSpec(
        code="XCR004",
        family=Family.CUSTOM,
        slug="cache-failure",
        message="cache failure",
        check=check,
    )


def install_rule_execution_failure(*, monkeypatch: pytest.MonkeyPatch) -> None:
    """Reject any fresh rule execution while proving a warm cache hit."""

    def fail_execute_rule(**kwargs: object) -> list[Fault]:
        del kwargs
        raise AssertionError("warm cache path executed a rule")

    monkeypatch.setattr(file_evaluation_module, "execute_rule", fail_execute_rule)


def install_cache_write_rejection(*, monkeypatch: pytest.MonkeyPatch) -> None:
    """Reject every persistent write while proving a fully warm generation."""

    def reject_write_batch(
        store: CacheStore,
        *,
        writes: tuple[CacheWrite, ...],
    ) -> bool:
        del store, writes
        raise AssertionError("fully warm cache path attempted a persistent write")

    def reject_mutate_batch(
        store: CacheStore,
        *,
        reads: tuple[CacheRead, ...],
        mutate: CacheMutator,
    ) -> CacheMutationOutcome:
        del store, reads, mutate
        raise AssertionError("fully warm cache path opened a write transaction")

    monkeypatch.setattr(CacheStore, "write_batch", reject_write_batch)
    monkeypatch.setattr(CacheStore, "mutate_batch", reject_mutate_batch)
