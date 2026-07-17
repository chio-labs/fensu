"""Convert runtime file evaluations into backend-neutral cache records."""

from __future__ import annotations

from functools import cache
from pathlib import Path

from strata.analysis.models import ProjectDependency
from strata.analysis.types import ProjectDependencyKind
from strata.cache.fingerprints.main._file_result import file_result_fingerprints
from strata.cache.fingerprints.models import CacheFingerprint, FileResultFingerprints
from strata.cache.fingerprints.types import CanonicalValue
from strata.cache.results._helpers.paths import relative_repository_path
from strata.cache.results._helpers.serialization import prepared_file_result_to_record
from strata.cache.results.models import (
    CachedCollectionContribution,
    CachedFault,
    CachedFileResult,
    CachedRuleExceptionKey,
    CachedThresholdOverrideUse,
    CacheIndexEntry,
    DependencyObservation,
    PreparedFileResult,
    PublicationCandidate,
    PublicationPreparation,
)
from strata.cache.results.types import (
    DependencyAnswer,
    DependencyAnswerCache,
    DependencyPathCache,
    DependencyReferenceKey,
)
from strata.cache.storage.exceptions import CacheRecordError
from strata.cache.storage.main._encode_record import encode_record
from strata.cache.storage.models import CacheRecord
from strata.evaluation.models import FileEvaluation, RuleExceptionKey, ThresholdOverrideUse
from strata.rules.authoring.main.is_rule_code import is_rule_code
from strata.rules.authoring.models import Fault
from strata.rules.authoring.types import Threshold


