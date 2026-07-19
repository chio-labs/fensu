"""Helpers for native result-generation integration tests."""

import ast
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import cast

import pytest

import strata.evaluation._helpers.file_evaluation as file_evaluation_module
from strata.analysis.types import Analysis
from strata.cache.fingerprints.models import CacheFingerprint
from strata.cache.fingerprints.types import CanonicalValue
from strata.cache.results.classes.result_cache import ResultCache
from strata.cache.results.main.evaluate import evaluate_with_cache
from strata.cache.results.models import CacheEvaluation, CacheStats
from strata.cache.storage.classes.cache_store import CacheStore
from strata.cache.storage.constants import CACHE_DATABASE_RELATIVE_PATH
from strata.cache.storage.exceptions import CacheRecordError
from strata.cache.storage.models import CacheRecord
from strata.config.models import Config, RuleExceptionEntry
from strata.discovery.main.discover_files import discover_files
from strata.discovery.models import DiscoveredTree
from strata.evaluation.models import EvaluationResult
from strata.rules.authoring.models import Fault, RuleSpec
from strata.rules.authoring.types import Family, RuleContext, RuleKind
from strata.rules.roles.constants import SFR_RULES
from tests.integration.src.strata.cache.storage.helpers import run_while_database_blocked


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
    return config, discover_files(config=config, repo_root=repo_root)


def role_rule(*, code: str) -> RuleSpec:
    """Return one core role rule by stable code."""

    rules_by_code: dict[str, RuleSpec] = {rule.code: rule for rule in SFR_RULES}
    return rules_by_code[code]


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
        exists: bool = ctx.project.exists(
            requester=ctx.path,
            path=ctx.repo_root / "dependency.py",
        )
        message: str = {False: "missing", True: "present"}[exists]
        return [ctx.path_fault(message=message)]

    return RuleSpec(
        code="XCR002",
        family=Family.CUSTOM,
        slug="cache-dependency",
        message="cache dependency",
        check=check,
    )


def arbitrary_glob_fault_rule() -> RuleSpec:
    """Return a cacheable rule consuming a recursive non-Python glob."""

    def check(module: ast.Module, ctx: RuleContext) -> list[Fault]:
        del module
        paths: tuple[Path, ...] = ctx.project.glob(
            requester=ctx.path,
            path=ctx.repo_root / "assets",
            pattern="*.sql",
            recursive=True,
        )
        message: str = ",".join(path.name for path in paths) or "empty"
        return [ctx.path_fault(message=message)]

    return RuleSpec(
        code="XCR007",
        family=Family.CUSTOM,
        slug="cache-arbitrary-glob",
        message="cache arbitrary glob",
        check=check,
        kind=RuleKind.CUSTOM,
        cacheable=True,
    )


def context_source_fault_rule() -> RuleSpec:
    """Return a cacheable rule whose diagnostic reads one discovered context file."""

    def check(module: ast.Module, ctx: RuleContext) -> list[Fault]:
        del module
        context_path: Path = ctx.repo_root / "src/pkg/context.py"
        analysis: Analysis | None = ctx.project.analysis(requester=ctx.path, path=context_path)
        source: str = getattr(getattr(analysis, "text", None), "source", "missing")
        return [ctx.path_fault(message=source.strip())]

    return RuleSpec(
        code="XCR006",
        family=Family.CUSTOM,
        slug="cache-context-source",
        message="cache context source",
        check=check,
        kind=RuleKind.CORE,
    )


def exception_fault_rule() -> RuleSpec:
    """Return a function-owned fault suitable for exception suppression."""

    def check(module: ast.Module, ctx: RuleContext) -> list[Fault]:
        return [ctx.fault(node=module.body[0])]

    return RuleSpec(
        code="XCR003",
        family=Family.CUSTOM,
        slug="cache-exception",
        message="cache exception",
        check=check,
        uses_module=True,
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
    """Return a rule emitting a fault position the native schema rejects."""

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
    """Fail every native generation publication with an internal record error."""

    def raise_publish_native(cache: ResultCache, **kwargs: object) -> CacheStats:
        del cache, kwargs
        raise CacheRecordError("publication rejected")

    monkeypatch.setattr(ResultCache, "publish_native_generation", raise_publish_native)


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
    """Reject generation publication while proving a fully warm cache hit."""

    def reject_publication(cache: ResultCache, **kwargs: object) -> CacheStats:
        del cache, kwargs
        raise AssertionError("fully warm cache path attempted a persistent write")

    monkeypatch.setattr(ResultCache, "publish_native_generation", reject_publication)


def evaluated_result(evaluation: CacheEvaluation) -> EvaluationResult:
    """Return the required evaluation result from a non-short-circuited run."""

    return cast(EvaluationResult, evaluation.result)


def corrupt_indexed_result_record(*, repo_root: Path) -> None:
    """Reseal a semantically shaped result whose identity no longer matches its index entry."""

    store: CacheStore = CacheStore(repo_root=repo_root)
    index: CacheRecord | None = store.read(relative_path=Path("index.json"), expected_kind="index")
    assert index is not None
    index_payload: dict[str, object] = cast(dict[str, object], index.payload)
    entries: list[dict[str, object]] = cast(list[dict[str, object]], index_payload["entries"])
    result_fingerprint: str = cast(str, entries[0]["result_fingerprint"])
    result_path: Path = Path("results") / result_fingerprint[:2] / f"{result_fingerprint}.json"
    record: CacheRecord | None = store.read(
        relative_path=result_path,
        expected_kind="file_result",
    )
    assert record is not None
    payload: dict[str, object] = dict(cast(dict[str, object], record.payload))
    faults: list[dict[str, object]] = [
        dict(value) for value in cast(list[dict[str, object]], payload["faults"])
    ]
    faults[0]["message"] = "resealed corruption"
    payload["faults"] = faults
    written: bool = store.write(
        relative_path=result_path,
        record=CacheRecord(kind="file_result", payload=cast(CanonicalValue, payload)),
    )
    assert written


def evaluate_cache_concurrently(
    *,
    tree: DiscoveredTree,
    ruleset: tuple[RuleSpec, ...],
    config: Config,
    global_fingerprint: CacheFingerprint,
    writer_count: int,
) -> tuple[CacheEvaluation, ...]:
    """Run simultaneous complete-generation evaluations against one repository."""

    def evaluate_one(_: int) -> CacheEvaluation:
        return evaluate_with_cache(
            tree=tree,
            ruleset=ruleset,
            config=config,
            global_fingerprint=global_fingerprint,
        )

    with ThreadPoolExecutor(max_workers=writer_count) as executor:
        return tuple(executor.map(evaluate_one, range(writer_count)))


def evaluate_cache_while_database_blocked(
    *,
    tree: DiscoveredTree,
    ruleset: tuple[RuleSpec, ...],
    config: Config,
    global_fingerprint: CacheFingerprint,
) -> CacheEvaluation:
    """Evaluate one changed generation while another process prevents publication."""

    store: CacheStore = CacheStore(repo_root=tree.repo_root.path)
    return run_while_database_blocked(
        store=store,
        operation=lambda: evaluate_with_cache(
            tree=tree,
            ruleset=ruleset,
            config=config,
            global_fingerprint=global_fingerprint,
        ),
    )
