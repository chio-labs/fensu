"""Mapping cache integration test helpers."""

import sqlite3
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

import pytest

from strata.cache.mapping._helpers.serialization import (
    decode_file_declarations,
    decode_manifest,
    file_declarations_record,
    manifest_record,
)
from strata.cache.mapping.constants import (
    MAP_FILE_RECORD_KIND,
    MAP_MANIFEST_PATH,
    MAP_MANIFEST_RECORD_KIND,
)
from strata.cache.mapping.main.build import build_cached_call_map
from strata.cache.mapping.models import CachedCallMap, FileDeclarations, MapManifest
from strata.cache.storage.classes.cache_store import CacheStore
from strata.cache.storage.models import CacheMutationOutcome, CacheRead, CacheRecord
from strata.cache.storage.types import CacheMutator
from strata.mapping.main.render import render_call_tree
from strata.mapping.models import MappingSource
from strata.mapping.types import PathMode

_OMIT_FUNCTION_MUTATION: str = "omit-function"
_REDIRECT_FUNCTION_MUTATION: str = "redirect-function"
_REDIRECT_CLASS_MUTATION: str = "redirect-class"
_REDIRECT_PROTOCOL_MUTATION: str = "redirect-protocol"


def _omit_function(manifest: MapManifest) -> MapManifest:
    return replace(manifest, functions={})


def _redirect_function(manifest: MapManifest) -> MapManifest:
    redirected: dict[str, str] = dict(manifest.functions)
    redirected["pkg.entry.run"] = manifest.files[-1].identity
    return replace(manifest, functions=redirected)


def _redirect_class(manifest: MapManifest) -> MapManifest:
    redirected: dict[str, str] = dict(manifest.classes)
    redirected["pkg.unused.Owner"] = manifest.files[0].identity
    return replace(manifest, classes=redirected)


def _redirect_bare_function(manifest: MapManifest) -> MapManifest:
    return replace(manifest, bare_functions={"run": ("pkg.steps.step",)})


def _redirect_protocol_implementation(manifest: MapManifest) -> MapManifest:
    return replace(
        manifest,
        protocol_implementations={"pkg.Contract": ("pkg.unused.Owner",)},
    )


def write_mapping_project(root: Path) -> MappingSource:
    """Write a three-file project with one unreachable declaration file."""

    source_root: Path = root / "src"
    package: Path = source_root / "pkg"
    package.mkdir(parents=True)
    (package / "entry.py").write_text(
        "from pkg.steps import step\n\ndef run():\n    step()\n", encoding="utf-8"
    )
    (package / "steps.py").write_text("def step():\n    return 1\n", encoding="utf-8")
    (package / "unused.py").write_text(
        "class Owner:\n    pass\n\ndef unused():\n    return 2\n", encoding="utf-8"
    )
    (root / "pyproject.toml").write_text(
        "[project]\nname='fixture'\nversion='0'\n", encoding="utf-8"
    )
    return MappingSource(scan_path=source_root, import_root=source_root)


def cached_map(*, root: Path, source: MappingSource) -> CachedCallMap:
    """Build the fixture's root call map through the persistent cache."""

    return build_cached_call_map(sources=(source,), symbol="run", depth=2, repo_root=root)


def cached_symbol_map(*, root: Path, source: MappingSource, symbol: str) -> CachedCallMap:
    """Build one selected fixture symbol through the persistent cache."""

    return build_cached_call_map(sources=(source,), symbol=symbol, depth=2, repo_root=root)


def direct_ast_parse_paths(*, root: Path) -> tuple[str, ...]:
    """Return Python modules containing direct ast.parse calls."""

    candidates: filter[Path] = filter(
        lambda candidate: "ast.parse" in candidate.read_text(encoding="utf-8"),
        root.rglob("*.py"),
    )
    return tuple(candidate.relative_to(root).as_posix() for candidate in candidates)


def mutate_manifest(*, root: Path, mutation: str) -> None:
    """Publish an integrity-valid but cross-inconsistent project manifest."""

    store: CacheStore = CacheStore(repo_root=root)
    manifest: MapManifest | None = decode_manifest(
        store.read(
            relative_path=MAP_MANIFEST_PATH,
            expected_kind=MAP_MANIFEST_RECORD_KIND,
        )
    )
    assert manifest is not None, "fixture manifest was not published"
    mutations: dict[str, Callable[[MapManifest], MapManifest]] = {
        _OMIT_FUNCTION_MUTATION: _omit_function,
        _REDIRECT_FUNCTION_MUTATION: _redirect_function,
        _REDIRECT_CLASS_MUTATION: _redirect_class,
        _REDIRECT_PROTOCOL_MUTATION: _redirect_protocol_implementation,
    }
    mutate: Callable[[MapManifest], MapManifest] = mutations.get(mutation, _redirect_bare_function)
    changed: MapManifest = mutate(manifest)
    _ = store.write(relative_path=MAP_MANIFEST_PATH, record=manifest_record(changed))