class _PublicationState:
    """Prepare compact file records and one shared dependency generation."""

    def __init__(self, *, repo_root: Path, global_fingerprint: CacheFingerprint) -> None:
        self._repo_root: Path = repo_root
        self._global_fingerprint: CacheFingerprint = global_fingerprint
        self._dependency_answers: DependencyAnswerCache = {}
        self._dependency_paths: DependencyPathCache = {}
        self._observations: dict[DependencyReferenceKey, DependencyObservation] = {}
        self._raw_dependencies: dict[
            DependencyReferenceKey,
            tuple[Path, None | bool | str | tuple[Path, ...]],
        ] = {}
        self._candidates: list[PublicationCandidate] = []
        self._non_cacheable: int = 0
        self._internal_error: bool = False
        self._observations_conflicted: bool = False

    def prepare(self, *, evaluation: FileEvaluation) -> None:
        """Prepare one evaluation or classify it as non-cacheable."""

        try:
            candidate: PublicationCandidate | None = self._candidate(evaluation=evaluation)
        except CacheRecordError:
            self._internal_error = True
            self._non_cacheable += 1
            return
        if candidate is None:
            self._non_cacheable += 1
            return
        self._candidates.append(candidate)

    def result(self) -> PublicationPreparation:
        """Return the complete compact publication preparation."""

        return PublicationPreparation(
            candidates=tuple(self._candidates),
            non_cacheable=self._non_cacheable,
            internal_error=self._internal_error,
            observations=tuple(self._observations.values()),
            observations_conflicted=self._observations_conflicted,
        )

    def _candidate(self, *, evaluation: FileEvaluation) -> PublicationCandidate | None:
        path: str | None = relative_repository_path(path=evaluation.path, repo_root=self._repo_root)
        if path is None:
            return None
        faults: tuple[CachedFault, ...] | None = self._faults(
            faults=evaluation.faults,
            requester_path=path,
        )
        warnings: tuple[CachedFault, ...] | None = self._faults(
            faults=evaluation.warnings,
            requester_path=path,
        )
        if faults is None or warnings is None:
            return None
        converted_exception_keys: list[CachedRuleExceptionKey] = []
        for key in evaluation.applied_exception_keys:
            cached_key: CachedRuleExceptionKey | None = _cached_exception_key(
                key=key,
                requester_path=path,
            )
            if cached_key is None:
                return None
            converted_exception_keys.append(cached_key)
        exception_keys: tuple[CachedRuleExceptionKey, ...] = tuple(converted_exception_keys)
        dependency_references: list[CanonicalValue] = []
        for dependency in evaluation.dependencies:
            reference: CanonicalValue | None = self._dependency_reference(
                dependency=dependency,
                requester=evaluation.path,
                requester_path=path,
            )
            if reference is None:
                return None
            dependency_references.append(reference)
        result: CachedFileResult = CachedFileResult(
            path=path,
            source_fingerprint=CacheFingerprint(evaluation.source_fingerprint),
            faults=faults,
            warnings=warnings,
            applied_exception_keys=exception_keys,
            dependencies=(),
            threshold_override_uses=tuple(
                _cached_threshold_override_use(use) for use in evaluation.threshold_override_uses
            ),
        )
        record: CacheRecord = prepared_file_result_to_record(
            result=result,
            dependency_references=dependency_references,
        )
        encoded: bytes = encode_record(record=record, payload_is_validated=True)
        fingerprints: FileResultFingerprints = file_result_fingerprints(
            global_fingerprint=self._global_fingerprint,
            encoded=encoded,
        )
        return PublicationCandidate(
            entry=CacheIndexEntry(
                path=path,
                source_fingerprint=result.source_fingerprint,
                result_fingerprint=fingerprints.result,
                record_fingerprint=fingerprints.record,
            ),
            encoded=encoded,
        )

    def _faults(
        self,
        *,
        faults: tuple[Fault, ...],
        requester_path: str,
    ) -> tuple[CachedFault, ...] | None:
        converted: list[CachedFault] = []
        for fault in faults:
            cached: CachedFault | None = _cached_fault(
                fault=fault,
                requester_path=requester_path,
                repo_root=self._repo_root,
            )
            if cached is None:
                return None
            converted.append(cached)
        return tuple(converted)

    def _dependency_reference(
        self,
        *,
        dependency: ProjectDependency,
        requester: Path,
        requester_path: str,
    ) -> CanonicalValue | None:
        if dependency.requester != requester:
            return None
        query_path: str | None = _cached_dependency_path(
            path=dependency.query_path,
            repo_root=self._repo_root,
            allow_root=True,
            dependency_paths=self._dependency_paths,
        )
        try:
            kind: ProjectDependencyKind = ProjectDependencyKind(dependency.kind)
        except ValueError:
            return None
        if query_path is None:
            return None
        key: DependencyReferenceKey = (query_path, kind, dependency.pattern, dependency.recursive)
        signature: tuple[Path, None | bool | str | tuple[Path, ...]] = (
            dependency.dependency,
            dependency.answer,
        )
        existing_signature: tuple[Path, None | bool | str | tuple[Path, ...]] | None = (
            self._raw_dependencies.get(key)
        )
        if existing_signature is not None and existing_signature != signature:
            self._observations_conflicted = True
        observation: DependencyObservation | None = self._observations.get(key)
        if observation is None:
            observation = self._new_observation(
                dependency=dependency,
                requester_path=requester_path,
                query_path=query_path,
                kind=kind,
            )
            if observation is None:
                return None
            self._observations[key] = observation
            self._raw_dependencies[key] = signature
        elif requester_path < observation.requester_path:
            self._observations[key] = DependencyObservation(
                requester_path=requester_path,
                query_path=observation.query_path,
                dependency_path=observation.dependency_path,
                kind=observation.kind,
                answer=observation.answer,
                pattern=observation.pattern,
                recursive=observation.recursive,
            )
        return {
            "kind": kind.value,
            "pattern": dependency.pattern,
            "query_path": query_path,
            "recursive": dependency.recursive,
        }

    def _new_observation(
        self,
        *,
        dependency: ProjectDependency,
        requester_path: str,
        query_path: str,
        kind: ProjectDependencyKind,
    ) -> DependencyObservation | None:
        dependency_path: str | None = _cached_dependency_path(
            path=dependency.dependency,
            repo_root=self._repo_root,
            allow_root=True,
            dependency_paths=self._dependency_paths,
        )
        answer: DependencyAnswer | None = _dependency_answer(
            answer=dependency.answer,
            repo_root=self._repo_root,
            dependency_answers=self._dependency_answers,
            dependency_paths=self._dependency_paths,
        )
        if dependency_path is None or (answer is None and dependency.answer is not None):
            return None
        return DependencyObservation(
            requester_path=requester_path,
            query_path=query_path,
            dependency_path=dependency_path,
            kind=kind,
            answer=answer,
            pattern=dependency.pattern,
            recursive=dependency.recursive,
        )


