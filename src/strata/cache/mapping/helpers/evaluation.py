"""Evaluate call maps through reusable declaration records."""

from __future__ import annotations

from pathlib import Path

from strata.cache.mapping.classes.lazy_symbol_resolver import LazySymbolResolver
from strata.cache.mapping.constants import (
    MAP_CACHE_PREFIX,
    MAP_FILE_PREFIX,
    MAP_FILE_RECORD_KIND,
    MAP_MANIFEST_PATH,
    MAP_MANIFEST_RECORD_KIND,
)
from strata.cache.mapping.helpers.fingerprints import (
    build_mapping_identity,
    file_declaration_identity,
    project_input_fingerprint,
)
from strata.cache.mapping.helpers.serialization import (
    decode_file_declarations,
    decode_manifest,
    file_declarations_record,
    manifest_record,
    seal_file_declarations,
    seal_manifest,
)
from strata.cache.mapping.helpers.validation import (
    file_declarations_are_current,
    manifest_is_current,
)
from strata.cache.mapping.models import (
    CachedCallMap,
    FileDeclarations,
    FunctionDeclaration,
    MapCacheStats,
    MapManifest,
    MappingIdentity,
)
from strata.cache.storage.models import (
    CacheMutation,
    CacheMutationOutcome,
    CacheRead,
    CacheRecord,
    CacheWrite,
)
from strata.cache.storage.types import CacheMutator, CacheStorage
from strata.mapping.constants import PATH_SYMBOL_SEPARATOR, QUALIFIED_NAME_SEPARATOR
from strata.mapping.exceptions import MapError
from strata.mapping.main.discover_sources import discover_mapping_sources
from strata.mapping.main.index_file import index_mapping_file
from strata.mapping.main.select import select_mapping_function
from strata.mapping.main.tree import build_mapping_tree
from strata.mapping.models import (
    CallMapNode,
    ClassDefinition,
    FunctionDefinition,
    MappingSource,
    ProjectIndex,
    SourceSnapshot,
)


def evaluate_cached_map(
    *,
    sources: tuple[MappingSource, ...],
    symbol: str,
    depth: int,
    repo_root: Path,
    store: CacheStorage,
) -> CachedCallMap:
    """Resolve one map while treating all cache failures as fresh-compute misses."""

    snapshots: tuple[SourceSnapshot, ...] = discover_mapping_sources(
        sources=sources, repo_root=repo_root
    )
    try:
        mapping_identity: MappingIdentity = build_mapping_identity()
        identities: tuple[str, ...] = tuple(
            file_declaration_identity(snapshot=snapshot, mapping_identity=mapping_identity)
            for snapshot in snapshots
        )
        input_fingerprint: str = project_input_fingerprint(
            snapshots=snapshots, mapping_identity=mapping_identity
        )
        record: CacheRecord | None = store.read(
            relative_path=MAP_MANIFEST_PATH,
            expected_kind=MAP_MANIFEST_RECORD_KIND,
        )
        manifest: MapManifest | None = decode_manifest(record)
        if (
            manifest is not None
            and manifest.input_fingerprint == input_fingerprint
            and manifest_is_current(manifest=manifest, snapshots=snapshots, identities=identities)
        ):
            resolver: LazySymbolResolver = LazySymbolResolver(
                manifest=manifest, snapshots=snapshots, identities=identities
            )
            root: FunctionDefinition = _select_function(
                manifest=manifest,
                resolver=resolver,
                symbol=symbol,
                snapshots=snapshots,
                identities=identities,
            )
            tree: CallMapNode = build_mapping_tree(root=root, resolver=resolver, depth=depth)
            return CachedCallMap(
                root=tree,
                stats=MapCacheStats(manifest_hit=True, parsed_files=resolver.parsed_files),
            )
        return _rebuild(
            snapshots=snapshots,
            symbol=symbol,
            depth=depth,
            input_fingerprint=input_fingerprint,
            identities=identities,
            store=store,
        )
    except MapError:
        raise
    except Exception:
        return _fresh_after_internal_failure(snapshots=snapshots, symbol=symbol, depth=depth)


