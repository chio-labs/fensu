"""Plan one deterministic callback anchor for each declared execution owner."""

from __future__ import annotations

from pathlib import Path

from strata.discovery.constants import INIT_MODULE_FILE_NAME
from strata.discovery.main.position import position_facts
from strata.discovery.main.route import families_for_scope
from strata.discovery.models import PositionFacts, ScopedFile
from strata.evaluation.models import EvaluationTarget
from strata.rules.authoring.models import RuleSpec
from strata.rules.authoring.types import ExecutionOwner, Family

type _OwnerKey = tuple[str, ...]
_EMPTY_CODES: frozenset[str] = frozenset()


def planned_rule_codes(
    *,
    targets: tuple[EvaluationTarget, ...],
    rules: tuple[RuleSpec, ...],
) -> dict[Path, frozenset[str]]:
    """Return rule codes assigned to deterministic selected-file owner anchors."""

    direct_targets: tuple[EvaluationTarget, ...] = tuple(
        target for target in targets if target.direct
    )
    positions: dict[Path, PositionFacts] = {
        target.scoped_file.path: position_facts(target.scoped_file) for target in direct_targets
    }
    families_by_path: dict[Path, frozenset[Family]] = {
        target.scoped_file.path: families_for_scope(scoped_file=target.scoped_file)
        for target in direct_targets
    }
    codes_by_path: dict[Path, set[str]] = {
        target.scoped_file.path: set() for target in direct_targets
    }
    file_codes_by_family: dict[Family, set[str]] = {}
    universal_file_codes: set[str] = set()
    broader_rules: list[RuleSpec] = []
    for rule in rules:
        if rule.execution_owner is not ExecutionOwner.FILE:
            broader_rules.append(rule)
        elif rule.family is Family.CUSTOM:
            universal_file_codes.add(rule.code)
        else:
            file_codes_by_family.setdefault(rule.family, set()).add(rule.code)
    for target in direct_targets:
        target_codes: set[str] = codes_by_path[target.scoped_file.path]
        target_codes.update(universal_file_codes)
        for family in families_by_path[target.scoped_file.path]:
            target_codes.update(file_codes_by_family.get(family, _EMPTY_CODES))
    for rule in broader_rules:
        grouped: dict[_OwnerKey, list[EvaluationTarget]] = {}
        for target in direct_targets:
            scoped_file: ScopedFile = target.scoped_file
            if (
                rule.family is not Family.CUSTOM
                and rule.family not in families_by_path[scoped_file.path]
            ):
                continue
            owner_key: _OwnerKey | None = _owner_key(
                target=target,
                position=positions[scoped_file.path],
                owner=rule.execution_owner,
            )
            if owner_key is not None:
                grouped.setdefault(owner_key, []).append(target)
        for owned_targets in grouped.values():
            anchor: EvaluationTarget = min(
                owned_targets,
                key=lambda target: _anchor_key(
                    target=target,
                    position=positions[target.scoped_file.path],
                    owner=rule.execution_owner,
                ),
            )
            codes_by_path[anchor.scoped_file.path].add(rule.code)
    return {path: frozenset(codes) for path, codes in codes_by_path.items()}


def _owner_key(
    *,
    target: EvaluationTarget,
    position: PositionFacts,
    owner: ExecutionOwner,
) -> _OwnerKey | None:
    scoped_file: ScopedFile = target.scoped_file
    if owner is ExecutionOwner.FILE:
        return (owner.value, str(scoped_file.path))
    if owner is ExecutionOwner.PROJECT:
        return (owner.value,)
    if owner is ExecutionOwner.PACKAGE:
        return (owner.value, str(scoped_file.path.parent))
    if owner is ExecutionOwner.SCOPE:
        return (owner.value, scoped_file.scope.value, str(scoped_file.root))
    if owner is ExecutionOwner.DOMAIN and position.domain is not None:
        return (owner.value, scoped_file.scope.value, str(scoped_file.root), position.domain)
    if owner is ExecutionOwner.LEAF and position.domain is not None:
        return (
            owner.value,
            scoped_file.scope.value,
            str(scoped_file.root),
            position.domain,
            position.subdomain or "",
        )
    if owner is ExecutionOwner.SUBDOMAIN and position.subdomain is not None:
        return (
            owner.value,
            scoped_file.scope.value,
            str(scoped_file.root),
            position.domain or "",
            position.subdomain,
        )
    return None


def _anchor_key(
    *,
    target: EvaluationTarget,
    position: PositionFacts,
    owner: ExecutionOwner,
) -> tuple[bool, int, str]:
    relative_parts: tuple[str, ...] = target.scoped_file.relative_parts
    owner_depth: dict[ExecutionOwner, int] = {
        ExecutionOwner.SCOPE: 1,
        ExecutionOwner.DOMAIN: 2,
        ExecutionOwner.SUBDOMAIN: 3,
    }
    expected_depth: int | None = owner_depth.get(owner)
    if owner is ExecutionOwner.LEAF:
        expected_depth = 3 if position.subdomain is not None else 2
    is_owner_init: bool = (
        expected_depth is not None
        and len(relative_parts) == expected_depth
        and relative_parts[-1] == INIT_MODULE_FILE_NAME
    )
    if owner is ExecutionOwner.PACKAGE:
        is_owner_init = relative_parts[-1] == INIT_MODULE_FILE_NAME
    return (
        not is_owner_init,
        len(relative_parts),
        str(target.scoped_file.path),
    )
