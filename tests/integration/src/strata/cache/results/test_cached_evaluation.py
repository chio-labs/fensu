"""Integration tests for cold, warm, and invalidated cached evaluation."""

from __future__ import annotations

from pathlib import Path

import pytest

from strata.cache.fingerprints.models import CacheFingerprint
from strata.cache.results.main.evaluate import evaluate_with_cache
from strata.cache.results.models import CacheEvaluation
from strata.config.core.models import Config
from strata.discovery.core.models import DiscoveredTree
from strata.rules.authoring.models import RuleSpec
from strata.rules.authoring.types import RuleKind
from tests.integration.src.strata.cache.results._test_types import (
    CachedEvaluationDegradationTestCase,
    CachedEvaluationFailureTestCase,
    CachedEvaluationInvalidationTestCase,
    CachedEvaluationManifestTestCase,
    CachedEvaluationRetentionTestCase,
    CachedEvaluationReuseTestCase,
    CachedEvaluationSweepTestCase,
)
from tests.integration.src.strata.cache.results.helpers import (
    dependency_fault_rule,
    discover_project,
    exception_config,
    exception_fault_rule,
    failing_rule,
    install_cache_write_rejection,
    install_publish_error,
    install_rule_execution_failure,
    invalid_fault_rule,
    result_record_keys,
    source_fault_rule,
    write_project_sources,
)

_GLOBAL_FINGERPRINT: CacheFingerprint = CacheFingerprint("e" * 64)


