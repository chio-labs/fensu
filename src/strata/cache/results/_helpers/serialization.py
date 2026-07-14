"""Convert typed evaluation cache records to canonical storage records."""

from __future__ import annotations

from collections.abc import Callable
from typing import cast

from strata.analysis.types import ProjectDependencyKind
from strata.cache.fingerprints.models import CacheFingerprint
from strata.cache.fingerprints.types import CanonicalValue
from strata.cache.results._helpers.validation import (
    fingerprint_or_none,
    is_dependency_observation,
    is_fingerprint,
    is_relative_path,
    is_rule_exception_symbol,
)
from strata.cache.results.constants import (
    CACHE_CHECK_OUTPUT_KIND,
    CACHE_FACT_KIND,
    CACHE_FILE_RESULT_KIND,
    CACHE_INDEX_KIND,
    CACHE_METADATA_KIND,
    CHECK_OUTPUT_PAYLOAD_KEYS,
    DEPENDENCY_OBSERVATION_KEYS,
    FACT_PAYLOAD_KEYS,
    FAULT_KEYS,
    FILE_RESULT_PAYLOAD_KEYS,
    INDEX_ENTRY_KEYS,
    INDEX_PAYLOAD_KEYS,
    METADATA_PAYLOAD_KEYS,
    RULE_EXCEPTION_KEY_KEYS,
    THRESHOLD_OVERRIDE_USE_KEYS,
)
from strata.cache.results.models import (
    CachedCheckOutput,
    CachedFact,
    CachedFault,
    CachedFileResult,
    CachedRuleExceptionKey,
    CachedThresholdOverrideUse,
    CacheIndex,
    CacheIndexEntry,
    CacheMetadata,
    DependencyObservation,
)
from strata.cache.results.types import DependencyAnswer
from strata.cache.storage.exceptions import CacheRecordError
from strata.cache.storage.models import CacheRecord
from strata.rules.authoring.main.is_rule_code import is_rule_code
from strata.rules.authoring.types import Threshold


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

    payload: dict[str, CanonicalValue] | None = _payload(record=record, kind=CACHE_METADATA_KIND)
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

    payload: dict[str, CanonicalValue] | None = _payload(record=record, kind=CACHE_INDEX_KIND)
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


def check_output_to_record(output: CachedCheckOutput) -> CacheRecord:
    """Return a validated storage record for one rendered check surface."""

    record: CacheRecord = CacheRecord(
        kind=CACHE_CHECK_OUTPUT_KIND,
        payload={
            "color_output": output.color_output,
            "exit_code": output.exit_code,
            "global_fingerprint": output.global_fingerprint.value,
            "index_fingerprint": output.index_fingerprint.value,
            "plain_output": output.plain_output,
            "targets": list(output.targets),
        },
    )
    if check_output_from_record(record) != output:
        raise CacheRecordError("Check output contains invalid or noncanonical values.")
    return record


def check_output_from_record(record: CacheRecord) -> CachedCheckOutput | None:
    """Return a typed rendered check surface or None for a semantic miss."""

    payload: dict[str, CanonicalValue] | None = _payload(
        record=record, kind=CACHE_CHECK_OUTPUT_KIND
    )
    if payload is None or set(payload) != CHECK_OUTPUT_PAYLOAD_KEYS:
        return None
    global_fingerprint: CacheFingerprint | None = fingerprint_or_none(payload["global_fingerprint"])
    index_fingerprint: CacheFingerprint | None = fingerprint_or_none(payload["index_fingerprint"])
    raw_targets: CanonicalValue = payload["targets"]
    plain_output: CanonicalValue = payload["plain_output"]
    color_output: CanonicalValue = payload["color_output"]
    exit_code: CanonicalValue = payload["exit_code"]
    if not (
        global_fingerprint is not None
        and index_fingerprint is not None
        and isinstance(raw_targets, list)
        and isinstance(plain_output, str)
        and isinstance(color_output, str)
        and type(exit_code) is int
        and exit_code >= 0
    ):
        return None
    if not all(is_relative_path(value=target) for target in raw_targets):
        return None
    targets: tuple[str, ...] = tuple(cast(list[str], raw_targets))
    if tuple(sorted(targets)) != targets:
        return None
    return CachedCheckOutput(
        global_fingerprint=global_fingerprint,
        index_fingerprint=index_fingerprint,
        targets=targets,
        plain_output=plain_output,
        color_output=color_output,
        exit_code=exit_code,
    )


def file_result_to_record(result: CachedFileResult) -> CacheRecord:
    """Return a validated storage record for one file evaluation."""

    payload: CanonicalValue = _file_result_value(result)
    record: CacheRecord = CacheRecord(kind=CACHE_FILE_RESULT_KIND, payload=payload)
    if file_result_from_record(record) != result:
        raise CacheRecordError("File result contains invalid or noncanonical values.")
    return record