def _rebuild(
    *,
    snapshots: tuple[SourceSnapshot, ...],
    symbol: str,
    depth: int,
    input_fingerprint: str,
    identities: tuple[str, ...],
    store: CacheStorage,
) -> CachedCallMap:
    reads: tuple[CacheRead, ...] = tuple(
        CacheRead(relative_path=MAP_FILE_PREFIX / identity, expected_kind=MAP_FILE_RECORD_KIND)
        for identity in identities
    )
    records: tuple[CacheRecord | None, ...] = store.read_batch(reads=reads)
    declarations: list[FileDeclarations] = []
    indexes: dict[str, ProjectIndex] = {}
    writes: list[CacheWrite] = []
    reused_records: list[tuple[Path, FileDeclarations]] = []
    reused: int = 0
    parsed: int = 0
    for snapshot, identity, record in zip(snapshots, identities, records, strict=True):
        declaration: FileDeclarations | None = decode_file_declarations(record)
        if declaration is not None and file_declarations_are_current(
            declaration=declaration, snapshot=snapshot, identity=identity
        ):
            reused += 1
            reused_records.append((MAP_FILE_PREFIX / identity, declaration))
        else:
            indexed: ProjectIndex = index_mapping_file(snapshot=snapshot)
            indexes[identity] = indexed
            declaration = seal_file_declarations(
                _declarations(snapshot=snapshot, identity=identity, index=indexed)
            )
            writes.append(
                CacheWrite(
                    relative_path=MAP_FILE_PREFIX / identity,
                    record=file_declarations_record(declaration),
                )
            )
            parsed += 1
        declarations.append(declaration)
    manifest: MapManifest = seal_manifest(
        _manifest(declarations=tuple(declarations), input_fingerprint=input_fingerprint)
    )
    writes.append(CacheWrite(relative_path=MAP_MANIFEST_PATH, record=manifest_record(manifest)))
    publication: CacheMutationOutcome = store.mutate_batch(
        reads=tuple(
            CacheRead(relative_path=path, expected_kind=MAP_FILE_RECORD_KIND)
            for path, _ in reused_records
        ),
        mutate=_publication_mutator(
            writes=tuple(writes),
            reused_records=tuple(reused_records),
            identities=identities,
        ),
    )
    resolver: LazySymbolResolver = LazySymbolResolver(
        manifest=manifest, snapshots=snapshots, identities=identities, indexes=indexes
    )
    root: FunctionDefinition = _select_function(
        manifest=manifest,
        resolver=resolver,
        symbol=symbol,
        snapshots=snapshots,
        identities=identities,
    )
    tree: CallMapNode = build_mapping_tree(root=root, resolver=resolver, depth=depth)
    return CachedCallMap(
        root=tree,
        stats=MapCacheStats(
            parsed_files=parsed + resolver.parsed_files,
            reused_file_records=reused,
            writes=_publication_write_count(publication),
            storage_failed=not publication.published,
        ),
    )


def _publication_mutator(
    *,
    writes: tuple[CacheWrite, ...],
    reused_records: tuple[tuple[Path, FileDeclarations], ...],
    identities: tuple[str, ...],
) -> CacheMutator:
    def mutate(records: tuple[CacheRecord | None, ...]) -> CacheMutation:
        repaired: list[CacheWrite] = list(writes)
        for (path, expected), record in zip(reused_records, records, strict=True):
            current: FileDeclarations | None = decode_file_declarations(record)
            if current != expected:
                repaired.append(
                    CacheWrite(
                        relative_path=path,
                        record=file_declarations_record(expected),
                    )
                )
        return CacheMutation(
            writes=tuple(repaired),
            swept_prefix=MAP_CACHE_PREFIX,
            retained_paths=(
                MAP_MANIFEST_PATH,
                *(MAP_FILE_PREFIX / identity for identity in identities),
            ),
        )

    return mutate


