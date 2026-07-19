"""Tests for public rule-authoring fact families extracted by Python."""

from pathlib import Path

import pytest

from fensu.analysis.models import (
    AssignmentReferenceFact,
    ClassDeclarationFact,
    ComparisonFact,
    LiteralArgumentFact,
    LocalCallEdgeFact,
    NamedCallFact,
    ParameterMutationFact,
    ParameterMutationOccurrenceFact,
    QualifiedReferenceFact,
)
from fensu.analysis.types import Analysis
from tests.unit.src.fensu.analysis._test_types import (
    AssignmentReferenceFamilyTestCase,
    ClassDeclarationFamilyTestCase,
    ComparisonFamilyTestCase,
    LocalCallEdgeFamilyTestCase,
    NamedCallFamilyTestCase,
    ParameterMutationOccurrenceFamilyTestCase,
)
from tests.unit.src.fensu.analysis.helpers import build_test_analysis, definition_line


@pytest.mark.parametrize(
    "test_case",
    [
        ClassDeclarationFamilyTestCase(
            description="classes expose bases decorators top-level state and direct methods",
            source=(
                "@registry.decorator(flag=True)\n"
                "class Outer(pkg.Base[T], factory()):\n"
                "    @property\n"
                "    def first(self):\n"
                "        pass\n\n"
                "    class Inner(Outer):\n"
                "        @tools.wrap()\n"
                "        async def second(self):\n"
                "            pass\n"
            ),
            expected_names=("Outer", "Inner"),
            expected_base_names=(("Base",), ("Outer",)),
            expected_decorator_names=(("registry.decorator",), ()),
            expected_lines=(2, 7),
            expected_top_level=(True, False),
            expected_method_names=(("first",), ("second",)),
            expected_method_decorators=((("property",),), (("tools.wrap",),)),
            expected_method_lines=((4,), (9,)),
            expected_method_owner_names=(("Outer",), ("Inner",)),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_class_declarations_when_querying_public_facts_then_returns_direct_metadata(
    test_case: ClassDeclarationFamilyTestCase,
    tmp_path: Path,
) -> None:
    analysis: Analysis = build_test_analysis(path=tmp_path / "module.py", source=test_case.source)
    facts: tuple[ClassDeclarationFact, ...] = analysis.facts.class_declarations()
    method_names: list[tuple[str, ...]] = []
    method_decorators: list[tuple[tuple[str, ...], ...]] = []
    method_lines: list[tuple[int, ...]] = []
    method_owner_names: list[tuple[str, ...]] = []
    for fact in facts:
        method_names.append(tuple(method.name for method in fact.methods))
        method_decorators.append(tuple(method.decorator_names for method in fact.methods))
        method_lines.append(tuple(method.location.line for method in fact.methods))
        method_owner_names.append(tuple(method.owning_class.name for method in fact.methods))

    assert tuple(fact.name for fact in facts) == test_case.expected_names
    assert tuple(fact.base_names for fact in facts) == test_case.expected_base_names
    assert tuple(fact.decorator_names for fact in facts) == test_case.expected_decorator_names
    assert tuple(fact.location.line for fact in facts) == test_case.expected_lines
    assert tuple(fact.top_level for fact in facts) == test_case.expected_top_level
    assert tuple(method_names) == test_case.expected_method_names
    assert tuple(method_decorators) == test_case.expected_method_decorators
    assert tuple(method_lines) == test_case.expected_method_lines
    assert tuple(method_owner_names) == test_case.expected_method_owner_names


@pytest.mark.parametrize(
    "test_case",
    [
        AssignmentReferenceFamilyTestCase(
            description="assignments expose recursive stores strict references and nearest owners",
            source=(
                "root = package.module.value\n"
                "class Box:\n"
                "    def method(self):\n"
                "        left, (right, *rest) = source.item\n"
                "        obj.attr = package.other\n"
                "        annotated: Thing = registry[Thing]\n"
                "        nested = factory().result\n"
            ),
            expected_lines=(1, 4, 5, 6, 7),
            expected_class_names=(None, "Box", "Box", "Box", "Box"),
            expected_class_lines=(None, 2, 2, 2, 2),
            expected_function_names=(None, "method", "method", "method", "method"),
            expected_function_lines=(None, 3, 3, 3, 3),
            expected_target_names=(
                ("root",),
                ("left", "right", "rest"),
                (),
                ("annotated",),
                ("nested",),
            ),
            expected_references=(
                QualifiedReferenceFact(
                    kind="attribute",
                    name="package.module.value",
                    base_name="value",
                    receiver_base_name="module",
                    parts=("package", "module", "value"),
                ),
                QualifiedReferenceFact(
                    kind="attribute",
                    name="source.item",
                    base_name="item",
                    receiver_base_name="source",
                    parts=("source", "item"),
                ),
                QualifiedReferenceFact(
                    kind="attribute",
                    name="package.other",
                    base_name="other",
                    receiver_base_name="package",
                    parts=("package", "other"),
                ),
                None,
                None,
            ),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_assignments_when_querying_public_facts_then_returns_references_and_owners(
    test_case: AssignmentReferenceFamilyTestCase,
    tmp_path: Path,
) -> None:
    analysis: Analysis = build_test_analysis(path=tmp_path / "module.py", source=test_case.source)
    facts: tuple[AssignmentReferenceFact, ...] = analysis.facts.assignment_references()

    assert tuple(fact.location.line for fact in facts) == test_case.expected_lines
    assert tuple(getattr(fact.owning_class, "name", None) for fact in facts) == (
        test_case.expected_class_names
    )
    assert tuple(definition_line(fact.owning_class) for fact in facts) == (
        test_case.expected_class_lines
    )
    assert tuple(getattr(fact.owning_function, "name", None) for fact in facts) == (
        test_case.expected_function_names
    )
    assert tuple(definition_line(fact.owning_function) for fact in facts) == (
        test_case.expected_function_lines
    )
    assert tuple(fact.target_names for fact in facts) == test_case.expected_target_names
    assert tuple(fact.value_reference for fact in facts) == test_case.expected_references


@pytest.mark.parametrize(
    "test_case",
    [
        NamedCallFamilyTestCase(
            description="calls preserve BFS order nearest owners loops literals bare use and super targets",
            source=(
                "class Outer:\n"
                "    def run(self):\n"
                "        for item in rows:\n"
                "            def inner():\n"
                '                service.call("x", dynamic, b"y", 3, 1.5, 2j, True, None, ...)\n'
                "        super()\n"
                "        assigned = factory().result()\n"
            ),
            expected_lines=(6, 7, 5, 7),
            expected_names=("super", "result", "service.call", "factory"),
            expected_references=(
                QualifiedReferenceFact("name", "super", "super", None, ("super",)),
                QualifiedReferenceFact("attribute", "result", "result", None, ()),
                QualifiedReferenceFact(
                    "attribute", "service.call", "call", "service", ("service", "call")
                ),
                QualifiedReferenceFact("name", "factory", "factory", None, ("factory",)),
            ),
            expected_class_chains=(("Outer",), ("Outer",), ("Outer",), ("Outer",)),
            expected_class_chain_lines=((1,), (1,), (1,), (1,)),
            expected_function_chains=(("run",), ("run",), ("inner", "run"), ("run",)),
            expected_function_chain_lines=((2,), (2,), (4, 2), (2,)),
            expected_inside_loop=(False, False, True, False),
            expected_literal_arguments=(
                (),
                (),
                (
                    LiteralArgumentFact(0, "string", "x"),
                    LiteralArgumentFact(2, "bytes", b"y"),
                    LiteralArgumentFact(3, "integer", 3),
                    LiteralArgumentFact(4, "float", 1.5),
                    LiteralArgumentFact(5, "complex", 2j),
                    LiteralArgumentFact(6, "boolean", True),
                    LiteralArgumentFact(7, "none", None),
                    LiteralArgumentFact(8, "ellipsis", None),
                ),
                (),
            ),
            expected_bare_expression=(True, False, True, False),
            expected_super_call=(True, False, False, False),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_calls_when_querying_public_facts_then_returns_context_and_literal_metadata(
    test_case: NamedCallFamilyTestCase,
    tmp_path: Path,
) -> None:
    analysis: Analysis = build_test_analysis(path=tmp_path / "module.py", source=test_case.source)
    facts: tuple[NamedCallFact, ...] = analysis.facts.named_calls()
    class_chains: list[tuple[str, ...]] = []
    class_chain_lines: list[tuple[int, ...]] = []
    function_chains: list[tuple[str, ...]] = []
    function_chain_lines: list[tuple[int, ...]] = []
    for fact in facts:
        class_chains.append(tuple(owner.name for owner in fact.enclosing_classes))
        class_chain_lines.append(tuple(owner.location.line for owner in fact.enclosing_classes))
        function_chains.append(tuple(owner.name for owner in fact.enclosing_functions))
        function_chain_lines.append(
            tuple(owner.location.line for owner in fact.enclosing_functions)
        )

    assert tuple(fact.location.line for fact in facts) == test_case.expected_lines
    assert tuple(fact.name for fact in facts) == test_case.expected_names
    assert tuple(fact.reference for fact in facts) == test_case.expected_references
    assert tuple(class_chains) == test_case.expected_class_chains
    assert tuple(class_chain_lines) == test_case.expected_class_chain_lines
    assert tuple(function_chains) == test_case.expected_function_chains
    assert tuple(function_chain_lines) == test_case.expected_function_chain_lines
    assert tuple(fact.owning_class for fact in facts) == tuple(
        fact.enclosing_classes[0] for fact in facts
    )
    assert tuple(fact.owning_function for fact in facts) == tuple(
        fact.enclosing_functions[0] for fact in facts
    )
    assert tuple(fact.inside_loop for fact in facts) == test_case.expected_inside_loop
    assert tuple(fact.literal_arguments for fact in facts) == test_case.expected_literal_arguments
    assert tuple(fact.bare_expression for fact in facts) == test_case.expected_bare_expression
    assert tuple(fact.super_call for fact in facts) == test_case.expected_super_call


@pytest.mark.parametrize(
    "test_case",
    [
        LocalCallEdgeFamilyTestCase(
            description="one loop call emits nearest-first edges for every named function ancestor",
            source=(
                "class Worker:\n"
                "    def outer(self):\n"
                "        def inner():\n"
                "            while ready:\n"
                "                target.part()\n"
                "                (lambda: None)()\n"
            ),
            expected_lines=(5, 5, 6, 6),
            expected_caller_names=("inner", "outer", "inner", "outer"),
            expected_caller_lines=(3, 2, 3, 2),
            expected_class_names=("Worker", "Worker", "Worker", "Worker"),
            expected_class_lines=(1, 1, 1, 1),
            expected_callees=(
                QualifiedReferenceFact(
                    "attribute", "target.part", "part", "target", ("target", "part")
                ),
                QualifiedReferenceFact(
                    "attribute", "target.part", "part", "target", ("target", "part")
                ),
                QualifiedReferenceFact("other", None, None, None, ()),
                QualifiedReferenceFact("other", None, None, None, ()),
            ),
            expected_inside_loop=(True, True, True, True),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_nested_call_when_querying_edges_then_attributes_every_named_caller(
    test_case: LocalCallEdgeFamilyTestCase,
    tmp_path: Path,
) -> None:
    analysis: Analysis = build_test_analysis(path=tmp_path / "module.py", source=test_case.source)
    facts: tuple[LocalCallEdgeFact, ...] = analysis.facts.local_call_edges()

    assert tuple(fact.location.line for fact in facts) == test_case.expected_lines
    assert tuple(fact.caller.name for fact in facts) == test_case.expected_caller_names
    assert tuple(fact.caller.location.line for fact in facts) == test_case.expected_caller_lines
    assert tuple(getattr(fact.caller_class, "name", None) for fact in facts) == (
        test_case.expected_class_names
    )
    assert tuple(definition_line(fact.caller_class) for fact in facts) == (
        test_case.expected_class_lines
    )
    assert tuple(fact.callee for fact in facts) == test_case.expected_callees
    assert tuple(fact.inside_loop for fact in facts) == test_case.expected_inside_loop


@pytest.mark.parametrize(
    "test_case",
    [
        ComparisonFamilyTestCase(
            description="comparison operands preserve holes and subscript reference shape",
            source="if pkg.value == compute() < rows[index] != factory().attr:\n    pass\n",
            expected_lines=(1,),
            expected_operand_references=(
                (
                    QualifiedReferenceFact(
                        "attribute", "pkg.value", "value", "pkg", ("pkg", "value")
                    ),
                    None,
                    QualifiedReferenceFact("subscript", None, "rows", None, ("rows",)),
                    QualifiedReferenceFact("attribute", "attr", "attr", None, ()),
                ),
            ),
        ),
        ComparisonFamilyTestCase(
            description="comparison attributes preserve the immediate receiver base",
            source=(
                "if SqlReferenceKind[T].DBT_REF == kind:\n    pass\n"
                "if factory()[T].DBT_REF == kind:\n    pass\n"
                "if factory().SqlReferenceKind.DBT_REF == kind:\n    pass\n"
            ),
            expected_lines=(1, 3, 5),
            expected_operand_references=(
                (
                    QualifiedReferenceFact(
                        "attribute",
                        "DBT_REF",
                        "DBT_REF",
                        "SqlReferenceKind",
                        ("SqlReferenceKind", "DBT_REF"),
                    ),
                    QualifiedReferenceFact("name", "kind", "kind", None, ("kind",)),
                ),
                (
                    QualifiedReferenceFact("attribute", "DBT_REF", "DBT_REF", None, ()),
                    QualifiedReferenceFact("name", "kind", "kind", None, ("kind",)),
                ),
                (
                    QualifiedReferenceFact(
                        "attribute",
                        "SqlReferenceKind.DBT_REF",
                        "DBT_REF",
                        "SqlReferenceKind",
                        (),
                    ),
                    QualifiedReferenceFact("name", "kind", "kind", None, ("kind",)),
                ),
            ),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_comparison_when_querying_public_facts_then_aligns_direct_operand_references(
    test_case: ComparisonFamilyTestCase,
    tmp_path: Path,
) -> None:
    analysis: Analysis = build_test_analysis(path=tmp_path / "module.py", source=test_case.source)
    facts: tuple[ComparisonFact, ...] = analysis.facts.comparisons()

    assert tuple(fact.location.line for fact in facts) == test_case.expected_lines
    assert tuple(fact.operand_references for fact in facts) == (
        test_case.expected_operand_references
    )


@pytest.mark.parametrize(
    "test_case",
    [
        ParameterMutationOccurrenceFamilyTestCase(
            description="repeated setter mutations retain every occurrence without changing first-only facts",
            source=(
                "class Box:\n"
                "    @value.setter\n"
                "    def value(self, items):\n"
                "        items.append(1)\n"
                "        items.append(2)\n"
                "        return items\n"
            ),
            expected_function_names=("value", "value"),
            expected_parameter_names=("items", "items"),
            expected_parameter_kinds=("positional_or_keyword", "positional_or_keyword"),
            expected_lines=(4, 5),
            expected_returned=(True, True),
            expected_dunder=(False, False),
            expected_setter=(True, True),
            expected_first_only_count=1,
        ),
        ParameterMutationOccurrenceFamilyTestCase(
            description="nested repeated mutations belong to inner and outer named functions",
            source=(
                "def __outer__(values):\n"
                "    def inner(values):\n"
                "        values.append(1)\n"
                "        values.append(2)\n"
            ),
            expected_function_names=("__outer__", "__outer__", "inner", "inner"),
            expected_parameter_names=("values", "values", "values", "values"),
            expected_parameter_kinds=(
                "positional_or_keyword",
                "positional_or_keyword",
                "positional_or_keyword",
                "positional_or_keyword",
            ),
            expected_lines=(3, 4, 3, 4),
            expected_returned=(False, False, False, False),
            expected_dunder=(True, True, False, False),
            expected_setter=(False, False, False, False),
            expected_first_only_count=2,
        ),
        ParameterMutationOccurrenceFamilyTestCase(
            description="variadic mutations expose parameter kinds for policy filtering",
            source=("def update(*args, **kwargs):\n    args.append(1)\n    kwargs.update({})\n"),
            expected_function_names=("update", "update"),
            expected_parameter_names=("args", "kwargs"),
            expected_parameter_kinds=("vararg", "kwarg"),
            expected_lines=(2, 3),
            expected_returned=(False, False),
            expected_dunder=(False, False),
            expected_setter=(False, False),
            expected_first_only_count=2,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_parameter_mutations_when_querying_occurrences_then_preserves_complete_cardinality(
    test_case: ParameterMutationOccurrenceFamilyTestCase,
    tmp_path: Path,
) -> None:
    analysis: Analysis = build_test_analysis(path=tmp_path / "module.py", source=test_case.source)
    facts: tuple[ParameterMutationOccurrenceFact, ...] = (
        analysis.facts.parameter_mutation_occurrences()
    )
    first_only: tuple[ParameterMutationFact, ...] = analysis.facts.parameter_mutations()

    assert tuple(fact.function_name for fact in facts) == test_case.expected_function_names
    assert tuple(fact.parameter_name for fact in facts) == test_case.expected_parameter_names
    assert tuple(fact.parameter_kind for fact in facts) == test_case.expected_parameter_kinds
    assert tuple(fact.location.line for fact in facts) == test_case.expected_lines
    assert tuple(fact.returned for fact in facts) == test_case.expected_returned
    assert tuple(fact.dunder for fact in facts) == test_case.expected_dunder
    assert tuple(fact.setter for fact in facts) == test_case.expected_setter
    assert len(first_only) == test_case.expected_first_only_count
