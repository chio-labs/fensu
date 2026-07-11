"""Convert typed evaluation cache records to canonical storage records."""

from __future__ import annotations

from collections.abc import Callable
from typing import cast

from strata.analysis.core.types import ProjectDependencyKind
from strata.cache.fingerprints.models import CacheFingerprint
from strata.cache.fingerprints.types import CanonicalValue
from strata.cache.results.constants import (
    CACHE_FACT_KIND,
    CACHE_FILE_RESULT_KIND,
    CACHE_INDEX_KIND,
    CACHE_METADATA_KIND,
    DEPENDENCY_OBSERVATION_KEYS,
    FACT_PAYLOAD_KEYS,
    FAULT_KEYS,
    FILE_RESULT_PAYLOAD_KEYS,
    INDEX_ENTRY_KEYS,
    INDEX_PAYLOAD_KEYS,
    METADATA_PAYLOAD_KEYS,
    RULE_EXCEPTION_KEY_KEYS,
)
from strata.cache.results.helpers.validation import (
    fingerprint_or_none,
    is_dependency_observation,
    is_fingerprint,
    is_relative_path,
    is_rule_code,
    is_rule_exception_symbol,
)
from strata.cache.results.models import (
    CachedFact,
    CachedFault,
    CachedFileResult,
    CachedRuleExceptionKey,
    CacheIndex,
    CacheIndexEntry,
    CacheMetadata,
    DependencyObservation,
)
from strata.cache.results.types import DependencyAnswer
from strata.cache.storage.exceptions import CacheRecordError
from strata.cache.storage.models import CacheRecord


def metadata_to_record(metadata: CacheMetadata) -> CacheRecord:
    """Return a validated storage record for cache metadata."""

    if not is_fingerprint(metadata.global_fingerprint.value):
        raise CacheRecordError("Cache metadata contains an invalid global fingerprint.")
    return CacheRecord(
        kind=CACHE_METADATA_KIND,
        payload={"global_fingerprint": metadata.global_fingerprint.value},
    )


def metadata_from_record(record: CacheRecord) -> CacheMetadata | None:
    """Return typed cache metadata or None for a semantic miss."""

    payload: dict[str, CanonicalValue] | None = _payload(record, kind=CACHE_METADATA_KIND)
    if payload is None or set(payload) != METADATA_PAYLOAD_KEYS:
        return None
    fingerprint: CacheFingerprint | None = fingerprint_or_none(payload["global_fingerprint"])
    return CacheMetadata(global_fingerprint=fingerprint) if fingerprint is not None else None


def index_to_record(index: CacheIndex) -> CacheRecord:
    """Return a validated storage record for a deterministic source index."""

    entries: list[CanonicalValue] = [_index_entry_value(entry) for entry in index.entries]
    if not is_fingerprint(index.global_fingerprint.value) or not _index_entries_are_ordered(
        index.entries
    ):
        raise CacheRecordError("Cache index contains invalid identity or entry ordering.")
    return CacheRecord(
        kind=CACHE_INDEX_KIND,
        payload={"entries": entries, "global_fingerprint": index.global_fingerprint.value},
    )


def index_from_record(record: CacheRecord) -> CacheIndex | None:
    """Return a typed source index or None for a semantic miss."""

    payload: dict[str, CanonicalValue] | None = _payload(record, kind=CACHE_INDEX_KIND)
    if payload is None or set(payload) != INDEX_PAYLOAD_KEYS:
        return None
    global_fingerprint: CacheFingerprint | None = fingerprint_or_none(payload["global_fingerprint"])
    raw_entries: CanonicalValue = payload["entries"]
    if global_fingerprint is None or not isinstance(raw_entries, list):
        return None
    entries: list[CacheIndexEntry] = []
    for raw_entry in raw_entries:
        entry: CacheIndexEntry | None = _index_entry(raw_entry)
        if entry is None:
            return None
        entries.append(entry)
    result: CacheIndex = CacheIndex(global_fingerprint=global_fingerprint, entries=tuple(entries))
    return result if _index_entries_are_ordered(result.entries) else None


def file_result_to_record(result: CachedFileResult) -> CacheRecord:
    """Return a validated storage record for one file evaluation."""

    payload: CanonicalValue = _file_result_value(result)
    record: CacheRecord = CacheRecord(kind=CACHE_FILE_RESULT_KIND, payload=payload)
    if file_result_from_record(record) != result:
        raise CacheRecordError("File result contains invalid or noncanonical values.")
    return record


