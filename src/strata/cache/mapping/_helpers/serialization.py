"""Strict canonical call-map cache serialization."""

from __future__ import annotations

from typing import cast

from strata.cache.fingerprints.main.canonical import fingerprint_canonical
from strata.cache.fingerprints.types import CanonicalValue
from strata.cache.mapping.constants import (
    MAP_CLASS_KEYS,
    MAP_FILE_KEYS,
    MAP_FILE_RECORD_KIND,
    MAP_FUNCTION_KEYS,
    MAP_MANIFEST_KEYS,
    MAP_MANIFEST_RECORD_KIND,
)
from strata.cache.mapping.models import (
    ClassDeclaration,
    FileDeclarations,
    FunctionDeclaration,
    MapManifest,
)
from strata.cache.storage.models import CacheRecord


def file_declarations_record(value: FileDeclarations) -> CacheRecord:
    """Encode one declaration record as canonical metadata."""

    return CacheRecord(
        kind=MAP_FILE_RECORD_KIND, payload=_file_value(seal_file_declarations(value))
    )


def manifest_record(value: MapManifest) -> CacheRecord:
    """Encode one project manifest as canonical metadata."""

    sealed: MapManifest = seal_manifest(value)
    return CacheRecord(kind=MAP_MANIFEST_RECORD_KIND, payload=_manifest_value(sealed))


def seal_file_declarations(value: FileDeclarations) -> FileDeclarations:
    """Bind one file declaration's complete semantic payload to its fingerprint."""

    fingerprint: str = fingerprint_canonical(_file_semantic_value(value)).value
    return FileDeclarations(
        identity=value.identity,
        path=value.path,
        module_name=value.module_name,
        functions=value.functions,
        classes=value.classes,
        record_fingerprint=fingerprint,
    )


def seal_manifest(value: MapManifest) -> MapManifest:
    """Bind one manifest's complete semantic payload to its fingerprint."""

    files: tuple[FileDeclarations, ...] = tuple(
        seal_file_declarations(item) for item in value.files
    )
    unsealed: MapManifest = MapManifest(
        input_fingerprint=value.input_fingerprint,
        files=files,
        functions=value.functions,
        classes=value.classes,
        bare_functions=value.bare_functions,
        protocol_implementations=value.protocol_implementations,
    )
    fingerprint: str = fingerprint_canonical(_manifest_semantic_value(unsealed)).value
    return MapManifest(
        input_fingerprint=unsealed.input_fingerprint,
        files=unsealed.files,
        functions=unsealed.functions,
        classes=unsealed.classes,
        bare_functions=unsealed.bare_functions,
        protocol_implementations=unsealed.protocol_implementations,
        record_fingerprint=fingerprint,
    )


def _manifest_semantic_value(value: MapManifest) -> CanonicalValue:
    return {
        "bare_functions": {key: list(items) for key, items in sorted(value.bare_functions.items())},
        "classes": dict(sorted(value.classes.items())),
        "files": [_file_value(item) for item in value.files],
        "functions": dict(sorted(value.functions.items())),
        "input_fingerprint": value.input_fingerprint,
        "protocol_implementations": {
            key: list(items) for key, items in sorted(value.protocol_implementations.items())
        },
    }


def _manifest_value(value: MapManifest) -> CanonicalValue:
    semantic: CanonicalValue = _manifest_semantic_value(value)
    if not isinstance(semantic, dict):
        return semantic
    return {**semantic, "record_fingerprint": value.record_fingerprint}


def decode_file_declarations(record: CacheRecord | None) -> FileDeclarations | None:
    """Decode one strict declaration record or return a cache miss."""

    if record is None or record.kind != MAP_FILE_RECORD_KIND:
        return None
    decoded: FileDeclarations | None = _decode_file(record.payload)
    if (
        decoded is None
        or seal_file_declarations(decoded).record_fingerprint != decoded.record_fingerprint
    ):
        return None
    return decoded


