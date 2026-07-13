"""Cycle-safe static rule-to-test association."""

from __future__ import annotations

from collections.abc import Mapping

from strata.analysis.models import (
    EvaluateRuleCallFact,
    ImportAliasFact,
    ImportFact,
    ModuleDeclarationFacts,
    ModuleStatementFact,
    RuleTestAssociationFact,
    SourceLocation,
    StaticReferenceFact,
)
from strata.analysis.types import Analysis


class RuleTestAssociator:
    """Resolve re-exports and deduplicate static harness cases per test and rule."""

    def __init__(self, *, modules: Mapping[str, Analysis]) -> None:
        """Bind the repository module analyses available for re-export resolution."""

        self._modules: Mapping[str, Analysis] = modules

    def associate(
        self, *, calls: tuple[EvaluateRuleCallFact, ...]
    ) -> tuple[RuleTestAssociationFact, ...]:
        """Return deterministic associations for resolvable test-owned calls."""

        grouped: dict[
            tuple[SourceLocation, StaticReferenceFact],
            tuple[str, set[SourceLocation], set[SourceLocation], bool],
        ] = {}
        for call in calls:
            if (
                call.test_function_name is None
                or call.test_function_location is None
                or call.rule_reference is None
            ):
                continue
            reference: StaticReferenceFact | None = self._resolve(
                reference=call.rule_reference,
                visited=frozenset(),
            )
            if reference is None:
                continue
            key: tuple[SourceLocation, StaticReferenceFact] = (
                call.test_function_location,
                reference,
            )
            current: tuple[str, set[SourceLocation], set[SourceLocation], bool] | None = (
                grouped.get(key)
            )
            if current is None:
                current = (call.test_function_name, set(), set(), False)
                grouped[key] = current
            current[1].add(call.location)
            current[2].update(call.case_locations)
            grouped[key] = (
                current[0],
                current[1],
                current[2],
                current[3] or call.unknown_case_count,
            )
        associations: list[RuleTestAssociationFact] = []
        for (function_location, reference), value in sorted(
            grouped.items(),
            key=lambda item: (
                str(item[0][0].path),
                item[0][0].line,
                item[0][0].column,
                item[0][1].module_name,
                item[0][1].symbol_name,
            ),
        ):
            function_name, call_locations, case_locations, unknown = value
            associations.append(
                RuleTestAssociationFact(
                    rule_reference=reference,
                    test_function_name=function_name,
                    test_function_location=function_location,
                    call_locations=tuple(sorted(call_locations, key=self._location_key)),
                    case_locations=tuple(sorted(case_locations, key=self._location_key)),
                    unknown_case_count=unknown,
                )
            )
        return tuple(associations)

    def _resolve(
        self,
        *,
        reference: StaticReferenceFact,
        visited: frozenset[StaticReferenceFact],
    ) -> StaticReferenceFact | None:
        if reference in visited:
            return None
        analysis: Analysis | None = self._modules.get(reference.module_name)
        if analysis is None:
            return reference
        declarations: ModuleDeclarationFacts = analysis.facts.module_declarations()
        matching_statements: tuple[ModuleStatementFact, ...] = tuple(
            statement
            for statement in declarations.statements
            if statement.function_name == reference.symbol_name
            or statement.class_name == reference.symbol_name
            or reference.symbol_name in statement.assignment_target_names
        )
        decorated: tuple[ModuleStatementFact, ...] = tuple(
            statement for statement in matching_statements if statement.rule_decorated_function
        )
        if len(decorated) == 1 and len(matching_statements) == 1:
            return reference
        if matching_statements:
            return None
        candidates: set[StaticReferenceFact] = set()
        for import_fact in analysis.facts.references().imports:
            candidate: StaticReferenceFact | None = self._reexport_candidate(
                import_fact=import_fact,
                symbol_name=reference.symbol_name,
            )
            if candidate is not None:
                candidates.add(candidate)
        if len(candidates) != 1:
            return None
        return self._resolve(reference=next(iter(candidates)), visited=visited | {reference})

    @staticmethod
    def _reexport_candidate(
        *, import_fact: ImportFact, symbol_name: str
    ) -> StaticReferenceFact | None:
        if not import_fact.top_level or not import_fact.from_import or import_fact.relative_level:
            return None
        matching: tuple[ImportAliasFact, ...] = tuple(
            alias for alias in import_fact.aliases if alias.bound_name == symbol_name
        )
        if len(matching) != 1 or not import_fact.module_parts:
            return None
        return StaticReferenceFact(
            module_name=".".join(import_fact.module_parts),
            symbol_name=matching[0].imported_name,
        )

    @staticmethod
    def _location_key(location: SourceLocation) -> tuple[str, int, int]:
        return str(location.path), location.line, location.column
