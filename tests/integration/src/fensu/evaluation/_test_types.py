"""Test case types for architecture graph integration behavior."""

from dataclasses import dataclass

from fensu import ImportResolution, RuleCase


@dataclass(frozen=True, slots=True)
class ProjectArchitectureGraphTestCase:
    """Project graph rule input and expected observations."""

    description: str
    rule_case: RuleCase
    expected_fault_count: int
    expected_invocations: tuple[int, ...]
    expected_dependency_kinds: frozenset[str]


@dataclass(frozen=True, slots=True)
class FileArchitectureGraphTestCase:
    """File graph rule input and expected finding count."""

    description: str
    rule_case: RuleCase
    expected_fault_count: int


@dataclass(frozen=True, slots=True)
class AmbiguousModuleGraphTestCase:
    """Duplicate module fixture and expected unresolved edge state."""

    description: str
    expected_edge_count: int
    expected_resolution: ImportResolution
    expected_target: object | None


@dataclass(frozen=True, slots=True)
class MultiAliasGraphParityTestCase:
    """Multi-alias import input and expected single statement finding."""

    description: str
    rule_case: RuleCase
    expected_fault_count: int
