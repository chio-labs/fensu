"""Build source-owned normal and supplemental evaluation targets."""

from __future__ import annotations

from dataclasses import replace
from importlib import import_module
from pathlib import Path
from types import ModuleType

from fensu.analysis.constants import NATIVE_FACT_MODULE_NAME
from fensu.discovery.models import DiscoveredTree, ScopedFile
from fensu.discovery.types import ScopeName
from fensu.evaluation.models import EvaluationSelection, EvaluationTarget
from fensu.rules.authoring.models import CustomRuleRegistration, RuleSpec
from fensu.rules.roles.types import RoleCode


def build_evaluation_targets(
    *,
    tree: DiscoveredTree,
    selection: EvaluationSelection,
    ruleset: tuple[RuleSpec, ...],
    warning_rules: tuple[RuleSpec, ...],
    custom_rule_registrations: tuple[CustomRuleRegistration, ...],
    plan_rule_owners: bool = True,
) -> tuple[EvaluationTarget, ...]:
    """Merge supplemental coverage work into records owned by each rule source."""

    targets: dict[Path, EvaluationTarget] = {
        scoped_file.path: EvaluationTarget(scoped_file=scoped_file, direct=True)
        for scoped_file in selection.files
    }
    blocking_coverage: bool = any(
        rule.code == RoleCode.CUSTOM_RULE_TEST_COVERAGE for rule in ruleset
    )
    warning_coverage: bool = any(
        rule.code == RoleCode.CUSTOM_RULE_TEST_COVERAGE for rule in warning_rules
    )
    if blocking_coverage or warning_coverage:
        targets = _supplemented_targets(
            targets=targets,
            registrations=custom_rule_registrations,
            tree=tree,
            warning_coverage=warning_coverage,
        )
    ordered: tuple[EvaluationTarget, ...] = tuple(
        sorted(targets.values(), key=lambda item: str(item.scoped_file.path))
    )
    if not plan_rule_owners:
        return ordered
    native: ModuleType = import_module(NATIVE_FACT_MODULE_NAME)
    planned: list[tuple[list[str], list[tuple[str, str]]]] = native.plan_native_execution_owners(
        [
            (
                target.scoped_file.path.relative_to(tree.repo_root.path).as_posix(),
                target.scoped_file.scope.value,
                str(target.scoped_file.root),
                list(target.scoped_file.relative_parts),
                target.direct,
            )
            for target in ordered
        ],
        [
            (rule.code, rule.family.value, rule.execution_owner.value)
            for rule in (*ruleset, *warning_rules)
        ],
    )
    return tuple(
        replace(
            target,
            applicable_rule_codes=frozenset(codes),
        )
        for target, (codes, _identities) in zip(ordered, planned, strict=True)
    )


def _supplemented_targets(
    *,
    targets: dict[Path, EvaluationTarget],
    registrations: tuple[CustomRuleRegistration, ...],
    tree: DiscoveredTree,
    warning_coverage: bool,
) -> dict[Path, EvaluationTarget]:
    supplemented: dict[Path, EvaluationTarget] = dict(targets)
    grouped: dict[Path, list[CustomRuleRegistration]] = {}
    for registration in registrations:
        grouped.setdefault(registration.source_path.resolve(), []).append(registration)
    discovered: dict[Path, ScopedFile] = {
        scoped_file.path: scoped_file for scoped_file in tree.files
    }
    for path, owned_registrations in grouped.items():
        current: EvaluationTarget | None = supplemented.get(path)
        scoped_file: ScopedFile = (
            current.scoped_file
            if current is not None
            else discovered.get(path, _supplemental_scoped_file(path=path, tree=tree))
        )
        supplemented[path] = EvaluationTarget(
            scoped_file=scoped_file,
            direct=current.direct if current is not None else False,
            custom_rule_registrations=tuple(owned_registrations),
            custom_rule_coverage_warning=warning_coverage,
        )
    return supplemented


def _supplemental_scoped_file(*, path: Path, tree: DiscoveredTree) -> ScopedFile:
    return ScopedFile(
        path=path,
        root=tree.repo_root.path,
        scope=ScopeName.TOOLING,
        relative_parts=path.relative_to(tree.repo_root.path).parts,
    )