def file_result_from_record(record: CacheRecord) -> CachedFileResult | None:
    """Return a typed file result or None for a semantic miss."""

    payload: dict[str, CanonicalValue] | None = _payload(record=record, kind=CACHE_FILE_RESULT_KIND)
    if payload is None or set(payload) != FILE_RESULT_PAYLOAD_KEYS:
        return None
    path: CanonicalValue = payload["path"]
    fingerprint: CacheFingerprint | None = fingerprint_or_none(payload["source_fingerprint"])
    raw_faults: CanonicalValue = payload["faults"]
    raw_warnings: CanonicalValue = payload["warnings"]
    raw_exceptions: CanonicalValue = payload["applied_exception_keys"]
    raw_dependencies: CanonicalValue = payload["dependencies"]
    raw_override_uses: CanonicalValue = payload["threshold_override_uses"]
    if not (
        is_relative_path(value=path)
        and fingerprint is not None
        and isinstance(raw_faults, list)
        and isinstance(raw_warnings, list)
        and isinstance(raw_exceptions, list)
        and isinstance(raw_dependencies, list)
        and isinstance(raw_override_uses, list)
    ):
        return None
    faults: tuple[CachedFault, ...] | None = _decode_sequence(values=raw_faults, decoder=_fault)
    warnings: tuple[CachedFault, ...] | None = _decode_sequence(values=raw_warnings, decoder=_fault)
    exceptions: tuple[CachedRuleExceptionKey, ...] | None = _decode_sequence(
        values=raw_exceptions, decoder=_exception_key
    )
    dependencies: tuple[DependencyObservation, ...] | None = _decode_sequence(
        values=raw_dependencies, decoder=_dependency
    )
    override_uses: tuple[CachedThresholdOverrideUse, ...] | None = _decode_sequence(
        values=raw_override_uses, decoder=_threshold_override_use
    )
    if (
        faults is None
        or warnings is None
        or exceptions is None
        or dependencies is None
        or override_uses is None
    ):
        return None
    result: CachedFileResult = CachedFileResult(
        path=cast(str, path),
        source_fingerprint=fingerprint,
        faults=faults,
        warnings=warnings,
        applied_exception_keys=exceptions,
        dependencies=dependencies,
        threshold_override_uses=override_uses,
    )
    return result if _file_result_relationships_are_valid(result) else None


