"""Build source-owned normal and supplemental evaluation targets."""

from __future__ import annotations

from pathlib import Path

from strata.discovery.models import DiscoveredTree, ScopedFile
from strata.discovery.types import ScopeName
from strata.evaluation.models import EvaluationSelection, EvaluationTarget
from strata.rules.authoring.models import CustomRuleRegistration, RuleSpec
from strata.rules.roles.types import RoleCode


def build_evaluation_targets(
    *,
    tree: DiscoveredTree,
    selection: EvaluationSelection,
    ruleset: tuple[RuleSpec, ...],
    warning_rules: tuple[RuleSpec, ...],
    custom_rule_registrations: tuple[CustomRuleRegistration, ...],
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
    if not blocking_coverage and not warning_coverage:
        return tuple(targets.values())
    grouped: dict[Path, list[CustomRuleRegistration]] = {}
    for registration in custom_rule_registrations:
        grouped.setdefault(registration.source_path.resolve(), []).append(registration)
    discovered: dict[Path, ScopedFile] = {
        scoped_file.path: scoped_file for scoped_file in tree.files
    }
    for path, registrations in grouped.items():
        current: EvaluationTarget | None = targets.get(path)
        scoped_file: ScopedFile = (
            current.scoped_file
            if current is not None
            else discovered.get(path, _supplemental_scoped_file(path=path, tree=tree))
        )
        targets[path] = EvaluationTarget(
            scoped_file=scoped_file,
            direct=current.direct if current is not None else False,
            custom_rule_registrations=tuple(registrations),
            custom_rule_coverage_warning=warning_coverage,
        )
    return tuple(sorted(targets.values(), key=lambda item: str(item.scoped_file.path)))


def _supplemental_scoped_file(*, path: Path, tree: DiscoveredTree) -> ScopedFile:
    return ScopedFile(
        path=path,
        root=tree.repo_root.path,
        scope=ScopeName.TOOLING,
        relative_parts=path.relative_to(tree.repo_root.path).parts,
    )
