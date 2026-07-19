"""Tests for persistent lazy call-map declarations."""

from io import StringIO
from pathlib import Path
from unittest.mock import Mock

import pytest

from fensu.analysis._helpers import building
from fensu.cache.mapping.models import CachedCallMap
from fensu.cache.storage.constants import CACHE_DATABASE_RELATIVE_PATH
from fensu.cli.main._map import run_map
from fensu.mapping.exceptions import MapError
from fensu.mapping.main.native import build_native_call_map
from fensu.mapping.main.render import render_call_tree
from fensu.mapping.models import MappingSource
from fensu.mapping.types import PathMode
from tests.integration.src.fensu.cache.mapping._test_types import (
    ConcurrentRetentionTestCase,
    ExplicitRootCachePreferenceTestCase,
    InvalidExplicitRootConfigTestCase,
    ManifestAdversarialTestCase,
    MapAnalysisOwnershipTestCase,
    MapCacheInvalidationTestCase,
    MapCacheTestCase,
    MapNoCacheTestCase,
    MapParseParityTestCase,
    MappingIdentityFailureTestCase,
    MapSourceEncodingTestCase,
    PathSelectorParityTestCase,
)
from tests.integration.src.fensu.cache.mapping.helpers import (
    cached_map,
    cached_symbol_map,
    current_file_record_count,
    direct_ast_parse_paths,
    explicit_root_argv,
    fail_mapping_identity,
    install_generation_sweep_interleaving,
    invalid_config_root_argv,
    mutate_file_record,
    mutate_manifest,
    path_selector_spelling,
    render_cached,
    write_disabled_cache_config,
    write_invalid_cache_config,
    write_mapping_project,
)