def file_result_from_record(record: CacheRecord) -> CachedFileResult | None:
    """Return a typed file result or None for a semantic miss."""

    payload: dict[str, CanonicalValue] | None = _payload(record, kind=CACHE_FILE_RESULT_KIND)
    if payload is None or set(payload) != FILE_RESULT_PAYLOAD_KEYS:
        return None
    path: CanonicalValue = payload["path"]
    fingerprint: CacheFingerprint | None = fingerprint_or_none(payload["source_fingerprint"])
    raw_faults: CanonicalValue = payload["faults"]
    raw_exceptions: CanonicalValue = payload["applied_exception_keys"]
    raw_dependencies: CanonicalValue = payload["dependencies"]
    if not (
        is_relative_path(path)
        and fingerprint is not None
        and isinstance(raw_faults, list)
        and isinstance(raw_exceptions, list)
        and isinstance(raw_dependencies, list)
    ):
        return None
    faults: tuple[CachedFault, ...] | None = _decode_sequence(raw_faults, decoder=_fault)
    exceptions: tuple[CachedRuleExceptionKey, ...] | None = _decode_sequence(
        raw_exceptions, decoder=_exception_key
    )
    dependencies: tuple[DependencyObservation, ...] | None = _decode_sequence(
        raw_dependencies, decoder=_dependency
    )
    if faults is None or exceptions is None or dependencies is None:
        return None
    result: CachedFileResult = CachedFileResult(
        path=cast(str, path),
        source_fingerprint=fingerprint,
        faults=faults,
        applied_exception_keys=exceptions,
        dependencies=dependencies,
    )
    return result if _file_result_relationships_are_valid(result) else None


def fact_to_record(fact: CachedFact) -> CacheRecord:
    """Return a validated independently tagged fact storage record."""

    if not (
        is_relative_path(fact.path)
        and is_fingerprint(fact.source_fingerprint.value)
        and fact.fact_kind
    ):
        raise CacheRecordError("Cached fact contains invalid identity values.")
    return CacheRecord(
        kind=CACHE_FACT_KIND,
        payload={
            "fact_kind": fact.fact_kind,
            "path": fact.path,
            "payload": fact.payload,
            "source_fingerprint": fact.source_fingerprint.value,
        },
    )


def fact_from_record(record: CacheRecord) -> CachedFact | None:
    """Return a typed fact envelope or None for a semantic miss."""

    payload: dict[str, CanonicalValue] | None = _payload(record, kind=CACHE_FACT_KIND)
    if payload is None or set(payload) != FACT_PAYLOAD_KEYS:
        return None
    path: CanonicalValue = payload["path"]
    fact_kind: CanonicalValue = payload["fact_kind"]
    fingerprint: CacheFingerprint | None = fingerprint_or_none(payload["source_fingerprint"])
    if not is_relative_path(path) or not isinstance(fact_kind, str) or not fact_kind:
        return None
    if fingerprint is None:
        return None
    return CachedFact(
        path=cast(str, path),
        source_fingerprint=fingerprint,
        fact_kind=fact_kind,
        payload=payload["payload"],
    )


def _payload(record: CacheRecord, *, kind: str) -> dict[str, CanonicalValue] | None:
    if record.kind != kind or not isinstance(record.payload, dict):
        return None
    return record.payload


def _index_entry_value(entry: CacheIndexEntry) -> CanonicalValue:
    if not (
        is_relative_path(entry.path)
        and is_fingerprint(entry.source_fingerprint.value)
        and is_fingerprint(entry.result_fingerprint.value)
    ):
        raise CacheRecordError("Cache index entry contains invalid identity values.")
    return {
        "path": entry.path,
        "result_fingerprint": entry.result_fingerprint.value,
        "source_fingerprint": entry.source_fingerprint.value,
    }


def _index_entry(value: CanonicalValue) -> CacheIndexEntry | None:
    if not isinstance(value, dict) or set(value) != INDEX_ENTRY_KEYS:
        return None
    path: CanonicalValue = value["path"]
    source_fingerprint: CacheFingerprint | None = fingerprint_or_none(value["source_fingerprint"])
    result_fingerprint: CacheFingerprint | None = fingerprint_or_none(value["result_fingerprint"])
    if not is_relative_path(path) or source_fingerprint is None or result_fingerprint is None:
        return None
    return CacheIndexEntry(
        path=cast(str, path),
        source_fingerprint=source_fingerprint,
        result_fingerprint=result_fingerprint,
    )


def _index_entries_are_ordered(entries: tuple[CacheIndexEntry, ...]) -> bool:
    paths: tuple[str, ...] = tuple(entry.path for entry in entries)
    return paths == tuple(sorted(set(paths)))


def _file_result_relationships_are_valid(result: CachedFileResult) -> bool:
    exception_identities: tuple[tuple[str, str, str], ...] = tuple(
        (key.rule, key.path, key.symbol) for key in result.applied_exception_keys
    )
    if exception_identities != tuple(sorted(set(exception_identities))):
        return False
    return (
        all(fault.path == result.path for fault in result.faults)
        and all(key.path == result.path for key in result.applied_exception_keys)
        and all(dependency.requester_path == result.path for dependency in result.dependencies)
        and len(set(result.dependencies)) == len(result.dependencies)
    )