def build_publication_preparation(
    *,
    evaluations: tuple[FileEvaluation, ...],
    repo_root: Path,
    global_fingerprint: CacheFingerprint,
) -> PublicationPreparation:
    """Prepare compact file records and one deduplicated dependency generation."""

    state: _PublicationState = _PublicationState(
        repo_root=repo_root,
        global_fingerprint=global_fingerprint,
    )
    for evaluation in evaluations:
        state.prepare(evaluation=evaluation)
    return state.result()


def build_cached_file_result(
    *,
    evaluation: FileEvaluation,
    repo_root: Path,
    dependency_answers: DependencyAnswerCache | None = None,
    dependency_paths: DependencyPathCache | None = None,
) -> PreparedFileResult | None:
    """Return a cache-safe file result with its record, or None for unsupported ownership."""

    path: str | None = relative_repository_path(path=evaluation.path, repo_root=repo_root)
    if path is None:
        return None
    faults: list[CachedFault] = []
    for fault in evaluation.faults:
        cached_fault: CachedFault | None = _cached_fault(
            fault=fault,
            requester_path=path,
            repo_root=repo_root,
        )
        if cached_fault is None:
            return None
        faults.append(cached_fault)
    warnings: list[CachedFault] = []
    for warning in evaluation.warnings:
        cached_warning: CachedFault | None = _cached_fault(
            fault=warning,
            requester_path=path,
            repo_root=repo_root,
        )
        if cached_warning is None:
            return None
        warnings.append(cached_warning)
    exception_keys: list[CachedRuleExceptionKey] = []
    for key in evaluation.applied_exception_keys:
        cached_key: CachedRuleExceptionKey | None = _cached_exception_key(
            key=key,
            requester_path=path,
        )
        if cached_key is None:
            return None
        exception_keys.append(cached_key)
    dependencies: list[DependencyObservation] = []
    active_dependency_answers: DependencyAnswerCache = (
        {} if dependency_answers is None else dependency_answers
    )
    active_dependency_paths: DependencyPathCache = (
        {} if dependency_paths is None else dependency_paths
    )
    for dependency in evaluation.dependencies:
        observation: DependencyObservation | None = _dependency_observation(
            dependency=dependency,
            requester=evaluation.path,
            requester_path=path,
            repo_root=repo_root,
            dependency_answers=active_dependency_answers,
            dependency_paths=active_dependency_paths,
        )
        if observation is None:
            return None
        dependencies.append(observation)
    result: CachedFileResult = CachedFileResult(
        path=path,
        source_fingerprint=CacheFingerprint(evaluation.source_fingerprint),
        faults=tuple(faults),
        warnings=tuple(warnings),
        applied_exception_keys=tuple(exception_keys),
        dependencies=tuple(dependencies),
        threshold_override_uses=tuple(
            _cached_threshold_override_use(use) for use in evaluation.threshold_override_uses
        ),
    )
    record: CacheRecord = prepared_file_result_to_record(result=result)
    return PreparedFileResult(result=result, record=record)


def build_collection_contributions(
    *,
    evaluations: tuple[FileEvaluation, ...],
    repo_root: Path,
) -> tuple[CachedCollectionContribution, ...] | None:
    """Return sorted nonempty collection inputs, or None for unsupported ownership."""

    contributions: list[CachedCollectionContribution] = []
    try:
        for evaluation in evaluations:
            contribution: CachedCollectionContribution | None = _collection_contribution(
                evaluation=evaluation,
                repo_root=repo_root,
            )
            if contribution is not None:
                contributions.append(contribution)
    except CacheRecordError:
        return None
    return tuple(sorted(contributions, key=lambda contribution: contribution.path))


