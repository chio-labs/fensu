"""Static extraction of public custom-rule harness use."""

from __future__ import annotations

import ast
from collections.abc import Mapping
from pathlib import Path

from strata.analysis._helpers.locations import source_location
from strata.analysis.models import (
    EvaluateRuleCallFact,
    ParametrizeDimensionFact,
    SourceLocation,
    StaticReferenceFact,
)
from strata.analysis.types import RuleCaseForm


class HarnessUseExtractor:
    """Resolve conservative per-file evaluate_rule and RuleCase syntax facts."""

    _evaluate_rule_reference: StaticReferenceFact = StaticReferenceFact(
        module_name="strata", symbol_name="evaluate_rule"
    )
    _rule_case_reference: StaticReferenceFact = StaticReferenceFact(
        module_name="strata", symbol_name="RuleCase"
    )
    _parametrize_name: tuple[str, ...] = ("pytest", "mark", "parametrize")
    _star_import_name: str = "*"
    _minimum_parametrize_arguments: int = 2

    def __init__(
        self,
        *,
        path: Path,
        module: ast.Module,
        node_index: Mapping[type[ast.AST], tuple[ast.AST, ...]],
        parent_by_node: Mapping[ast.AST, ast.AST],
    ) -> None:
        """Index module imports, bindings, and literal case sequences."""

        self._path: Path = path
        self._module: ast.Module = module
        self._node_index: Mapping[type[ast.AST], tuple[ast.AST, ...]] = node_index
        self._parent_by_node: Mapping[ast.AST, ast.AST] = parent_by_node
        self._from_bindings: dict[str, set[StaticReferenceFact]] = {}
        self._module_bindings: dict[str, set[str]] = {}
        self._module_shadowed: set[str] = set()
        self._literal_sequences: dict[str, list[ast.List | ast.Tuple]] = {}
        self._dimensions: (
            dict[ast.FunctionDef | ast.AsyncFunctionDef, tuple[ParametrizeDimensionFact, ...]]
            | None
        ) = None
        self._calls: tuple[EvaluateRuleCallFact, ...] | None = None
        self._index_module_bindings()

    def parametrize_dimensions(
        self,
    ) -> Mapping[ast.FunctionDef | ast.AsyncFunctionDef, tuple[ParametrizeDimensionFact, ...]]:
        """Return every pytest parametrization dimension by test function."""

        if self._dimensions is None:
            dimensions: dict[
                ast.FunctionDef | ast.AsyncFunctionDef, tuple[ParametrizeDimensionFact, ...]
            ] = {}
            for node in self._function_nodes():
                dimensions[node] = tuple(
                    self._dimension_fact(decorator=decorator)
                    for decorator in node.decorator_list
                    if isinstance(decorator, ast.Call)
                    and self._expression_parts(decorator.func) == self._parametrize_name
                )
            self._dimensions = dimensions
        return self._dimensions

    def evaluate_rule_calls(self) -> tuple[EvaluateRuleCallFact, ...]:
        """Return every unshadowed call to the top-level Strata harness."""

        if self._calls is None:
            calls: list[EvaluateRuleCallFact] = []
            for node in self._node_index.get(ast.Call, ()):
                if not isinstance(node, ast.Call):
                    continue
                owner: ast.FunctionDef | ast.AsyncFunctionDef | None = self._test_owner(node)
                shadowed: frozenset[str] = (
                    frozenset() if owner is None else self._function_shadowed_names(owner)
                )
                if self._resolve_expression(expression=node.func, shadowed=shadowed) != (
                    self._evaluate_rule_reference
                ):
                    continue
                calls.append(self._call_fact(call=node, owner=owner, shadowed=shadowed))
            self._calls = tuple(calls)
        return self._calls

    def _index_module_bindings(self) -> None:
        for statement in self._module.body:
            if isinstance(statement, ast.ImportFrom):
                self._index_from_import(statement)
                continue
            if isinstance(statement, ast.Import):
                self._index_import(statement)
                continue
            names: tuple[str, ...] = self._statement_bound_names(statement)
            self._module_shadowed.update(names)
            sequence: ast.List | ast.Tuple | None = self._literal_sequence(statement)
            if sequence is not None:
                for name in names:
                    self._literal_sequences.setdefault(name, []).append(sequence)

    def _index_from_import(self, statement: ast.ImportFrom) -> None:
        if statement.level or statement.module is None:
            return
        for alias in statement.names:
            if alias.name == self._star_import_name:
                continue
            bound_name: str = alias.asname or alias.name
            self._from_bindings.setdefault(bound_name, set()).add(
                StaticReferenceFact(module_name=statement.module, symbol_name=alias.name)
            )

    def _index_import(self, statement: ast.Import) -> None:
        for alias in statement.names:
            if alias.asname is not None:
                bound_name: str = alias.asname
                module_name: str = alias.name
            else:
                bound_name = alias.name.partition(".")[0]
                module_name = bound_name
            self._module_bindings.setdefault(bound_name, set()).add(module_name)

    def _function_nodes(self) -> tuple[ast.FunctionDef | ast.AsyncFunctionDef, ...]:
        nodes: tuple[ast.AST, ...] = (
            *self._node_index.get(ast.FunctionDef, ()),
            *self._node_index.get(ast.AsyncFunctionDef, ()),
        )
        return tuple(
            node
            for node in nodes
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
            and node.name.startswith("test_")
        )

    def _dimension_fact(self, *, decorator: ast.Call) -> ParametrizeDimensionFact:
        parameter_names: tuple[str, ...] = ()
        values: ast.expr | None = None
        if decorator.args:
            parameter_names = self._parameter_names(decorator.args[0])
        if len(decorator.args) >= self._minimum_parametrize_arguments:
            values = decorator.args[1]
        sequence: ast.List | ast.Tuple | None = self._resolved_sequence(
            expression=values,
            before_line=decorator.lineno,
        )
        case_locations: tuple[SourceLocation, ...] = ()
        unknown: bool = values is not None and sequence is None
        if sequence is not None:
            literal_cases: list[SourceLocation] = []
            for element in sequence.elts:
                if not self._is_rule_case_call(expression=element, shadowed=frozenset()):
                    unknown = True
                    literal_cases = []
                    break
                literal_cases.append(source_location(path=self._path, node=element))
            case_locations = tuple(literal_cases)
        return ParametrizeDimensionFact(
            location=source_location(path=self._path, node=decorator),
            parameter_names=parameter_names,
            values_location=(
                source_location(path=self._path, node=values) if values is not None else None
            ),
            rule_case_locations=case_locations,
            unknown_rule_case_count=unknown,
        )

    def _call_fact(
        self,
        *,
        call: ast.Call,
        owner: ast.FunctionDef | ast.AsyncFunctionDef | None,
        shadowed: frozenset[str],
    ) -> EvaluateRuleCallFact:
        rule_expression: ast.expr | None = self._keyword_value(call=call, name="rule")
        test_case_expression: ast.expr | None = self._keyword_value(call=call, name="test_case")
        form, case_locations, unknown = self._test_case_fact(
            expression=test_case_expression,
            owner=owner,
            shadowed=shadowed,
        )
        return EvaluateRuleCallFact(
            location=source_location(path=self._path, node=call),
            test_function_name=owner.name if owner is not None else None,
            test_function_location=(
                source_location(path=self._path, node=owner) if owner is not None else None
            ),
            rule_expression=self._expression_parts(rule_expression),
            rule_location=(
                source_location(path=self._path, node=rule_expression)
                if rule_expression is not None
                else None
            ),
            rule_reference=(
                self._resolve_expression(expression=rule_expression, shadowed=shadowed)
                if rule_expression is not None
                else None
            ),
            test_case_expression=self._expression_parts(test_case_expression),
            test_case_location=(
                source_location(path=self._path, node=test_case_expression)
                if test_case_expression is not None
                else None
            ),
            test_case_form=form,
            case_locations=case_locations,
            unknown_case_count=unknown,
        )

    def _test_case_fact(
        self,
        *,
        expression: ast.expr | None,
        owner: ast.FunctionDef | ast.AsyncFunctionDef | None,
        shadowed: frozenset[str],
    ) -> tuple[RuleCaseForm, tuple[SourceLocation, ...], bool]:
        if expression is None:
            return RuleCaseForm.MISSING, (), True
        if self._is_rule_case_call(expression=expression, shadowed=shadowed):
            return RuleCaseForm.LITERAL, (source_location(path=self._path, node=expression),), False
        if not isinstance(expression, ast.Name):
            return RuleCaseForm.DYNAMIC, (), True
        if owner is None or expression.id not in self._parameter_names_from_function(owner):
            form: RuleCaseForm = (
                RuleCaseForm.LOCAL if expression.id in shadowed else RuleCaseForm.DYNAMIC
            )
            return form, (), True
        matching_dimensions: tuple[ParametrizeDimensionFact, ...] = tuple(
            dimension
            for dimension in self.parametrize_dimensions().get(owner, ())
            if dimension.parameter_names == (expression.id,)
        )
        if len(matching_dimensions) != 1:
            return RuleCaseForm.PARAMETER, (), True
        dimension: ParametrizeDimensionFact = matching_dimensions[0]
        return (
            RuleCaseForm.PARAMETER,
            dimension.rule_case_locations,
            dimension.unknown_rule_case_count,
        )

    def _resolve_expression(
        self, *, expression: ast.expr, shadowed: frozenset[str]
    ) -> StaticReferenceFact | None:
        parts: tuple[str, ...] | None = self._expression_parts(expression)
        if not parts or parts[0] in shadowed or parts[0] in self._module_shadowed:
            return None
        if len(parts) == 1:
            references: set[StaticReferenceFact] = self._from_bindings.get(parts[0], set())
            return next(iter(references)) if len(references) == 1 else None
        modules: set[str] = self._module_bindings.get(parts[0], set())
        if len(modules) != 1:
            return None
        module_name: str = next(iter(modules))
        return StaticReferenceFact(
            module_name=".".join((module_name, *parts[1:-1])),
            symbol_name=parts[-1],
        )

    def _is_rule_case_call(self, *, expression: ast.expr, shadowed: frozenset[str]) -> bool:
        return (
            isinstance(expression, ast.Call)
            and self._resolve_expression(expression=expression.func, shadowed=shadowed)
            == self._rule_case_reference
        )

    def _resolved_sequence(
        self, *, expression: ast.expr | None, before_line: int
    ) -> ast.List | ast.Tuple | None:
        if isinstance(expression, ast.List | ast.Tuple):
            return expression
        if not isinstance(expression, ast.Name) or expression.id in self._from_bindings:
            return None
        candidates: list[ast.List | ast.Tuple] = self._literal_sequences.get(expression.id, [])
        if len(candidates) != 1 or candidates[0].lineno >= before_line:
            return None
        return candidates[0]

    def _test_owner(self, node: ast.AST) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
        current: ast.AST | None = self._parent_by_node.get(node)
        while current is not None:
            if isinstance(current, ast.Lambda | ast.ClassDef):
                return None
            if isinstance(current, ast.FunctionDef | ast.AsyncFunctionDef):
                return current if current.name.startswith("test_") else None
            current = self._parent_by_node.get(current)
        return None

    def _function_shadowed_names(
        self, function: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> frozenset[str]:
        names: set[str] = set(self._parameter_names_from_function(function))
        for node in ast.walk(function):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                names.add(node.id)
            elif isinstance(node, ast.Import | ast.ImportFrom):
                names.update(alias.asname or alias.name.partition(".")[0] for alias in node.names)
            elif node is not function and isinstance(
                node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef
            ):
                names.add(node.name)
        return frozenset(names)

    @staticmethod
    def _parameter_names_from_function(
        function: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> tuple[str, ...]:
        arguments: ast.arguments = function.args
        names: list[str] = [
            argument.arg
            for argument in (*arguments.posonlyargs, *arguments.args, *arguments.kwonlyargs)
        ]
        if arguments.vararg is not None:
            names.append(arguments.vararg.arg)
        if arguments.kwarg is not None:
            names.append(arguments.kwarg.arg)
        return tuple(names)

    @staticmethod
    def _parameter_names(expression: ast.expr) -> tuple[str, ...]:
        if not isinstance(expression, ast.Constant) or not isinstance(expression.value, str):
            return ()
        return tuple(name.strip() for name in expression.value.split(",") if name.strip())

    @staticmethod
    def _expression_parts(expression: ast.expr | None) -> tuple[str, ...] | None:
        if isinstance(expression, ast.Name):
            return (expression.id,)
        if isinstance(expression, ast.Attribute):
            parent: tuple[str, ...] | None = HarnessUseExtractor._expression_parts(expression.value)
            return (*parent, expression.attr) if parent else None
        return None

    @staticmethod
    def _keyword_value(*, call: ast.Call, name: str) -> ast.expr | None:
        values: tuple[ast.expr, ...] = tuple(
            keyword.value for keyword in call.keywords if keyword.arg == name
        )
        return values[0] if len(values) == 1 else None

    @staticmethod
    def _statement_bound_names(statement: ast.stmt) -> tuple[str, ...]:
        if isinstance(statement, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            return (statement.name,)
        if isinstance(statement, ast.Assign):
            return tuple(target.id for target in statement.targets if isinstance(target, ast.Name))
        if isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name):
            return (statement.target.id,)
        return ()

    @staticmethod
    def _literal_sequence(statement: ast.stmt) -> ast.List | ast.Tuple | None:
        value: ast.expr | None = None
        if isinstance(statement, ast.Assign):
            value = statement.value
        elif isinstance(statement, ast.AnnAssign):
            value = statement.value
        return value if isinstance(value, ast.List | ast.Tuple) else None