def _publication_write_count(publication: CacheMutationOutcome) -> int:
    if not publication.published or publication.mutation is None:
        return 0
    return len(publication.mutation.writes)


def _fresh_after_internal_failure(
    *, snapshots: tuple[SourceSnapshot, ...], symbol: str, depth: int
) -> CachedCallMap:
    functions: dict[str, FunctionDefinition] = {}
    classes: dict[str, ClassDefinition] = {}
    for snapshot in snapshots:
        indexed: ProjectIndex = index_mapping_file(snapshot=snapshot)
        functions.update(indexed.functions)
        classes.update(indexed.classes)
    index: ProjectIndex = ProjectIndex(functions=functions, classes=classes)
    root: FunctionDefinition = select_mapping_function(definitions=functions, symbol=symbol)
    return CachedCallMap(
        root=build_mapping_tree(root=root, resolver=index, depth=depth),
        stats=MapCacheStats(parsed_files=len(snapshots), storage_failed=True, internal_error=True),
    )


def _declarations(
    *, snapshot: SourceSnapshot, identity: str, index: ProjectIndex
) -> FileDeclarations:
    functions: tuple[FunctionDeclaration, ...] = tuple(
        FunctionDeclaration(
            key=item.key,
            name=item.name,
            qualified_name=item.qualified_name,
            owning_class=item.owning_class,
        )
        for item in index.functions.values()
    )
    return FileDeclarations(
        identity=identity,
        path=snapshot.relative_path,
        module_name=snapshot.module_name,
        functions=functions,
        class_keys=tuple(index.classes),
    )


def _manifest(*, declarations: tuple[FileDeclarations, ...], input_fingerprint: str) -> MapManifest:
    functions: dict[str, str] = {}
    classes: dict[str, str] = {}
    metadata: dict[str, FunctionDeclaration] = {}
    for declaration in declarations:
        for function in declaration.functions:
            functions[function.key] = declaration.identity
            metadata[function.key] = function
        for class_key in declaration.class_keys:
            classes[class_key] = declaration.identity
    bare: dict[str, list[str]] = {}
    for key in functions:
        function: FunctionDeclaration = metadata[key]
        bare.setdefault(function.name, []).append(key)
    return MapManifest(
        input_fingerprint=input_fingerprint,
        files=declarations,
        functions=functions,
        classes=classes,
        bare_functions={key: tuple(value) for key, value in bare.items()},
    )


def _select_function(
    *,
    manifest: MapManifest,
    resolver: LazySymbolResolver,
    symbol: str,
    snapshots: tuple[SourceSnapshot, ...],
    identities: tuple[str, ...],
) -> FunctionDefinition:
    matches: tuple[str, ...]
    if PATH_SYMBOL_SEPARATOR in symbol:
        path_fragment, function_name = symbol.rsplit(PATH_SYMBOL_SEPARATOR, maxsplit=1)
        selected: list[tuple[str, str]] = []
        paths: dict[str, str] = {
            identity: str(snapshot.path)
            for identity, snapshot in zip(identities, snapshots, strict=True)
        }
        for declaration in manifest.files:
            absolute_path: str = paths[declaration.identity]
            if not absolute_path.removesuffix(".py").endswith(path_fragment.removesuffix(".py")):
                continue
            selected.extend(
                (item.key, declaration.identity)
                for item in declaration.functions
                if item.qualified_name == function_name
            )
        matches = tuple(
            key for key, identity in selected if manifest.functions.get(key) == identity
        )
    elif symbol in manifest.functions:
        matches = (symbol,)
    elif QUALIFIED_NAME_SEPARATOR not in symbol:
        matches = manifest.bare_functions.get(symbol, ())
    else:
        matches = ()
    if len(matches) == 1:
        result: FunctionDefinition | None = resolver.get_function(matches[0])
        if result is not None:
            return result
    if not matches:
        raise MapError(f"Unknown project function: {symbol}")
    choices: str = ", ".join(sorted(matches))
    raise MapError(f"Ambiguous function {symbol}; choose one of: {choices}")