def decode_manifest(record: CacheRecord | None) -> MapManifest | None:
    """Decode one strict project manifest or return a cache miss."""

    if (
        record is None
        or record.kind != MAP_MANIFEST_RECORD_KIND
        or not isinstance(record.payload, dict)
    ):
        return None
    payload: dict[str, CanonicalValue] = record.payload
    if set(payload) != MAP_MANIFEST_KEYS:
        return None
    input_fingerprint: object = payload["input_fingerprint"]
    record_fingerprint: object = payload["record_fingerprint"]
    raw_files: object = payload["files"]
    functions: dict[str, str] | None = _string_dict(payload["functions"])
    classes: dict[str, str] | None = _string_dict(payload["classes"])
    bare: dict[str, tuple[str, ...]] | None = _string_tuple_dict(payload["bare_functions"])
    protocol_implementations: dict[str, tuple[str, ...]] | None = _string_tuple_dict(
        payload["protocol_implementations"]
    )
    if (
        not isinstance(input_fingerprint, str)
        or not isinstance(record_fingerprint, str)
        or not isinstance(raw_files, list)
    ):
        return None
    files: list[FileDeclarations] = []
    for raw_file in raw_files:
        decoded: FileDeclarations | None = _decode_file(raw_file)
        if decoded is None:
            return None
        files.append(decoded)
    if functions is None or classes is None or bare is None or protocol_implementations is None:
        return None
    manifest: MapManifest = MapManifest(
        input_fingerprint,
        tuple(files),
        functions,
        classes,
        bare,
        protocol_implementations,
        record_fingerprint,
    )
    if any(
        seal_file_declarations(item).record_fingerprint != item.record_fingerprint for item in files
    ):
        return None
    return manifest if seal_manifest(manifest).record_fingerprint == record_fingerprint else None


def _file_value(value: FileDeclarations) -> CanonicalValue:
    return {
        **cast(dict[str, CanonicalValue], _file_semantic_value(value)),
        "record_fingerprint": value.record_fingerprint,
    }


def _file_semantic_value(value: FileDeclarations) -> CanonicalValue:
    return {
        "classes": [
            {
                "base_keys": list(item.base_keys),
                "key": item.key,
                "protocol": item.protocol,
            }
            for item in value.classes
        ],
        "functions": [
            {
                "key": item.key,
                "name": item.name,
                "owning_class": item.owning_class,
                "qualified_name": item.qualified_name,
            }
            for item in value.functions
        ],
        "identity": value.identity,
        "module_name": value.module_name,
        "path": value.path,
    }


def _decode_file(value: object) -> FileDeclarations | None:
    if not isinstance(value, dict) or set(value) != MAP_FILE_KEYS:
        return None
    fields: dict[str, object] = cast(dict[str, object], value)
    identity: object = fields["identity"]
    path: object = fields["path"]
    module_name: object = fields["module_name"]
    raw_classes: object = fields["classes"]
    raw_functions: object = fields["functions"]
    record_fingerprint: object = fields["record_fingerprint"]
    if not all(isinstance(item, str) for item in (identity, path, module_name, record_fingerprint)):
        return None
    if not isinstance(raw_classes, list) or not isinstance(raw_functions, list):
        return None
    classes: list[ClassDeclaration] = []
    for raw in raw_classes:
        if not isinstance(raw, dict) or set(raw) != MAP_CLASS_KEYS:
            return None
        class_fields: dict[str, object] = cast(dict[str, object], raw)
        key: object = class_fields["key"]
        base_keys: object = class_fields["base_keys"]
        protocol: object = class_fields["protocol"]
        if (
            not isinstance(key, str)
            or not isinstance(base_keys, list)
            or not all(isinstance(item, str) for item in base_keys)
            or not isinstance(protocol, bool)
        ):
            return None
        classes.append(ClassDeclaration(key, tuple(cast(list[str], base_keys)), protocol))
    functions: list[FunctionDeclaration] = []
    for raw in raw_functions:
        if not isinstance(raw, dict) or set(raw) != MAP_FUNCTION_KEYS:
            return None
        function_fields: dict[str, object] = cast(dict[str, object], raw)
        key: object = function_fields["key"]
        name: object = function_fields["name"]
        owning_class: object = function_fields["owning_class"]
        qualified_name: object = function_fields["qualified_name"]
        if (
            not isinstance(key, str)
            or not isinstance(name, str)
            or not isinstance(qualified_name, str)
        ):
            return None
        if owning_class is not None and not isinstance(owning_class, str):
            return None
        functions.append(FunctionDeclaration(key, name, qualified_name, owning_class))
    return FileDeclarations(
        cast(str, identity),
        cast(str, path),
        cast(str, module_name),
        tuple(functions),
        tuple(classes),
        cast(str, record_fingerprint),
    )


def _string_dict(value: object) -> dict[str, str] | None:
    if not isinstance(value, dict) or not all(
        isinstance(key, str) and isinstance(item, str) for key, item in value.items()
    ):
        return None
    return cast(dict[str, str], value)


def _string_tuple_dict(value: object) -> dict[str, tuple[str, ...]] | None:
    if not isinstance(value, dict):
        return None
    result: dict[str, tuple[str, ...]] = {}
    for key, item in value.items():
        if (
            not isinstance(key, str)
            or not isinstance(item, list)
            or not all(isinstance(entry, str) for entry in item)
        ):
            return None
        result[key] = tuple(cast(list[str], item))
    return result