def _file_result_value(result: CachedFileResult) -> CanonicalValue:
    return {
        "applied_exception_keys": [
            _exception_key_value(item) for item in result.applied_exception_keys
        ],
        "dependencies": [_dependency_value(item) for item in result.dependencies],
        "faults": [_fault_value(item) for item in result.faults],
        "path": result.path,
        "source_fingerprint": result.source_fingerprint.value,
    }


def _fault_value(fault: CachedFault) -> CanonicalValue:
    return {
        "code": fault.code,
        "column": fault.column,
        "line": fault.line,
        "message": fault.message,
        "path": fault.path,
        "remediation": fault.remediation,
    }


def _fault(value: CanonicalValue) -> CachedFault | None:
    if not isinstance(value, dict) or set(value) != FAULT_KEYS:
        return None
    code: CanonicalValue = value["code"]
    path: CanonicalValue = value["path"]
    message: CanonicalValue = value["message"]
    line: CanonicalValue = value["line"]
    column: CanonicalValue = value["column"]
    remediation: CanonicalValue = value["remediation"]
    if not (
        is_rule_code(code)
        and is_relative_path(path)
        and isinstance(message, str)
        and _optional_position(line, minimum=1)
        and _optional_position(column, minimum=0)
        and (line is not None or column is None)
        and (remediation is None or isinstance(remediation, str))
    ):
        return None
    return CachedFault(
        code=cast(str, code),
        path=cast(str, path),
        message=message,
        line=cast(int | None, line),
        column=cast(int | None, column),
        remediation=remediation,
    )


def _exception_key_value(key: CachedRuleExceptionKey) -> CanonicalValue:
    return {"path": key.path, "rule": key.rule, "symbol": key.symbol}


def _exception_key(value: CanonicalValue) -> CachedRuleExceptionKey | None:
    if not isinstance(value, dict) or set(value) != RULE_EXCEPTION_KEY_KEYS:
        return None
    path: CanonicalValue = value["path"]
    rule: CanonicalValue = value["rule"]
    symbol: CanonicalValue = value["symbol"]
    if not (is_relative_path(path) and is_rule_code(rule) and is_rule_exception_symbol(symbol)):
        return None
    return CachedRuleExceptionKey(
        rule=cast(str, rule),
        path=cast(str, path),
        symbol=cast(str, symbol),
    )


def _dependency_value(observation: DependencyObservation) -> CanonicalValue:
    answer: CanonicalValue
    if isinstance(observation.answer, tuple):
        answer = list(observation.answer)
    else:
        answer = observation.answer
    return {
        "answer": answer,
        "dependency_path": observation.dependency_path,
        "kind": observation.kind.value,
        "pattern": observation.pattern,
        "query_path": observation.query_path,
        "recursive": observation.recursive,
        "requester_path": observation.requester_path,
    }


def _dependency(value: CanonicalValue) -> DependencyObservation | None:
    if not isinstance(value, dict) or set(value) != DEPENDENCY_OBSERVATION_KEYS:
        return None
    try:
        kind: ProjectDependencyKind = ProjectDependencyKind(value["kind"])
    except (TypeError, ValueError):
        return None
    raw_answer: CanonicalValue = value["answer"]
    if isinstance(raw_answer, list):
        if not all(isinstance(item, str) for item in raw_answer):
            return None
        answer: DependencyAnswer = tuple(cast(list[str], raw_answer))
    elif raw_answer is None or type(raw_answer) is bool or isinstance(raw_answer, str):
        answer = raw_answer
    else:
        return None
    pattern: CanonicalValue = value["pattern"]
    recursive: CanonicalValue = value["recursive"]
    requester_path: CanonicalValue = value["requester_path"]
    query_path: CanonicalValue = value["query_path"]
    dependency_path: CanonicalValue = value["dependency_path"]
    if not (
        (pattern is None or isinstance(pattern, str))
        and type(recursive) is bool
        and isinstance(requester_path, str)
        and isinstance(query_path, str)
        and isinstance(dependency_path, str)
    ):
        return None
    observation: DependencyObservation = DependencyObservation(
        requester_path=requester_path,
        query_path=query_path,
        dependency_path=dependency_path,
        kind=kind,
        answer=answer,
        pattern=pattern,
        recursive=recursive,
    )
    return observation if is_dependency_observation(observation) else None


def _decode_sequence[Decoded](
    values: list[CanonicalValue],
    *,
    decoder: Callable[[CanonicalValue], Decoded | None],
) -> tuple[Decoded, ...] | None:
    decoded: list[Decoded] = []
    for value in values:
        item: Decoded | None = decoder(value)
        if item is None:
            return None
        decoded.append(item)
    return tuple(decoded)


def _optional_position(value: CanonicalValue, *, minimum: int) -> bool:
    return value is None or (type(value) is int and value >= minimum)
