"""Integration tests for cold, warm, and invalidated cached evaluation."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from unittest.mock import Mock

import pytest

from strata.analysis.models import ProjectDependency
from strata.cache.fingerprints.models import CacheFingerprint
from strata.cache.results.main.evaluate import evaluate_with_cache
from strata.cache.results.models import CacheEvaluation
from strata.config.models import Config, EvaluationConfig
from strata.discovery.main.discover_files import discover_files
from strata.discovery.models import DiscoveredTree
from strata.evaluation.main.evaluate import evaluate
from strata.evaluation.models import EvaluationResult, EvaluationSelection
from strata.rules.authoring.models import RuleSpec
from strata.rules.authoring.types import RuleKind
from strata.rules.naming.constants import SFN_RULES
from strata.rules.tests.constants import SFT_RULES
from tests.integration.src.strata.cache.results._test_types import (
    CachedDomainShapeInvalidationTestCase,
    CachedEvaluationDegradationTestCase,
    CachedEvaluationFailureTestCase,
    CachedEvaluationInvalidationTestCase,
    CachedEvaluationManifestTestCase,
    CachedEvaluationRetentionTestCase,
    CachedEvaluationReuseTestCase,
    CachedEvaluationSelectionTestCase,
    CachedEvaluationSweepTestCase,
    CachedGenerationConcurrencyTestCase,
    CachedLeafMainInvalidationTestCase,
    CachedNamingParityTestCase,
    CachedNativeProjectRuleTestCase,
    CachedPublicationInterruptionTestCase,
    CachedResultReadFilteringTestCase,
    CachedSemanticCorruptionTestCase,
    CachedSharedDomainPrefixInvalidationTestCase,
    CachedSymlinkDependencyTestCase,
    EditReplayDependencyTestCase,
    EditReplayFastPathTestCase,
)
from tests.integration.src.strata.cache.results.helpers import (
    arbitrary_glob_fault_rule,
    context_source_fault_rule,
    corrupt_indexed_result_record,
    dependency_fault_rule,
    discover_project,
    evaluate_cache_concurrently,
    evaluate_cache_while_database_blocked,
    evaluated_result,
    exception_config,
    exception_fault_rule,
    failing_rule,
    install_cache_write_rejection,
    install_publish_error,
    install_rule_execution_failure,
    invalid_fault_rule,
    result_record_keys,
    role_rule,
    source_fault_rule,
    write_project_sources,
)

_GLOBAL_FINGERPRINT: CacheFingerprint = CacheFingerprint("e" * 64)


@pytest.mark.parametrize(
    "test_case",
    [
        CachedEvaluationInvalidationTestCase(
            description="recursive arbitrary glob invalidates when a matching asset appears",
            relative_path="src/pkg/models.py",
            first_source="VALUE: int = 1\n",
            second_source="select 1\n",
            expected_invalidations=1,
            expected_message="orders.sql",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_cached_arbitrary_glob_when_match_appears_then_invalidates_requester(
    tmp_path: Path,
    test_case: CachedEvaluationInvalidationTestCase,
) -> None:
    write_project_sources(
        repo_root=tmp_path,
        files=((test_case.relative_path, test_case.first_source),),
    )
    (tmp_path / "assets").mkdir()
    config, tree = discover_project(repo_root=tmp_path)
    ruleset: tuple[RuleSpec, ...] = (arbitrary_glob_fault_rule(),)
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
    write_project_sources(
        repo_root=tmp_path,
        files=(("assets/nested/orders.sql", test_case.second_source),),
    )

    changed: CacheEvaluation = evaluate_with_cache(
        tree=tree,
        ruleset=ruleset,
        config=config,
        global_fingerprint=_GLOBAL_FINGERPRINT,
    )

    assert warm.stats.hits == 1
    assert evaluated_result(warm).faults == evaluated_result(cold).faults
    assert changed.stats.invalidations == test_case.expected_invalidations
    assert evaluated_result(changed).faults[0].message == test_case.expected_message


@pytest.mark.parametrize(
    "test_case",
    [
        CachedEvaluationSelectionTestCase(
            description="warm cache counts targets and invalidates on excluded context change",
            expected_discovered_count=2,
            expected_target_count=1,
            expected_cold_misses=1,
            expected_warm_hits=1,
            expected_invalidations=1,
            expected_changed_message="CONTEXT: int = 2",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_excluded_cached_dependency_when_changed_then_invalidates_selected_target(
    tmp_path: Path,
    test_case: CachedEvaluationSelectionTestCase,
) -> None:
    write_project_sources(
        repo_root=tmp_path,
        files=(
            ("src/pkg/target.py", "TARGET: int = 1\n"),
            ("src/pkg/context.py", "CONTEXT: int = 1\n"),
        ),
    )
    config: Config = Config(
        roots=("src/pkg",),
        tests=(),
        evaluation=EvaluationConfig(include=("src/pkg/target.py",)),
    )
    tree: DiscoveredTree = discover_project(repo_root=tmp_path)[1]
    ruleset: tuple[RuleSpec, ...] = (context_source_fault_rule(),)

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
    write_project_sources(
        repo_root=tmp_path,
        files=(("src/pkg/context.py", "CONTEXT: int = 2\n"),),
    )
    changed_tree: DiscoveredTree = discover_project(repo_root=tmp_path)[1]
    changed: CacheEvaluation = evaluate_with_cache(
        tree=changed_tree,
        ruleset=ruleset,
        config=config,
        global_fingerprint=_GLOBAL_FINGERPRINT,
    )

    cold_selection: EvaluationSelection | None = evaluated_result(cold).selection
    assert cold_selection is not None
    assert cold_selection.discovered_count == test_case.expected_discovered_count
    assert len(cold_selection.files) == test_case.expected_target_count
    assert cold.stats.misses == test_case.expected_cold_misses
    assert warm.stats.hits == test_case.expected_warm_hits
    assert evaluated_result(warm).faults == evaluated_result(cold).faults
    assert changed.stats.invalidations == test_case.expected_invalidations
    assert evaluated_result(changed).faults[0].message == test_case.expected_changed_message


@pytest.mark.parametrize(
    "test_case",
    [
        CachedNamingParityTestCase(
            description="all naming behaviors have byte-identical cold and warm faults",
            relative_path="src/pkg/domain/_helpers/contracts.py",
            source=(
                "def validate_item() -> int:\n    return 1\n"
                "def is_ready() -> Status:\n    return Status()\n"
                "def get_item() -> None:\n    return None\n"
                "def iter_items() -> list[int]:\n    return []\n"
            ),
            expected_codes=("SFN001", "SFN002", "SFN003", "SFN004"),
            expected_warm_hits=1,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_cached_naming_facts_when_evaluating_warm_then_preserves_exact_faults(
    tmp_path: Path,
    test_case: CachedNamingParityTestCase,
) -> None:
    write_project_sources(
        repo_root=tmp_path,
        files=((test_case.relative_path, test_case.source),),
    )
    config, tree = discover_project(repo_root=tmp_path)

    cold: CacheEvaluation = evaluate_with_cache(
        tree=tree,
        ruleset=SFN_RULES,
        config=config,
        global_fingerprint=_GLOBAL_FINGERPRINT,
    )
    warm: CacheEvaluation = evaluate_with_cache(
        tree=tree,
        ruleset=SFN_RULES,
        config=config,
        global_fingerprint=_GLOBAL_FINGERPRINT,
    )

    assert tuple(fault.code for fault in evaluated_result(cold).faults) == test_case.expected_codes
    assert warm.stats.hits == test_case.expected_warm_hits
    assert evaluated_result(warm).faults == evaluated_result(cold).faults


@pytest.mark.parametrize(
    "test_case",
    [
        CachedNativeProjectRuleTestCase(
            description="native project dependency is cacheable and reused",
            target_path="tests/unit/src/pkg/domain/test_models.py",
            source_path="src/pkg/domain/models.py",
            expected_code="SFT204",
            expected_dependency_kind="is_file",
            expected_dependency_answer=False,
            expected_cold_misses=1,
            expected_warm_hits=1,
            expected_non_cacheable=0,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_native_project_dependency_when_evaluating_warm_then_reuses_exact_result(
    tmp_path: Path,
    test_case: CachedNativeProjectRuleTestCase,
) -> None:
    write_project_sources(
        repo_root=tmp_path,
        files=(
            (test_case.source_path, "value: int = 1\n"),
            (test_case.target_path, ""),
        ),
    )
    config: Config = Config(
        roots=("src/pkg",),
        tests=("tests",),
        evaluation=EvaluationConfig(include=(test_case.target_path,)),
    )
    tree: DiscoveredTree = discover_files(config=config, repo_root=tmp_path)
    rules_by_code: dict[str, RuleSpec] = {rule.code: rule for rule in SFT_RULES}
    python_callback: Mock = Mock(side_effect=AssertionError("Python callback executed"))
    ruleset: tuple[RuleSpec, ...] = (
        replace(rules_by_code[test_case.expected_code], check=python_callback),
    )

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

    cold_result: EvaluationResult = evaluated_result(cold)
    dependency: ProjectDependency = cold_result.dependencies[0]
    assert tuple(fault.code for fault in cold_result.faults) == (test_case.expected_code,)
    assert dependency.requester.relative_to(tmp_path).as_posix() == test_case.target_path
    assert dependency.kind == test_case.expected_dependency_kind
    assert dependency.answer is test_case.expected_dependency_answer
    assert cold.stats.misses == test_case.expected_cold_misses
    assert cold.stats.non_cacheable == test_case.expected_non_cacheable
    assert warm.stats.hits == test_case.expected_warm_hits
    assert warm.stats.non_cacheable == test_case.expected_non_cacheable
    assert evaluated_result(warm) == cold_result
    assert python_callback.call_count == 0


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
    assert len(evaluated_result(warm).faults) == test_case.expected_fault_count
    assert evaluated_result(warm).faults == evaluated_result(cold).faults


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
    assert evaluated_result(changed).faults[0].message == test_case.expected_message


@pytest.mark.parametrize(
    "test_case",
    [
        CachedResultReadFilteringTestCase(
            description="one changed source replays unchanged files without result reads",
            initial_files=(
                ("src/pkg/alpha.py", "VALUE: int = 1\n"),
                ("src/pkg/bravo.py", "VALUE: int = 1\n"),
                ("src/pkg/charlie.py", "VALUE: int = 1\n"),
                ("src/pkg/delta.py", "VALUE: int = 1\n"),
            ),
            changed_files=(("src/pkg/alpha.py", "VALUE: int = 2\n"),),
            expected_loaded_paths=(),
            expected_invalidations=1,
        ),
        CachedResultReadFilteringTestCase(
            description="three changed sources replay unchanged files without result reads",
            initial_files=(
                ("src/pkg/alpha.py", "VALUE: int = 1\n"),
                ("src/pkg/bravo.py", "VALUE: int = 1\n"),
                ("src/pkg/charlie.py", "VALUE: int = 1\n"),
                ("src/pkg/delta.py", "VALUE: int = 1\n"),
            ),
            changed_files=(
                ("src/pkg/alpha.py", "VALUE: int = 2\n"),
                ("src/pkg/bravo.py", "VALUE: int = 2\n"),
                ("src/pkg/charlie.py", "VALUE: int = 2\n"),
            ),
            expected_loaded_paths=(),
            expected_invalidations=3,
        ),
        CachedResultReadFilteringTestCase(
            description="all changed sources are rejected before old result records are read",
            initial_files=(
                ("src/pkg/alpha.py", "VALUE: int = 1\n"),
                ("src/pkg/bravo.py", "VALUE: int = 1\n"),
                ("src/pkg/charlie.py", "VALUE: int = 1\n"),
                ("src/pkg/delta.py", "VALUE: int = 1\n"),
            ),
            changed_files=(
                ("src/pkg/alpha.py", "VALUE: int = 2\n"),
                ("src/pkg/bravo.py", "VALUE: int = 2\n"),
                ("src/pkg/charlie.py", "VALUE: int = 2\n"),
                ("src/pkg/delta.py", "VALUE: int = 2\n"),
            ),
            expected_loaded_paths=(),
            expected_invalidations=4,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_changed_sources_when_loading_cache_then_reads_only_source_equal_results(
    tmp_path: Path,
    test_case: CachedResultReadFilteringTestCase,
) -> None:
    write_project_sources(repo_root=tmp_path, files=test_case.initial_files)
    config, tree = discover_project(repo_root=tmp_path)
    ruleset: tuple[RuleSpec, ...] = (source_fault_rule(),)
    _ = evaluate_with_cache(
        tree=tree,
        ruleset=ruleset,
        config=config,
        global_fingerprint=_GLOBAL_FINGERPRINT,
    )
    write_project_sources(repo_root=tmp_path, files=test_case.changed_files)
    changed: CacheEvaluation = evaluate_with_cache(
        tree=tree,
        ruleset=ruleset,
        config=config,
        global_fingerprint=_GLOBAL_FINGERPRINT,
    )
    uncached: EvaluationResult = evaluate(tree=tree, ruleset=ruleset, config=config)

    assert changed.stats.invalidations == test_case.expected_invalidations
    assert evaluated_result(changed).faults == uncached.faults


@pytest.mark.parametrize(
    "test_case",
    [
        EditReplayDependencyTestCase(
            description="editing a queried file recomputes every dependent result",
            initial_context_source="CONTEXT: int = 1\n",
            changed_context_source="CONTEXT: int = 2\n",
            expected_invalidations=2,
            expected_messages=("CONTEXT: int = 2", "CONTEXT: int = 2"),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_edited_queried_file_when_replaying_then_recomputes_dependents(
    tmp_path: Path,
    test_case: EditReplayDependencyTestCase,
) -> None:
    write_project_sources(
        repo_root=tmp_path,
        files=(
            ("src/pkg/context.py", test_case.initial_context_source),
            ("src/pkg/target.py", "TARGET: int = 1\n"),
        ),
    )
    config, tree = discover_project(repo_root=tmp_path)
    ruleset: tuple[RuleSpec, ...] = (context_source_fault_rule(),)
    _ = evaluate_with_cache(
        tree=tree,
        ruleset=ruleset,
        config=config,
        global_fingerprint=_GLOBAL_FINGERPRINT,
    )
    write_project_sources(
        repo_root=tmp_path,
        files=(("src/pkg/context.py", test_case.changed_context_source),),
    )
    changed_tree: DiscoveredTree = discover_project(repo_root=tmp_path)[1]

    changed: CacheEvaluation = evaluate_with_cache(
        tree=changed_tree,
        ruleset=ruleset,
        config=config,
        global_fingerprint=_GLOBAL_FINGERPRINT,
    )

    assert changed.stats.invalidations == test_case.expected_invalidations
    assert (
        tuple(fault.message for fault in evaluated_result(changed).faults)
        == test_case.expected_messages
    )


@pytest.mark.parametrize(
    "test_case",
    [
        EditReplayFastPathTestCase(
            description="independent edit replays unchanged results without record reads",
            initial_target_source="TARGET: int = 1\n",
            changed_target_source="TARGET: int = 2\n",
            expected_invalidations=1,
            expected_loaded_paths=(),
            expected_messages=("CONTEXT: int = 1", "CONTEXT: int = 1"),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_independent_edit_when_replaying_then_skips_unchanged_record_reads(
    tmp_path: Path,
    test_case: EditReplayFastPathTestCase,
) -> None:
    write_project_sources(
        repo_root=tmp_path,
        files=(
            ("src/pkg/context.py", "CONTEXT: int = 1\n"),
            ("src/pkg/target.py", test_case.initial_target_source),
        ),
    )
    config, tree = discover_project(repo_root=tmp_path)
    ruleset: tuple[RuleSpec, ...] = (context_source_fault_rule(),)
    _ = evaluate_with_cache(
        tree=tree,
        ruleset=ruleset,
        config=config,
        global_fingerprint=_GLOBAL_FINGERPRINT,
    )
    write_project_sources(
        repo_root=tmp_path,
        files=(("src/pkg/target.py", test_case.changed_target_source),),
    )
    changed_tree: DiscoveredTree = discover_project(repo_root=tmp_path)[1]
    changed: CacheEvaluation = evaluate_with_cache(
        tree=changed_tree,
        ruleset=ruleset,
        config=config,
        global_fingerprint=_GLOBAL_FINGERPRINT,
    )

    assert changed.stats.invalidations == test_case.expected_invalidations
    assert (
        tuple(fault.message for fault in evaluated_result(changed).faults)
        == test_case.expected_messages
    )


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
    assert evaluated_result(changed).faults[0].message == test_case.expected_message


@pytest.mark.parametrize(
    "test_case",
    [
        CachedDomainShapeInvalidationTestCase(
            description="Python source appearing in asset directory invalidates cached SFR306",
            role_relative_path="src/pkg/domain/models.py",
            asset_relative_path="src/pkg/domain/assets/records.json",
            namespace_relative_path="src/pkg/domain/assets/models.py",
            expected_initial_codes=(),
            expected_invalidations=1,
            expected_misses=1,
            expected_changed_codes=("SFR306",),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_cached_leaf_when_asset_directory_gains_python_then_invalidates_domain_shape(
    tmp_path: Path,
    test_case: CachedDomainShapeInvalidationTestCase,
) -> None:
    write_project_sources(
        repo_root=tmp_path,
        files=(
            (test_case.role_relative_path, ""),
            (test_case.asset_relative_path, "[]\n"),
        ),
    )
    config, initial_tree = discover_project(repo_root=tmp_path)
    sfr306: RuleSpec = role_rule(code="SFR306")
    ruleset: tuple[RuleSpec, ...] = (sfr306,)
    initial: CacheEvaluation = evaluate_with_cache(
        tree=initial_tree,
        ruleset=ruleset,
        config=config,
        global_fingerprint=_GLOBAL_FINGERPRINT,
    )
    write_project_sources(
        repo_root=tmp_path,
        files=((test_case.namespace_relative_path, ""),),
    )
    final_tree: DiscoveredTree = discover_project(repo_root=tmp_path)[1]

    changed: CacheEvaluation = evaluate_with_cache(
        tree=final_tree,
        ruleset=ruleset,
        config=config,
        global_fingerprint=_GLOBAL_FINGERPRINT,
    )

    assert (
        tuple(fault.code for fault in evaluated_result(initial).faults)
        == test_case.expected_initial_codes
    )
    assert changed.stats.invalidations == test_case.expected_invalidations
    assert changed.stats.misses == test_case.expected_misses
    assert (
        tuple(fault.code for fault in evaluated_result(changed).faults)
        == test_case.expected_changed_codes
    )


@pytest.mark.parametrize(
    "test_case",
    [
        CachedLeafMainInvalidationTestCase(
            description="added main entry invalidates cached SFR309",
            role_relative_path="src/pkg/domain/models.py",
            main_relative_path="src/pkg/domain/main/run.py",
            expected_initial_codes=("SFR309",),
            expected_invalidations=1,
            expected_misses=1,
            expected_changed_codes=(),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_cached_leaf_when_main_entry_appears_then_invalidates_main_boundary(
    tmp_path: Path,
    test_case: CachedLeafMainInvalidationTestCase,
) -> None:
    write_project_sources(
        repo_root=tmp_path,
        files=((test_case.role_relative_path, ""),),
    )
    config, initial_tree = discover_project(repo_root=tmp_path)
    sfr309: RuleSpec = role_rule(code="SFR309")
    ruleset: tuple[RuleSpec, ...] = (sfr309,)
    initial: CacheEvaluation = evaluate_with_cache(
        tree=initial_tree,
        ruleset=ruleset,
        config=config,
        global_fingerprint=_GLOBAL_FINGERPRINT,
    )
    write_project_sources(
        repo_root=tmp_path,
        files=((test_case.main_relative_path, "def run() -> None:\n    return None\n"),),
    )
    final_tree: DiscoveredTree = discover_project(repo_root=tmp_path)[1]

    changed: CacheEvaluation = evaluate_with_cache(
        tree=final_tree,
        ruleset=ruleset,
        config=config,
        global_fingerprint=_GLOBAL_FINGERPRINT,
    )

    assert (
        tuple(fault.code for fault in evaluated_result(initial).faults)
        == test_case.expected_initial_codes
    )
    assert changed.stats.invalidations == test_case.expected_invalidations
    assert changed.stats.misses == test_case.expected_misses
    assert (
        tuple(fault.code for fault in evaluated_result(changed).faults)
        == test_case.expected_changed_codes
    )


@pytest.mark.parametrize(
    "test_case",
    [
        CachedSharedDomainPrefixInvalidationTestCase(
            description="added sibling domain invalidates cached shared-prefix result",
            first_domain_path="src/pkg/annotation_export/__init__.py",
            second_domain_path="src/pkg/annotation_validation/__init__.py",
            expected_initial_codes=(),
            expected_invalidations=1,
            expected_changed_codes=("SFR308",),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_cached_domain_when_matching_sibling_is_added_then_invalidates_prefix_result(
    tmp_path: Path,
    test_case: CachedSharedDomainPrefixInvalidationTestCase,
) -> None:
    write_project_sources(
        repo_root=tmp_path,
        files=(
            ("src/pkg/__init__.py", ""),
            (test_case.first_domain_path, ""),
        ),
    )
    config, initial_tree = discover_project(repo_root=tmp_path)
    ruleset: tuple[RuleSpec, ...] = (role_rule(code="SFR308"),)
    initial: CacheEvaluation = evaluate_with_cache(
        tree=initial_tree,
        ruleset=ruleset,
        config=config,
        global_fingerprint=_GLOBAL_FINGERPRINT,
    )
    write_project_sources(
        repo_root=tmp_path,
        files=((test_case.second_domain_path, ""),),
    )
    final_tree: DiscoveredTree = discover_project(repo_root=tmp_path)[1]

    changed: CacheEvaluation = evaluate_with_cache(
        tree=final_tree,
        ruleset=ruleset,
        config=config,
        global_fingerprint=_GLOBAL_FINGERPRINT,
    )

    assert (
        tuple(fault.code for fault in evaluated_result(initial).faults)
        == test_case.expected_initial_codes
    )
    assert changed.stats.invalidations == test_case.expected_invalidations
    assert (
        tuple(fault.code for fault in evaluated_result(changed).faults)
        == test_case.expected_changed_codes
    )


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
    assert tuple(fault.path.name for fault in evaluated_result(changed).faults) == (
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
    assert len(evaluated_result(warm).faults) == test_case.expected_fault_count
    assert evaluated_result(warm).faults == evaluated_result(cold).faults
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
    assert len(evaluated_result(second).faults) == test_case.expected_fault_count
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
    assert len(evaluated_result(warm).faults) == test_case.expected_fault_count
    assert evaluated_result(warm).applied_exception_count == 1


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
    assert len(evaluated_result(degraded).faults) == test_case.expected_fault_count


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
    assert len(evaluated_result(degraded).faults) == test_case.expected_fault_count


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


@pytest.mark.parametrize(
    "test_case",
    [
        CachedSemanticCorruptionTestCase(
            description="resealed result corruption is rejected against the indexed identity",
            relative_path="src/pkg/models.py",
            source="value: int = 1\n",
            expected_misses=1,
            expected_writes=1,
            expected_fault_count=1,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_resealed_result_corruption_when_evaluating_then_regenerates_complete_result(
    tmp_path: Path,
    test_case: CachedSemanticCorruptionTestCase,
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
    corrupt_indexed_result_record(repo_root=tmp_path)

    repaired: CacheEvaluation = evaluate_with_cache(
        tree=tree,
        ruleset=ruleset,
        config=config,
        global_fingerprint=_GLOBAL_FINGERPRINT,
    )

    assert repaired.stats.misses == test_case.expected_misses
    assert repaired.stats.writes == test_case.expected_writes
    assert len(evaluated_result(repaired).faults) == test_case.expected_fault_count
    assert evaluated_result(repaired).faults == evaluated_result(cold).faults


@pytest.mark.parametrize(
    "test_case",
    [
        CachedGenerationConcurrencyTestCase(
            description="concurrent cold publishers leave one complete reusable generation",
            relative_paths=("src/pkg/alpha.py", "src/pkg/bravo.py"),
            writer_count=4,
            expected_warm_hits=2,
            expected_fault_count=2,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_concurrent_cold_publications_when_loading_warm_then_generation_is_complete(
    tmp_path: Path,
    test_case: CachedGenerationConcurrencyTestCase,
) -> None:
    write_project_sources(
        repo_root=tmp_path,
        files=tuple((path, "value: int = 1\n") for path in test_case.relative_paths),
    )
    config, tree = discover_project(repo_root=tmp_path)
    ruleset: tuple[RuleSpec, ...] = (source_fault_rule(),)

    concurrent: tuple[CacheEvaluation, ...] = evaluate_cache_concurrently(
        tree=tree,
        ruleset=ruleset,
        config=config,
        global_fingerprint=_GLOBAL_FINGERPRINT,
        writer_count=test_case.writer_count,
    )
    warm: CacheEvaluation = evaluate_with_cache(
        tree=tree,
        ruleset=ruleset,
        config=config,
        global_fingerprint=_GLOBAL_FINGERPRINT,
    )

    assert len(concurrent) == test_case.writer_count
    assert warm.stats.hits == test_case.expected_warm_hits
    assert len(evaluated_result(warm).faults) == test_case.expected_fault_count
    assert all(
        evaluated_result(result).faults == evaluated_result(warm).faults for result in concurrent
    )


@pytest.mark.parametrize(
    "test_case",
    [
        CachedSymlinkDependencyTestCase(
            description="retargeted custom source dependency invalidates its requester",
            requester_path="src/pkg/target.py",
            first_context_path="src/pkg/context_a.py",
            second_context_path="src/pkg/context_b.py",
            expected_warm_hits=1,
            expected_invalidations=1,
            expected_changed_message="CONTEXT: int = 2",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_cached_symlink_dependency_when_retargeted_then_invalidates_requester(
    tmp_path: Path,
    test_case: CachedSymlinkDependencyTestCase,
) -> None:
    write_project_sources(
        repo_root=tmp_path,
        files=(
            (test_case.requester_path, "TARGET: int = 1\n"),
            (test_case.first_context_path, "CONTEXT: int = 1\n"),
            (test_case.second_context_path, "CONTEXT: int = 2\n"),
        ),
    )
    context: Path = tmp_path / "src/pkg/context.py"
    context.symlink_to(Path(test_case.first_context_path).name)
    config: Config = Config(
        roots=("src/pkg",),
        tests=(),
        evaluation=EvaluationConfig(include=(test_case.requester_path,)),
    )
    tree: DiscoveredTree = discover_project(repo_root=tmp_path)[1]
    ruleset: tuple[RuleSpec, ...] = (context_source_fault_rule(),)
    _ = evaluate_with_cache(
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
    context.unlink()
    context.symlink_to(Path(test_case.second_context_path).name)

    changed: CacheEvaluation = evaluate_with_cache(
        tree=tree,
        ruleset=ruleset,
        config=config,
        global_fingerprint=_GLOBAL_FINGERPRINT,
    )

    assert warm.stats.hits == test_case.expected_warm_hits
    assert changed.stats.invalidations == test_case.expected_invalidations
    assert evaluated_result(changed).faults[0].message == test_case.expected_changed_message


@pytest.mark.parametrize(
    "test_case",
    [
        CachedPublicationInterruptionTestCase(
            description="blocked changed publication preserves the prior complete generation",
            relative_path="src/pkg/models.py",
            first_source="value: int = 1\n",
            second_source="value: int = 2\n",
            expected_storage_failed=True,
            expected_interrupted_writes=0,
            expected_restored_hits=1,
            expected_restored_message="value: int = 1",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_blocked_generation_publication_when_restoring_source_then_prior_cache_is_reusable(
    tmp_path: Path,
    test_case: CachedPublicationInterruptionTestCase,
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
    interrupted: CacheEvaluation = evaluate_cache_while_database_blocked(
        tree=tree,
        ruleset=ruleset,
        config=config,
        global_fingerprint=_GLOBAL_FINGERPRINT,
    )
    write_project_sources(
        repo_root=tmp_path,
        files=((test_case.relative_path, test_case.first_source),),
    )

    restored: CacheEvaluation = evaluate_with_cache(
        tree=tree,
        ruleset=ruleset,
        config=config,
        global_fingerprint=_GLOBAL_FINGERPRINT,
    )

    assert interrupted.stats.storage_failed is test_case.expected_storage_failed
    assert interrupted.stats.writes == test_case.expected_interrupted_writes
    assert restored.stats.hits == test_case.expected_restored_hits
    assert evaluated_result(restored).faults[0].message == test_case.expected_restored_message