@pytest.mark.parametrize(
    "test_case",
    [
        MapCacheTestCase(
            description="warm manifest lazily parses only reachable files",
            expected_cold_manifest_hit=False,
            expected_warm_manifest_hit=True,
            expected_warm_parsed_files=2,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_unchanged_project_when_mapping_twice_then_reuses_manifest_lazily(
    tmp_path: Path, test_case: MapCacheTestCase
) -> None:
    source: MappingSource = write_mapping_project(tmp_path)

    cold: CachedCallMap = cached_map(root=tmp_path, source=source)
    warm: CachedCallMap = cached_map(root=tmp_path, source=source)

    assert cold.stats.manifest_hit is test_case.expected_cold_manifest_hit
    assert warm.stats.manifest_hit is test_case.expected_warm_manifest_hit
    assert warm.stats.parsed_files == test_case.expected_warm_parsed_files
    assert render_cached(root=tmp_path, cached=cold) == render_cached(root=tmp_path, cached=warm)


@pytest.mark.parametrize(
    "test_case",
    [
        MapCacheInvalidationTestCase(
            description="one changed reached file reuses unchanged declaration records",
            changed_source="def step():\n    return 3\n",
            expected_reused_file_records=2,
            expected_output_fragment="step(...)  src/pkg/steps.py:1",
            expected_writes=2,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_one_file_edit_when_mapping_then_rebuilds_only_changed_metadata(
    tmp_path: Path, test_case: MapCacheInvalidationTestCase
) -> None:
    source: MappingSource = write_mapping_project(tmp_path)
    _ = cached_map(root=tmp_path, source=source)
    (tmp_path / "src/pkg/steps.py").write_text(test_case.changed_source, encoding="utf-8")

    changed: CachedCallMap = cached_map(root=tmp_path, source=source)

    assert changed.stats.reused_file_records == test_case.expected_reused_file_records
    assert changed.stats.writes == test_case.expected_writes
    assert test_case.expected_output_fragment in render_cached(root=tmp_path, cached=changed)


@pytest.mark.parametrize(
    "test_case",
    [
        MapCacheInvalidationTestCase(
            description="successive edits retain every unchanged declaration record",
            changed_source="def unused():\n    return 4\n",
            expected_reused_file_records=2,
            expected_output_fragment="run(...)  src/pkg/entry.py:3",
            expected_writes=2,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_successive_file_edits_when_mapping_then_each_reuses_other_file_records(
    tmp_path: Path, test_case: MapCacheInvalidationTestCase
) -> None:
    source: MappingSource = write_mapping_project(tmp_path)
    _ = cached_map(root=tmp_path, source=source)
    (tmp_path / "src/pkg/steps.py").write_text("def step():\n    return 3\n", encoding="utf-8")
    first: CachedCallMap = cached_map(root=tmp_path, source=source)
    (tmp_path / "src/pkg/unused.py").write_text(test_case.changed_source, encoding="utf-8")

    second: CachedCallMap = cached_map(root=tmp_path, source=source)

    assert first.stats.reused_file_records == test_case.expected_reused_file_records
    assert second.stats.reused_file_records == test_case.expected_reused_file_records
    assert first.stats.writes == test_case.expected_writes
    assert second.stats.writes == test_case.expected_writes
    assert test_case.expected_output_fragment in render_cached(root=tmp_path, cached=second)


@pytest.mark.parametrize(
    "test_case",
    [
        ConcurrentRetentionTestCase(
            description="concurrent sweep of reused record is repaired transactionally",
            expected_reused_file_records=2,
            expected_publication_writes=3,
            expected_file_record_count=3,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_reused_record_swept_before_publication_when_mapping_then_repairs_generation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: ConcurrentRetentionTestCase,
) -> None:
    source: MappingSource = write_mapping_project(tmp_path)
    _ = cached_map(root=tmp_path, source=source)
    (tmp_path / "src/pkg/steps.py").write_text("def step():\n    return 3\n", encoding="utf-8")
    install_generation_sweep_interleaving(monkeypatch)

    changed: CachedCallMap = cached_map(root=tmp_path, source=source)

    assert changed.stats.reused_file_records == test_case.expected_reused_file_records
    assert changed.stats.writes == test_case.expected_publication_writes
    assert current_file_record_count(tmp_path) == test_case.expected_file_record_count


@pytest.mark.parametrize(
    "test_case",
    [
        ManifestAdversarialTestCase(
            description="omitted function locator misses and heals",
            mutation="omit-function",
            expected_manifest_hit=False,
            expected_reused_file_records=3,
        ),
        ManifestAdversarialTestCase(
            description="redirected function locator misses and heals",
            mutation="redirect-function",
            expected_manifest_hit=False,
            expected_reused_file_records=3,
        ),
        ManifestAdversarialTestCase(
            description="redirected class locator misses and heals",
            mutation="redirect-class",
            expected_manifest_hit=False,
            expected_reused_file_records=3,
        ),
        ManifestAdversarialTestCase(
            description="mutated bare index misses and heals",
            mutation="mutate-bare",
            expected_manifest_hit=False,
            expected_reused_file_records=3,
        ),
        ManifestAdversarialTestCase(
            description="redirected protocol index misses and heals",
            mutation="redirect-protocol",
            expected_manifest_hit=False,
            expected_reused_file_records=3,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_integrity_valid_inconsistent_manifest_when_mapping_then_misses_and_heals(
    tmp_path: Path, test_case: ManifestAdversarialTestCase
) -> None:
    source: MappingSource = write_mapping_project(tmp_path)
    _ = cached_map(root=tmp_path, source=source)
    mutate_manifest(root=tmp_path, mutation=test_case.mutation)

    healed: CachedCallMap = cached_map(root=tmp_path, source=source)
    warm: CachedCallMap = cached_map(root=tmp_path, source=source)

    assert healed.stats.manifest_hit is test_case.expected_manifest_hit
    assert healed.stats.reused_file_records == test_case.expected_reused_file_records
    assert warm.stats.manifest_hit is True


@pytest.mark.parametrize(
    "test_case",
    [
        ManifestAdversarialTestCase(
            description="redirected file record misses and heals during partial rebuild",
            mutation="redirect-file",
            expected_manifest_hit=False,
            expected_reused_file_records=1,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_integrity_valid_redirected_file_record_when_rebuilding_then_reparses_and_heals(
    tmp_path: Path, test_case: ManifestAdversarialTestCase
) -> None:
    source: MappingSource = write_mapping_project(tmp_path)
    _ = cached_map(root=tmp_path, source=source)
    mutate_file_record(root=tmp_path)
    (tmp_path / "src/pkg/steps.py").write_text("def step():\n    return 3\n", encoding="utf-8")

    healed: CachedCallMap = cached_map(root=tmp_path, source=source)
    warm: CachedCallMap = cached_map(root=tmp_path, source=source)

    assert healed.stats.manifest_hit is test_case.expected_manifest_hit
    assert healed.stats.reused_file_records == test_case.expected_reused_file_records
    assert warm.stats.manifest_hit is True


@pytest.mark.parametrize(
    "test_case",
    [
        PathSelectorParityTestCase(
            description="relative path selector preserves cached parity",
            absolute=False,
            expected_output_fragment="run(...)  src/pkg/entry.py:3",
        ),
        PathSelectorParityTestCase(
            description="absolute path selector preserves cached parity",
            absolute=True,
            expected_output_fragment="run(...)  src/pkg/entry.py:3",
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_path_selector_when_mapping_cached_then_matches_uncached_output(
    tmp_path: Path, test_case: PathSelectorParityTestCase
) -> None:
    source: MappingSource = write_mapping_project(tmp_path)
    selected_path: Path = tmp_path / "src/pkg/entry.py"
    path_spelling: str = path_selector_spelling(path=selected_path, absolute=test_case.absolute)
    symbol: str = f"{path_spelling}::run"

    uncached_output: str = render_call_tree(
        root=build_native_call_map(sources=(source,), symbol=symbol, depth=2),
        repo_root=tmp_path,
        path_mode=PathMode.RELATIVE,
        use_color=False,
    )
    cached: CachedCallMap = cached_symbol_map(root=tmp_path, source=source, symbol=symbol)
    cached_output: str = render_cached(root=tmp_path, cached=cached)

    assert cached_output == uncached_output
    assert test_case.expected_output_fragment in cached_output


@pytest.mark.parametrize(
    "test_case",
    [
        MapCacheInvalidationTestCase(
            description="currently invalid changed source is never masked by old metadata",
            changed_source="def step(:\n",
            expected_reused_file_records=0,
            expected_output_fragment="Could not parse",
            expected_writes=0,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_invalid_changed_source_when_mapping_then_raises_map_error(
    tmp_path: Path, test_case: MapCacheInvalidationTestCase
) -> None:
    source: MappingSource = write_mapping_project(tmp_path)
    _ = cached_map(root=tmp_path, source=source)
    (tmp_path / "src/pkg/steps.py").write_text(test_case.changed_source, encoding="utf-8")

    with pytest.raises(MapError, match=test_case.expected_output_fragment):
        _ = cached_map(root=tmp_path, source=source)


@pytest.mark.parametrize(
    "test_case",
    [
        MapParseParityTestCase(
            description="native map rejects invalid encoding without a CPython parser",
            changed_source=b"value = '\xff'\n",
            expected_error="invalid or missing encoding declaration",
            expected_direct_parse_paths=(),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_invalid_snapshot_when_mapping_then_preserves_error_and_shared_parse_ownership(
    tmp_path: Path, test_case: MapParseParityTestCase
) -> None:
    source: MappingSource = write_mapping_project(tmp_path)
    invalid_path: Path = tmp_path / "src/pkg/steps.py"
    invalid_path.write_bytes(test_case.changed_source)

    with pytest.raises(MapError) as error:
        _ = cached_map(root=tmp_path, source=source)
    direct_parse_paths: tuple[str, ...] = direct_ast_parse_paths(root=Path("src/fensu/mapping"))

    assert str(error.value) == f"Could not parse {invalid_path}: {test_case.expected_error}"
    assert direct_parse_paths == test_case.expected_direct_parse_paths


@pytest.mark.parametrize(
    "test_case",
    [
        MapSourceEncodingTestCase(
            description="cached map accepts UTF-8 BOM source",
            source=(b"\xef\xbb\xbffrom pkg.steps import step\n\ndef run():\n    step()\n"),
            expected_output_fragment="run(...)  src/pkg/entry.py:3",
        ),
        MapSourceEncodingTestCase(
            description="cached map accepts PEP 263 Latin-1 source",
            source=(
                b"# coding: latin-1\nfrom pkg.steps import step\n\ndef run():\n"
                b"    label = 'caf\xe9'\n    step()\n"
            ),
            expected_output_fragment="run(...)  src/pkg/entry.py:4",
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_python_encoded_source_when_mapping_cached_then_preserves_output(
    tmp_path: Path, test_case: MapSourceEncodingTestCase
) -> None:
    source: MappingSource = write_mapping_project(tmp_path)
    (tmp_path / "src/pkg/entry.py").write_bytes(test_case.source)

    result: CachedCallMap = cached_map(root=tmp_path, source=source)

    assert test_case.expected_output_fragment in render_cached(root=tmp_path, cached=result)


@pytest.mark.parametrize(
    "test_case",
    [
        MapAnalysisOwnershipTestCase(
            description="mapping consumes parsed module without building full analysis",
            expected_output_fragment="run(...)  src/pkg/entry.py:3",
            expected_analysis_build_count=0,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_mapping_snapshot_when_indexing_then_does_not_build_analysis(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: MapAnalysisOwnershipTestCase,
) -> None:
    source: MappingSource = write_mapping_project(tmp_path)
    analysis_build_spy: Mock = Mock(side_effect=AssertionError("mapping built full analysis"))
    monkeypatch.setattr(building, "index_module_nodes", analysis_build_spy)

    result: CachedCallMap = cached_map(root=tmp_path, source=source)

    assert analysis_build_spy.call_count == test_case.expected_analysis_build_count
    assert test_case.expected_output_fragment in render_cached(root=tmp_path, cached=result)


@pytest.mark.parametrize(
    "test_case",
    [
        MapNoCacheTestCase(
            description="explicit no-cache does not create cache storage",
            argv=("run", "--no-cache"),
            expected_exit_code=0,
            expected_cache_exists=False,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_no_cache_flag_when_mapping_then_does_not_modify_cache(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, test_case: MapNoCacheTestCase
) -> None:
    _ = write_mapping_project(tmp_path)
    monkeypatch.chdir(tmp_path)

    exit_code: int = run_map(argv=test_case.argv)

    assert exit_code == test_case.expected_exit_code
    assert (tmp_path / CACHE_DATABASE_RELATIVE_PATH).exists() is test_case.expected_cache_exists


@pytest.mark.parametrize(
    "test_case",
    [
        ExplicitRootCachePreferenceTestCase(
            description="explicit root honors local disabled cache preference",
            invocation_subdirectory=".",
            cache_override=False,
            expected_cache_exists=False,
        ),
        ExplicitRootCachePreferenceTestCase(
            description="explicit root honors inherited disabled cache preference",
            invocation_subdirectory="nested",
            cache_override=False,
            expected_cache_exists=False,
        ),
        ExplicitRootCachePreferenceTestCase(
            description="explicit cache flag overrides disabled preference",
            invocation_subdirectory="nested",
            cache_override=True,
            expected_cache_exists=True,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_explicit_root_when_config_controls_cache_then_scans_only_explicit_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: ExplicitRootCachePreferenceTestCase,
) -> None:
    _ = write_mapping_project(tmp_path)
    write_disabled_cache_config(tmp_path)
    invocation: Path = tmp_path / test_case.invocation_subdirectory
    invocation.mkdir(exist_ok=True)
    monkeypatch.chdir(invocation)
    stdout: StringIO = StringIO()
    stderr: StringIO = StringIO()

    exit_code: int = run_map(
        argv=explicit_root_argv(root=tmp_path, cache_override=test_case.cache_override),
        stdout=stdout,
        stderr=stderr,
    )

    assert exit_code == 0
    assert "run(...)" in stdout.getvalue()
    assert (tmp_path / CACHE_DATABASE_RELATIVE_PATH).exists() is test_case.expected_cache_exists


@pytest.mark.parametrize(
    "test_case",
    [
        InvalidExplicitRootConfigTestCase(
            description="invalid local config defaults explicit-root cache to enabled",
            invocation_subdirectory=".",
            no_cache=False,
            expected_cache_exists=True,
        ),
        InvalidExplicitRootConfigTestCase(
            description="invalid inherited config defaults explicit-root cache to enabled",
            invocation_subdirectory="nested",
            no_cache=False,
            expected_cache_exists=True,
        ),
        InvalidExplicitRootConfigTestCase(
            description="no-cache maps despite invalid local config without storage",
            invocation_subdirectory=".",
            no_cache=True,
            expected_cache_exists=False,
        ),
        InvalidExplicitRootConfigTestCase(
            description="no-cache maps despite invalid inherited config without storage",
            invocation_subdirectory="nested",
            no_cache=True,
            expected_cache_exists=False,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_invalid_config_and_explicit_root_when_mapping_then_config_is_nonblocking(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: InvalidExplicitRootConfigTestCase,
) -> None:
    _ = write_mapping_project(tmp_path)
    write_invalid_cache_config(tmp_path)
    invocation: Path = tmp_path / test_case.invocation_subdirectory
    invocation.mkdir(exist_ok=True)
    monkeypatch.chdir(invocation)
    stdout: StringIO = StringIO()
    stderr: StringIO = StringIO()

    exit_code: int = run_map(
        argv=invalid_config_root_argv(root=tmp_path, no_cache=test_case.no_cache),
        stdout=stdout,
        stderr=stderr,
    )

    assert exit_code == 0
    assert "run(...)" in stdout.getvalue()
    assert (tmp_path / CACHE_DATABASE_RELATIVE_PATH).exists() is test_case.expected_cache_exists


@pytest.mark.parametrize(
    "test_case",
    [
        MappingIdentityFailureTestCase(
            description="identity fingerprint failure degrades to fresh mapping",
            invalid_source=False,
            expected_internal_error=True,
            expected_output_fragment="run(...)  src/pkg/entry.py:3",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_mapping_identity_failure_when_mapping_valid_project_then_computes_fresh(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: MappingIdentityFailureTestCase,
) -> None:
    source: MappingSource = write_mapping_project(tmp_path)
    fail_mapping_identity(monkeypatch)

    result: CachedCallMap = cached_map(root=tmp_path, source=source)

    assert result.stats.internal_error is test_case.expected_internal_error
    assert test_case.expected_output_fragment in render_cached(root=tmp_path, cached=result)


@pytest.mark.parametrize(
    "test_case",
    [
        MappingIdentityFailureTestCase(
            description="identity failure does not suppress current source MapError",
            invalid_source=True,
            expected_internal_error=True,
            expected_output_fragment="Could not parse",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_mapping_identity_failure_and_invalid_source_when_mapping_then_raises_map_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: MappingIdentityFailureTestCase,
) -> None:
    source: MappingSource = write_mapping_project(tmp_path)
    (tmp_path / "src/pkg/steps.py").write_text("def step(:\n", encoding="utf-8")
    fail_mapping_identity(monkeypatch)

    with pytest.raises(MapError, match=test_case.expected_output_fragment):
        _ = cached_map(root=tmp_path, source=source)