def fact_to_record(fact: CachedFact) -> CacheRecord:
    """Return a validated independently tagged fact storage record."""

    if not (
        is_relative_path(value=fact.path)
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

    payload: dict[str, CanonicalValue] | None = _payload(record=record, kind=CACHE_FACT_KIND)
    if payload is None or set(payload) != FACT_PAYLOAD_KEYS:
        return None
    path: CanonicalValue = payload["path"]
    fact_kind: CanonicalValue = payload["fact_kind"]
    fingerprint: CacheFingerprint | None = fingerprint_or_none(payload["source_fingerprint"])
    if not is_relative_path(value=path) or not isinstance(fact_kind, str) or not fact_kind:
        return None
    if fingerprint is None:
        return None
    return CachedFact(
        path=cast(str, path),
        source_fingerprint=fingerprint,
        fact_kind=fact_kind,
        payload=payload["payload"],
    )


def _payload(*, record: CacheRecord, kind: str) -> dict[str, CanonicalValue] | None:
    if record.kind != kind or not isinstance(record.payload, dict):
        return None
    return record.payload


def _index_entry_value(entry: CacheIndexEntry) -> CanonicalValue:
    if not (
        is_relative_path(value=entry.path)
        and is_fingerprint(entry.source_fingerprint.value)
        and is_fingerprint(entry.result_fingerprint.value)
        and is_fingerprint(entry.record_fingerprint.value)
    ):
        raise CacheRecordError("Cache index entry contains invalid identity values.")
    return {
        "path": entry.path,
        "record_fingerprint": entry.record_fingerprint.value,
        "result_fingerprint": entry.result_fingerprint.value,
        "source_fingerprint": entry.source_fingerprint.value,
    }


def _index_entry(value: CanonicalValue) -> CacheIndexEntry | None:
    if not isinstance(value, dict) or set(value) != INDEX_ENTRY_KEYS:
        return None
    path: CanonicalValue = value["path"]
    source_fingerprint: CacheFingerprint | None = fingerprint_or_none(value["source_fingerprint"])
    result_fingerprint: CacheFingerprint | None = fingerprint_or_none(value["result_fingerprint"])
    record_fingerprint: CacheFingerprint | None = fingerprint_or_none(value["record_fingerprint"])
    if (
        not is_relative_path(value=path)
        or source_fingerprint is None
        or result_fingerprint is None
        or record_fingerprint is None
    ):
        return None
    return CacheIndexEntry(
        path=cast(str, path),
        source_fingerprint=source_fingerprint,
        result_fingerprint=result_fingerprint,
        record_fingerprint=record_fingerprint,
    )


def _index_entries_are_ordered(entries: tuple[CacheIndexEntry, ...]) -> bool:
    paths: tuple[str, ...] = tuple(entry.path for entry in entries)
    return paths == tuple(sorted(set(paths)))


def _file_result_relationships_are_valid(result: CachedFileResult) -> bool:
    exception_identities: tuple[tuple[str, str, str | None], ...] = tuple(
        (key.rule, key.path, key.symbol) for key in result.applied_exception_keys
    )
    ordered_exception_identities: tuple[tuple[str, str, str | None], ...] = tuple(
        sorted(set(exception_identities), key=lambda item: (item[0], item[1], item[2] or ""))
    )
    if exception_identities != ordered_exception_identities:
        return False
    if result.threshold_override_uses != tuple(
        sorted(set(result.threshold_override_uses), key=_threshold_override_use_sort_key)
    ):
        return False
    return (
        all(fault.path == result.path for fault in result.faults)
        and all(warning.path == result.path for warning in result.warnings)
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
        "warnings": [_fault_value(item) for item in result.warnings],
        "path": result.path,
        "source_fingerprint": result.source_fingerprint.value,
        "threshold_override_uses": [
            _threshold_override_use_value(item) for item in result.threshold_override_uses
        ],
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
        and is_relative_path(value=path)
        and isinstance(message, str)
        and _optional_position(value=line, minimum=1)
        and _optional_position(value=column, minimum=0)
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


def _threshold_override_use_value(use: CachedThresholdOverrideUse) -> CanonicalValue:
    return {
        "effective_value": use.effective_value,
        "matched_pattern": use.matched_pattern,
        "override_order": use.override_order,
        "reason": use.reason,
        "repository_path": use.repository_path,
        "threshold": use.threshold,
    }


def _threshold_override_use(value: CanonicalValue) -> CachedThresholdOverrideUse | None:
    if not isinstance(value, dict) or set(value) != THRESHOLD_OVERRIDE_USE_KEYS:
        return None
    threshold: CanonicalValue = value["threshold"]
    effective_value: CanonicalValue = value["effective_value"]
    matched_pattern: CanonicalValue = value["matched_pattern"]
    reason: CanonicalValue = value["reason"]
    override_order: CanonicalValue = value["override_order"]
    repository_path: CanonicalValue = value["repository_path"]
    if not (
        isinstance(threshold, str)
        and threshold in {item.value for item in Threshold}
        and type(effective_value) is int
        and effective_value >= 0
        and isinstance(matched_pattern, str)
        and bool(matched_pattern)
        and isinstance(reason, str)
        and bool(reason.strip())
        and type(override_order) is int
        and override_order >= 0
        and is_relative_path(value=repository_path)
    ):
        return None
    return CachedThresholdOverrideUse(
        threshold=threshold,
        effective_value=effective_value,
        matched_pattern=matched_pattern,
        reason=reason,
        override_order=override_order,
        repository_path=cast(str, repository_path),
    )


def _threshold_override_use_sort_key(
    use: CachedThresholdOverrideUse,
) -> tuple[str, str, int, str, str, int]:
    return (
        use.repository_path,
        use.threshold,
        use.override_order,
        use.matched_pattern,
        use.reason,
        use.effective_value,
    )


def _exception_key(value: CanonicalValue) -> CachedRuleExceptionKey | None:
    if not isinstance(value, dict) or set(value) != RULE_EXCEPTION_KEY_KEYS:
        return None
    path: CanonicalValue = value["path"]
    rule: CanonicalValue = value["rule"]
    symbol: CanonicalValue = value["symbol"]
    if not (
        is_relative_path(value=path)
        and is_rule_code(rule)
        and (symbol is None or is_rule_exception_symbol(symbol))
    ):
        return None
    return CachedRuleExceptionKey(
        rule=cast(str, rule),
        path=cast(str, path),
        symbol=cast(str | None, symbol),
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
    *,
    values: list[CanonicalValue],
    decoder: Callable[[CanonicalValue], Decoded | None],
) -> tuple[Decoded, ...] | None:
    decoded: list[Decoded] = []
    for value in values:
        item: Decoded | None = decoder(value)
        if item is None:
            return None
        decoded.append(item)
    return tuple(decoded)


def _optional_position(*, value: CanonicalValue, minimum: int) -> bool:
    return value is None or (type(value) is int and value >= minimum)