def mutate_file_record(*, root: Path) -> None:
    """Publish integrity-valid but semantically redirected file declarations."""

    store: CacheStore = CacheStore(repo_root=root)
    manifest: MapManifest | None = decode_manifest(
        store.read(
            relative_path=MAP_MANIFEST_PATH,
            expected_kind=MAP_MANIFEST_RECORD_KIND,
        )
    )
    assert manifest is not None, "fixture manifest was not published"
    target: FileDeclarations = manifest.files[-1]
    record_path: Path = Path("mapping/files") / target.identity
    declarations: FileDeclarations | None = decode_file_declarations(
        store.read(relative_path=record_path, expected_kind=MAP_FILE_RECORD_KIND)
    )
    assert declarations is not None, "fixture file declarations were not published"
    redirected: FileDeclarations = replace(declarations, path="src/pkg/redirected.py")
    _ = store.write(
        relative_path=record_path,
        record=file_declarations_record(redirected),
    )


def render_cached(*, root: Path, cached: CachedCallMap) -> str:
    """Render one cached fixture result."""

    return render_call_tree(
        root=cached.root,
        repo_root=root,
        path_mode=PathMode.RELATIVE,
        use_color=False,
    )


def path_selector_spelling(*, path: Path, absolute: bool) -> str:
    """Return one absolute or repository-relative fixture selector path."""

    return {False: "src/pkg/entry.py", True: str(path)}[absolute]


def install_generation_sweep_interleaving(monkeypatch: pytest.MonkeyPatch) -> None:
    """Delete one reused record after preparation but before mutation reads."""

    original: Callable[..., CacheMutationOutcome] = CacheStore.mutate_batch

    def mutate_batch(
        store: CacheStore,
        *,
        reads: tuple[CacheRead, ...],
        mutate: CacheMutator,
    ) -> CacheMutationOutcome:
        for read in reads[:1]:
            with sqlite3.connect(store.root) as connection:
                connection.execute(
                    "DELETE FROM records WHERE key = ?",
                    (read.relative_path.as_posix(),),
                )
        return original(store, reads=reads, mutate=mutate)

    monkeypatch.setattr(CacheStore, "mutate_batch", mutate_batch)


def write_disabled_cache_config(root: Path) -> None:
    """Write a config whose layout must not replace explicit map roots."""

    (root / "strata.toml").write_text(
        'roots = ["configured-root-not-used"]\n[cache]\nenabled = false\n',
        encoding="utf-8",
    )


def write_invalid_cache_config(root: Path) -> None:
    """Write malformed configuration beside an otherwise mappable project."""

    (root / "strata.toml").write_text("roots = [\n", encoding="utf-8")


def fail_mapping_identity(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace mapping identity construction with a deterministic I/O failure."""

    def fail() -> None:
        raise OSError("mapping identity unavailable")

    monkeypatch.setattr(
        "strata.cache.mapping._helpers.evaluation.build_mapping_identity",
        fail,
    )


def current_file_record_count(root: Path) -> int:
    """Return the number of manifest file records currently readable."""

    store: CacheStore = CacheStore(repo_root=root)
    manifest: MapManifest | None = decode_manifest(
        store.read(
            relative_path=MAP_MANIFEST_PATH,
            expected_kind=MAP_MANIFEST_RECORD_KIND,
        )
    )
    manifest_files: tuple[FileDeclarations, ...] = getattr(manifest, "files", ())
    records: tuple[CacheRecord | None, ...] = store.read_batch(
        reads=tuple(
            CacheRead(
                relative_path=Path("mapping/files") / item.identity,
                expected_kind=MAP_FILE_RECORD_KIND,
            )
            for item in manifest_files
        )
    )
    return sum(record is not None for record in records)


def explicit_root_argv(*, root: Path, cache_override: bool) -> tuple[str, ...]:
    """Return explicit-root CLI arguments with an optional cache override."""

    base: tuple[str, ...] = ("run", "--root", str(root / "src"))
    return {False: base, True: (*base, "--cache")}[cache_override]


def invalid_config_root_argv(*, root: Path, no_cache: bool) -> tuple[str, ...]:
    """Return explicit-root arguments with an optional no-cache override."""

    base: tuple[str, ...] = ("run", "--root", str(root / "src"))
    return {False: base, True: (*base, "--no-cache")}[no_cache]
