"""Snapshot-backed lazy symbol resolver."""

from __future__ import annotations

from strata.cache.mapping.models import MapManifest
from strata.mapping.main.index_file import index_mapping_file
from strata.mapping.models import ClassDefinition, FunctionDefinition, ProjectIndex, SourceSnapshot


class LazySymbolResolver:
    """Hydrate only files reached through canonical symbol point lookups."""

    def __init__(
        self,
        *,
        manifest: MapManifest,
        snapshots: tuple[SourceSnapshot, ...],
        identities: tuple[str, ...],
        indexes: dict[str, ProjectIndex] | None = None,
    ) -> None:
        self._manifest: MapManifest = manifest
        self._snapshots: dict[str, SourceSnapshot] = dict(zip(identities, snapshots, strict=True))
        self._indexes: dict[str, ProjectIndex] = {} if indexes is None else dict(indexes)
        self.parsed_files: int = 0

    def get_function(self, key: str) -> FunctionDefinition | None:
        """Return one function, parsing its owning snapshot at most once."""

        identity: str | None = self._manifest.functions.get(key)
        if identity is None:
            return None
        return self._index(identity).functions.get(key)

    def get_class(self, key: str) -> ClassDefinition | None:
        """Return one class, parsing its owning snapshot at most once."""

        identity: str | None = self._manifest.classes.get(key)
        if identity is None:
            return None
        return self._index(identity).classes.get(key)

    def get_protocol_implementations(self, key: str) -> tuple[ClassDefinition, ...]:
        """Hydrate only concrete classes nominally implementing one protocol."""

        implementations: list[ClassDefinition] = []
        for class_key in self._manifest.protocol_implementations.get(key, ()):
            definition: ClassDefinition | None = self.get_class(class_key)
            if definition is not None:
                implementations.append(definition)
        return tuple(implementations)

    def _index(self, identity: str) -> ProjectIndex:
        indexed: ProjectIndex | None = self._indexes.get(identity)
        if indexed is not None:
            return indexed
        indexed = index_mapping_file(snapshot=self._snapshots[identity])
        self._indexes[identity] = indexed
        self.parsed_files += 1
        return indexed