def _collection_contribution(
    *,
    evaluation: FileEvaluation,
    repo_root: Path,
) -> CachedCollectionContribution | None:
    if not (
        evaluation.faults
        or evaluation.warnings
        or evaluation.applied_exception_keys
        or evaluation.threshold_override_uses
    ):
        return None
    path: str | None = relative_repository_path(path=evaluation.path, repo_root=repo_root)
    if path is None:
        raise CacheRecordError("Collection contribution path is outside the repository.")
    faults: list[CachedFault] = []
    for fault in evaluation.faults:
        cached_fault: CachedFault | None = _cached_fault(
            fault=fault,
            requester_path=path,
            repo_root=repo_root,
        )
        if cached_fault is None:
            raise CacheRecordError("Collection contribution fault is not cache-safe.")
        faults.append(cached_fault)
    warnings: list[CachedFault] = []
    for warning in evaluation.warnings:
        cached_warning: CachedFault | None = _cached_fault(
            fault=warning,
            requester_path=path,
            repo_root=repo_root,
        )
        if cached_warning is None:
            raise CacheRecordError("Collection contribution warning is not cache-safe.")
        warnings.append(cached_warning)
    exception_keys: list[CachedRuleExceptionKey] = []
    for key in evaluation.applied_exception_keys:
        cached_key: CachedRuleExceptionKey | None = _cached_exception_key(
            key=key,
            requester_path=path,
        )
        if cached_key is None:
            raise CacheRecordError("Collection contribution exception key is not cache-safe.")
        exception_keys.append(cached_key)
    return CachedCollectionContribution(
        path=path,
        faults=tuple(faults),
        warnings=tuple(warnings),
        applied_exception_keys=tuple(exception_keys),
        threshold_override_uses=tuple(
            _cached_threshold_override_use(use) for use in evaluation.threshold_override_uses
        ),
    )


def restore_contribution_evaluation(
    *,
    contribution: CachedCollectionContribution,
    source_fingerprint: CacheFingerprint,
    repo_root: Path,
) -> FileEvaluation:
    """Restore one persisted collection contribution to runtime evaluation models."""

    return restore_file_evaluation(
        result=CachedFileResult(
            path=contribution.path,
            source_fingerprint=source_fingerprint,
            faults=contribution.faults,
            warnings=contribution.warnings,
            applied_exception_keys=contribution.applied_exception_keys,
            dependencies=(),
            threshold_override_uses=contribution.threshold_override_uses,
        ),
        repo_root=repo_root,
    )


def restore_file_evaluation(*, result: CachedFileResult, repo_root: Path) -> FileEvaluation:
    """Restore one validated backend-neutral result to runtime evaluation models."""

    return FileEvaluation(
        path=_restored_path(repo_root=repo_root, relative=result.path),
        source_fingerprint=result.source_fingerprint.value,
        faults=tuple(
            Fault(
                code=fault.code,
                path=_restored_path(repo_root=repo_root, relative=fault.path),
                message=fault.message,
                line=fault.line,
                column=fault.column,
                remediation=fault.remediation,
            )
            for fault in result.faults
        ),
        warnings=tuple(
            Fault(
                code=warning.code,
                path=_restored_path(repo_root=repo_root, relative=warning.path),
                message=warning.message,
                line=warning.line,
                column=warning.column,
                remediation=warning.remediation,
            )
            for warning in result.warnings
        ),
        applied_exception_keys=tuple(
            RuleExceptionKey(rule=key.rule, path=key.path, symbol=key.symbol)
            for key in result.applied_exception_keys
        ),
        dependencies=tuple(
            ProjectDependency(
                requester=_restored_path(repo_root=repo_root, relative=dependency.requester_path),
                query_path=_restored_path(repo_root=repo_root, relative=dependency.query_path),
                dependency=_restored_path(
                    repo_root=repo_root,
                    relative=dependency.dependency_path,
                ),
                kind=dependency.kind,
                answer=_restore_dependency_answer(answer=dependency.answer, repo_root=repo_root),
                pattern=dependency.pattern,
                recursive=dependency.recursive,
            )
            for dependency in result.dependencies
        ),
        threshold_override_uses=tuple(
            ThresholdOverrideUse(
                threshold=Threshold(use.threshold),
                effective_value=use.effective_value,
                matched_pattern=use.matched_pattern,
                reason=use.reason,
                override_order=use.override_order,
                repository_path=use.repository_path,
            )
            for use in result.threshold_override_uses
        ),
    )


def _cached_threshold_override_use(use: ThresholdOverrideUse) -> CachedThresholdOverrideUse:
    return CachedThresholdOverrideUse(
        threshold=use.threshold.value,
        effective_value=use.effective_value,
        matched_pattern=use.matched_pattern,
        reason=use.reason,
        override_order=use.override_order,
        repository_path=use.repository_path,
    )