@pytest.mark.parametrize(
    "test_case",
    [
        CachedEvaluationReuseTestCase(
            description="cold evaluation publishes and warm evaluation reuses without execution",
            relative_path="src/pkg/models.py",
            source="value: int = 1\n",
            expected_cold_hits=0,
            expected_cold_misses=1,
            expected_warm_hits=1,
            expected_warm_misses=0,
            expected_warm_writes=0,
            expected_fault_count=1,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_published_result_when_evaluating_warm_then_reuses_without_rule_execution(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: CachedEvaluationReuseTestCase,
) -> None:
    write_project_sources(
        repo_root=tmp_path,
        files=((test_case.relative_path, test_case.source),),
    )
    config, tree = discover_project(repo_root=tmp_path)
    ruleset: tuple[RuleSpec, ...] = (source_fault_rule(),)

    cold: CacheEvaluation = evaluate_with_cache(
        tree=tree,
        ruleset=ruleset,
        config=config,
        global_fingerprint=_GLOBAL_FINGERPRINT,
    )
    install_rule_execution_failure(monkeypatch=monkeypatch)
    install_cache_write_rejection(monkeypatch=monkeypatch)
    warm: CacheEvaluation = evaluate_with_cache(
        tree=tree,
        ruleset=ruleset,
        config=config,
        global_fingerprint=_GLOBAL_FINGERPRINT,
    )

    assert cold.stats.hits == test_case.expected_cold_hits
    assert cold.stats.misses == test_case.expected_cold_misses
    assert warm.stats.hits == test_case.expected_warm_hits
    assert warm.stats.misses == test_case.expected_warm_misses
    assert warm.stats.writes == test_case.expected_warm_writes
    assert len(warm.result.faults) == test_case.expected_fault_count
    assert warm.result.faults == cold.result.faults


@pytest.mark.parametrize(
    "test_case",
    [
        CachedEvaluationInvalidationTestCase(
            description="same-length source edit recomputes indexed requester",
            relative_path="src/pkg/models.py",
            first_source="value: int = 1\n",
            second_source="value: int = 2\n",
            expected_invalidations=1,
            expected_message="value: int = 2",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_published_result_when_source_changes_then_recomputes_diagnostic(
    tmp_path: Path,
    test_case: CachedEvaluationInvalidationTestCase,
) -> None:
    write_project_sources(
        repo_root=tmp_path,
        files=((test_case.relative_path, test_case.first_source),),
    )
    config, tree = discover_project(repo_root=tmp_path)
    ruleset: tuple[RuleSpec, ...] = (source_fault_rule(),)
    _ = evaluate_with_cache(
        tree=tree,
        ruleset=ruleset,
        config=config,
        global_fingerprint=_GLOBAL_FINGERPRINT,
    )
    write_project_sources(
        repo_root=tmp_path,
        files=((test_case.relative_path, test_case.second_source),),
    )

    changed: CacheEvaluation = evaluate_with_cache(
        tree=tree,
        ruleset=ruleset,
        config=config,
        global_fingerprint=_GLOBAL_FINGERPRINT,
    )

    assert changed.stats.invalidations == test_case.expected_invalidations
    assert changed.result.faults[0].message == test_case.expected_message


@pytest.mark.parametrize(
    "test_case",
    [
        CachedEvaluationInvalidationTestCase(
            description="negative dependency creation recomputes requester",
            relative_path="src/pkg/models.py",
            first_source="value: int = 1\n",
            second_source="value: int = 1\n",
            expected_invalidations=1,
            expected_message="present",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_negative_dependency_when_file_appears_then_recomputes_requester(
    tmp_path: Path,
    test_case: CachedEvaluationInvalidationTestCase,
) -> None:
    write_project_sources(
        repo_root=tmp_path,
        files=((test_case.relative_path, test_case.first_source),),
    )
    config, tree = discover_project(repo_root=tmp_path)
    ruleset: tuple[RuleSpec, ...] = (dependency_fault_rule(),)
    _ = evaluate_with_cache(
        tree=tree,
        ruleset=ruleset,
        config=config,
        global_fingerprint=_GLOBAL_FINGERPRINT,
    )
    (tmp_path / "dependency.py").write_text(test_case.second_source, encoding="utf-8")

    changed: CacheEvaluation = evaluate_with_cache(
        tree=tree,
        ruleset=ruleset,
        config=config,
        global_fingerprint=_GLOBAL_FINGERPRINT,
    )

    assert changed.stats.invalidations == test_case.expected_invalidations
    assert changed.result.faults[0].message == test_case.expected_message


@pytest.mark.parametrize(
    "test_case",
    [
        CachedEvaluationManifestTestCase(
            description="new and deleted files update complete result while reusing unchanged file",
            initial_files=("src/pkg/a.py", "src/pkg/b.py"),
            final_files=("src/pkg/a.py", "src/pkg/c.py"),
            expected_hits=1,
            expected_misses=1,
            expected_invalidations=1,
            expected_fault_paths=("a.py", "c.py"),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_changed_manifest_when_evaluating_then_combines_hits_and_new_files(
    tmp_path: Path,
    test_case: CachedEvaluationManifestTestCase,
) -> None:
    write_project_sources(
        repo_root=tmp_path,
        files=tuple((path, "value: int = 1\n") for path in test_case.initial_files),
    )
    config, initial_tree = discover_project(repo_root=tmp_path)
    ruleset: tuple[RuleSpec, ...] = (source_fault_rule(),)
    _ = evaluate_with_cache(
        tree=initial_tree,
        ruleset=ruleset,
        config=config,
        global_fingerprint=_GLOBAL_FINGERPRINT,
    )
    (tmp_path / "src/pkg/b.py").unlink()
    write_project_sources(
        repo_root=tmp_path,
        files=(("src/pkg/c.py", "value: int = 1\n"),),
    )
    final_tree: DiscoveredTree = discover_project(repo_root=tmp_path)[1]

    changed: CacheEvaluation = evaluate_with_cache(
        tree=final_tree,
        ruleset=ruleset,
        config=config,
        global_fingerprint=_GLOBAL_FINGERPRINT,
    )

    assert changed.stats.hits == test_case.expected_hits
    assert changed.stats.misses == test_case.expected_misses
    assert changed.stats.invalidations == test_case.expected_invalidations
    assert tuple(fault.path.name for fault in changed.result.faults) == (
        test_case.expected_fault_paths
    )


@pytest.mark.parametrize(
    "test_case",
    [
        CachedEvaluationReuseTestCase(
            description="declared cacheable custom rule publishes and reuses results",
            relative_path="src/pkg/models.py",
            source="value: int = 1\n",
            expected_cold_hits=0,
            expected_cold_misses=1,
            expected_warm_hits=1,
            expected_warm_misses=0,
            expected_warm_writes=0,
            expected_fault_count=1,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_cacheable_custom_rule_when_evaluating_then_reuses_published_result(
    tmp_path: Path,
    test_case: CachedEvaluationReuseTestCase,
) -> None:
    write_project_sources(
        repo_root=tmp_path,
        files=((test_case.relative_path, test_case.source),),
    )
    config, tree = discover_project(repo_root=tmp_path)
    ruleset: tuple[RuleSpec, ...] = (source_fault_rule(kind=RuleKind.CUSTOM, cacheable=True),)

    cold: CacheEvaluation = evaluate_with_cache(
        tree=tree,
        ruleset=ruleset,
        config=config,
        global_fingerprint=_GLOBAL_FINGERPRINT,
    )
    warm: CacheEvaluation = evaluate_with_cache(
        tree=tree,
        ruleset=ruleset,
        config=config,
        global_fingerprint=_GLOBAL_FINGERPRINT,
    )

    assert cold.stats.hits == test_case.expected_cold_hits
    assert cold.stats.misses == test_case.expected_cold_misses
    assert warm.stats.hits == test_case.expected_warm_hits
    assert warm.stats.misses == test_case.expected_warm_misses
    assert warm.stats.writes == test_case.expected_warm_writes
    assert len(warm.result.faults) == test_case.expected_fault_count
    assert warm.result.faults == cold.result.faults
    assert (tmp_path / ".strata").exists()


@pytest.mark.parametrize(
    "test_case",
    [
        CachedEvaluationReuseTestCase(
            description="custom rules remain non-cacheable and create no storage",
            relative_path="src/pkg/models.py",
            source="value: int = 1\n",
            expected_cold_hits=0,
            expected_cold_misses=0,
            expected_warm_hits=0,
            expected_warm_misses=0,
            expected_warm_writes=0,
            expected_fault_count=1,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_custom_rule_when_evaluating_then_bypasses_persistent_cache(
    tmp_path: Path,
    test_case: CachedEvaluationReuseTestCase,
) -> None:
    write_project_sources(
        repo_root=tmp_path,
        files=((test_case.relative_path, test_case.source),),
    )
    config, tree = discover_project(repo_root=tmp_path)
    ruleset: tuple[RuleSpec, ...] = (source_fault_rule(kind=RuleKind.CUSTOM),)

    first: CacheEvaluation = evaluate_with_cache(
        tree=tree,
        ruleset=ruleset,
        config=config,
        global_fingerprint=_GLOBAL_FINGERPRINT,
    )
    second: CacheEvaluation = evaluate_with_cache(
        tree=tree,
        ruleset=ruleset,
        config=config,
        global_fingerprint=_GLOBAL_FINGERPRINT,
    )

    assert first.stats.hits == test_case.expected_cold_hits
    assert first.stats.misses == test_case.expected_cold_misses
    assert second.stats.hits == test_case.expected_warm_hits
    assert second.stats.misses == test_case.expected_warm_misses
    assert len(second.result.faults) == test_case.expected_fault_count
    assert not (tmp_path / ".strata").exists()


@pytest.mark.parametrize(
    "test_case",
    [
        CachedEvaluationReuseTestCase(
            description="warm hit preserves applied exception and global stale validation",
            relative_path="src/pkg/models.py",
            source="def build() -> None:\n    pass\n",
            expected_cold_hits=0,
            expected_cold_misses=1,
            expected_warm_hits=1,
            expected_warm_misses=0,
            expected_warm_writes=0,
            expected_fault_count=0,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_applied_exception_when_reusing_result_then_preserves_global_validation(
    tmp_path: Path,
    test_case: CachedEvaluationReuseTestCase,
) -> None:
    write_project_sources(
        repo_root=tmp_path,
        files=((test_case.relative_path, test_case.source),),
    )
    config: Config = exception_config(relative_path=test_case.relative_path)
    tree: DiscoveredTree = discover_project(repo_root=tmp_path)[1]
    ruleset: tuple[RuleSpec, ...] = (exception_fault_rule(),)

    cold: CacheEvaluation = evaluate_with_cache(
        tree=tree,
        ruleset=ruleset,
        config=config,
        global_fingerprint=_GLOBAL_FINGERPRINT,
    )
    warm: CacheEvaluation = evaluate_with_cache(
        tree=tree,
        ruleset=ruleset,
        config=config,
        global_fingerprint=_GLOBAL_FINGERPRINT,
    )

    assert cold.stats.hits == test_case.expected_cold_hits
    assert cold.stats.misses == test_case.expected_cold_misses
    assert warm.stats.hits == test_case.expected_warm_hits
    assert warm.stats.misses == test_case.expected_warm_misses
    assert warm.stats.writes == test_case.expected_warm_writes
    assert len(warm.result.faults) == test_case.expected_fault_count
    assert warm.result.applied_exception_count == 1


@pytest.mark.parametrize(
    "test_case",
    [
        CachedEvaluationRetentionTestCase(
            description="mixed hit and invalidation publication preserves retained entries",
            relative_paths=("src/pkg/a.py", "src/pkg/b.py"),
            edited_path="src/pkg/b.py",
            second_source="value: int = 2\n",
            expected_third_hits=2,
            expected_third_misses=0,
            expected_third_invalidations=0,
            expected_third_writes=0,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_mixed_publication_when_evaluating_again_then_reuses_retained_entries(
    tmp_path: Path,
    test_case: CachedEvaluationRetentionTestCase,
) -> None:
    write_project_sources(
        repo_root=tmp_path,
        files=tuple((path, "value: int = 1\n") for path in test_case.relative_paths),
    )
    config, tree = discover_project(repo_root=tmp_path)
    ruleset: tuple[RuleSpec, ...] = (source_fault_rule(),)
    _ = evaluate_with_cache(
        tree=tree,
        ruleset=ruleset,
        config=config,
        global_fingerprint=_GLOBAL_FINGERPRINT,
    )
    write_project_sources(
        repo_root=tmp_path,
        files=((test_case.edited_path, test_case.second_source),),
    )
    _ = evaluate_with_cache(
        tree=tree,
        ruleset=ruleset,
        config=config,
        global_fingerprint=_GLOBAL_FINGERPRINT,
    )

    third: CacheEvaluation = evaluate_with_cache(
        tree=tree,
        ruleset=ruleset,
        config=config,
        global_fingerprint=_GLOBAL_FINGERPRINT,
    )

    assert third.stats.hits == test_case.expected_third_hits
    assert third.stats.misses == test_case.expected_third_misses
    assert third.stats.invalidations == test_case.expected_third_invalidations
    assert third.stats.writes == test_case.expected_third_writes


@pytest.mark.parametrize(
    "test_case",
    [
        CachedEvaluationSweepTestCase(
            description="invalidating edit sweeps the superseded record from storage",
            relative_path="src/pkg/models.py",
            first_source="value: int = 1\n",
            second_source="value: int = 2\n",
            expected_first_record_count=1,
            expected_second_record_count=1,
            expected_shared_keys=0,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_invalidating_edit_when_publishing_then_sweeps_superseded_records(
    tmp_path: Path,
    test_case: CachedEvaluationSweepTestCase,
) -> None:
    write_project_sources(
        repo_root=tmp_path,
        files=((test_case.relative_path, test_case.first_source),),
    )
    config, tree = discover_project(repo_root=tmp_path)
    ruleset: tuple[RuleSpec, ...] = (source_fault_rule(),)
    _ = evaluate_with_cache(
        tree=tree,
        ruleset=ruleset,
        config=config,
        global_fingerprint=_GLOBAL_FINGERPRINT,
    )
    first_keys: tuple[str, ...] = result_record_keys(repo_root=tmp_path)
    write_project_sources(
        repo_root=tmp_path,
        files=((test_case.relative_path, test_case.second_source),),
    )

    _ = evaluate_with_cache(
        tree=tree,
        ruleset=ruleset,
        config=config,
        global_fingerprint=_GLOBAL_FINGERPRINT,
    )
    second_keys: tuple[str, ...] = result_record_keys(repo_root=tmp_path)

    assert len(first_keys) == test_case.expected_first_record_count
    assert len(second_keys) == test_case.expected_second_record_count
    assert len(set(first_keys) & set(second_keys)) == test_case.expected_shared_keys


@pytest.mark.parametrize(
    "test_case",
    [
        CachedEvaluationDegradationTestCase(
            description="schema-rejected fault degrades to non-cacheable with complete diagnostics",
            relative_path="src/pkg/models.py",
            source="value: int = 1\n",
            expected_misses=1,
            expected_writes=0,
            expected_non_cacheable=1,
            expected_internal_error=True,
            expected_storage_failed=False,
            expected_fault_count=1,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_schema_rejected_fault_when_evaluating_then_degrades_without_crashing(
    tmp_path: Path,
    test_case: CachedEvaluationDegradationTestCase,
) -> None:
    write_project_sources(
        repo_root=tmp_path,
        files=((test_case.relative_path, test_case.source),),
    )
    config, tree = discover_project(repo_root=tmp_path)

    degraded: CacheEvaluation = evaluate_with_cache(
        tree=tree,
        ruleset=(invalid_fault_rule(),),
        config=config,
        global_fingerprint=_GLOBAL_FINGERPRINT,
    )

    assert degraded.stats.misses == test_case.expected_misses
    assert degraded.stats.writes == test_case.expected_writes
    assert degraded.stats.non_cacheable == test_case.expected_non_cacheable
    assert degraded.stats.internal_error is test_case.expected_internal_error
    assert degraded.stats.storage_failed is test_case.expected_storage_failed
    assert len(degraded.result.faults) == test_case.expected_fault_count


@pytest.mark.parametrize(
    "test_case",
    [
        CachedEvaluationDegradationTestCase(
            description="publication error degrades to storage failure with complete diagnostics",
            relative_path="src/pkg/models.py",
            source="value: int = 1\n",
            expected_misses=0,
            expected_writes=0,
            expected_non_cacheable=0,
            expected_internal_error=True,
            expected_storage_failed=True,
            expected_fault_count=1,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_publication_error_when_evaluating_then_degrades_without_crashing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: CachedEvaluationDegradationTestCase,
) -> None:
    write_project_sources(
        repo_root=tmp_path,
        files=((test_case.relative_path, test_case.source),),
    )
    config, tree = discover_project(repo_root=tmp_path)
    install_publish_error(monkeypatch=monkeypatch)

    degraded: CacheEvaluation = evaluate_with_cache(
        tree=tree,
        ruleset=(source_fault_rule(),),
        config=config,
        global_fingerprint=_GLOBAL_FINGERPRINT,
    )

    assert degraded.stats.writes == test_case.expected_writes
    assert degraded.stats.non_cacheable == test_case.expected_non_cacheable
    assert degraded.stats.internal_error is test_case.expected_internal_error
    assert degraded.stats.storage_failed is test_case.expected_storage_failed
    assert len(degraded.result.faults) == test_case.expected_fault_count


@pytest.mark.parametrize(
    "test_case",
    [
        CachedEvaluationFailureTestCase(
            description="failed evaluation publishes no cache generation",
            relative_path="src/pkg/models.py",
            source="value: int = 1\n",
            expected_error_type=AssertionError,
            expected_cache_exists=False,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_rule_failure_when_evaluating_then_does_not_publish_cache(
    tmp_path: Path,
    test_case: CachedEvaluationFailureTestCase,
) -> None:
    write_project_sources(
        repo_root=tmp_path,
        files=((test_case.relative_path, test_case.source),),
    )
    config, tree = discover_project(repo_root=tmp_path)

    with pytest.raises(test_case.expected_error_type):
        evaluate_with_cache(
            tree=tree,
            ruleset=(failing_rule(),),
            config=config,
            global_fingerprint=_GLOBAL_FINGERPRINT,
        )

    assert (tmp_path / ".strata").exists() is test_case.expected_cache_exists