def _cached_fault(
    *,
    fault: Fault,
    requester_path: str,
    repo_root: Path,
) -> CachedFault | None:
    path: str | None = relative_repository_path(path=fault.path, repo_root=repo_root)
    if path is None or path != requester_path:
        return None
    if (
        not is_rule_code(fault.code)
        or not isinstance(fault.message, str)
        or not _optional_position(value=fault.line, minimum=1)
        or not _optional_position(value=fault.column, minimum=0)
        or (fault.line is None and fault.column is not None)
        or (fault.remediation is not None and not isinstance(fault.remediation, str))
    ):
        raise CacheRecordError("File evaluation contains an invalid fault value.")
    return CachedFault(
        code=fault.code,
        path=path,
        message=fault.message,
        line=fault.line,
        column=fault.column,
        remediation=fault.remediation,
    )


def _cached_exception_key(
    *,
    key: RuleExceptionKey,
    requester_path: str,
) -> CachedRuleExceptionKey | None:
    if key.path != requester_path:
        return None
    return CachedRuleExceptionKey(rule=key.rule, path=key.path, symbol=key.symbol)


def _dependency_observation(
    *,
    dependency: ProjectDependency,
    requester: Path,
    requester_path: str,
    repo_root: Path,
    dependency_answers: DependencyAnswerCache,
    dependency_paths: DependencyPathCache,
) -> DependencyObservation | None:
    query_path: str | None = _cached_dependency_path(
        path=dependency.query_path,
        repo_root=repo_root,
        allow_root=True,
        dependency_paths=dependency_paths,
    )
    dependency_path: str | None = _cached_dependency_path(
        path=dependency.dependency,
        repo_root=repo_root,
        allow_root=True,
        dependency_paths=dependency_paths,
    )
    answer: DependencyAnswer | None = _dependency_answer(
        answer=dependency.answer,
        repo_root=repo_root,
        dependency_answers=dependency_answers,
        dependency_paths=dependency_paths,
    )
    try:
        kind: ProjectDependencyKind = ProjectDependencyKind(dependency.kind)
    except ValueError:
        return None
    if (
        dependency.requester != requester
        or query_path is None
        or dependency_path is None
        or (answer is None and dependency.answer is not None)
    ):
        return None
    return DependencyObservation(
        requester_path=requester_path,
        query_path=query_path,
        dependency_path=dependency_path,
        kind=kind,
        answer=answer,
        pattern=dependency.pattern,
        recursive=dependency.recursive,
    )


def _dependency_answer(
    *,
    answer: None | bool | str | tuple[Path, ...],
    repo_root: Path,
    dependency_answers: DependencyAnswerCache,
    dependency_paths: DependencyPathCache,
) -> DependencyAnswer | None:
    if not isinstance(answer, tuple):
        return answer
    identity: int = id(answer)
    if identity in dependency_answers:
        return dependency_answers[identity]
    paths: list[str] = []
    for path in answer:
        relative_path: str | None = _cached_dependency_path(
            path=path,
            repo_root=repo_root,
            allow_root=True,
            dependency_paths=dependency_paths,
        )
        if relative_path is None:
            return None
        paths.append(relative_path)
    converted: tuple[str, ...] = tuple(paths)
    dependency_answers[identity] = converted
    return converted


def _cached_dependency_path(
    *,
    path: Path,
    repo_root: Path,
    allow_root: bool,
    dependency_paths: DependencyPathCache,
) -> str | None:
    key: tuple[int, bool] = (id(path), allow_root)
    if key not in dependency_paths:
        dependency_paths[key] = relative_repository_path(
            path=path,
            repo_root=repo_root,
            allow_root=allow_root,
        )
    return dependency_paths[key]


def _optional_position(*, value: int | None, minimum: int) -> bool:
    return value is None or (type(value) is int and value >= minimum)


def _restore_dependency_answer(
    *,
    answer: DependencyAnswer,
    repo_root: Path,
) -> None | bool | str | tuple[Path, ...]:
    if isinstance(answer, tuple):
        return tuple(_restored_path(repo_root=repo_root, relative=path) for path in answer)
    return answer


@cache
def _restored_path(*, repo_root: Path, relative: str) -> Path:
    return repo_root / relative
