"""AST visitor for annotation convention checks."""

from __future__ import annotations

import ast

from strata.rules.annotations.types import AnnotationCode
from strata.rules.authoring.models import Fault
from strata.rules.authoring.types import RuleContext


class AnnotationVisitor(ast.NodeVisitor):
    """Collect annotation faults for one active annotation rule code."""

    def __init__(self, *, ctx: RuleContext, code: AnnotationCode) -> None:
        self._ctx: RuleContext = ctx
        self._code: AnnotationCode = code
        self._faults: list[Fault] = []
        self._class_depth: int = 0
        self._function_scopes: list[set[str]] = []

    def collect(self, module: ast.Module) -> list[Fault]:
        """Visit a module and return collected faults."""

        self.visit(module)
        return self._faults

    def visit_Module(self, node: ast.Module) -> None:
        for statement in node.body:
            if isinstance(statement, (ast.Assign, ast.AugAssign)):
                self._check_module_assignment(statement)
                continue
            if isinstance(statement, ast.AnnAssign):
                self._record_annotated_assignment(statement.target)
                continue
            self.visit(statement)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._class_depth += 1
        is_enum_class: bool = _is_enum_class(node)
        try:
            for statement in node.body:
                if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    self.visit(statement)
                    continue
                if isinstance(statement, (ast.Assign, ast.AugAssign)):
                    if is_enum_class:
                        self.generic_visit(statement)
                        continue
                    self._check_class_assignment(statement)
                    continue
                if isinstance(statement, ast.AnnAssign):
                    if is_enum_class:
                        self.generic_visit(statement)
                        continue
                    self._record_annotated_assignment(statement.target)
                    continue
                self.visit(statement)
        finally:
            self._class_depth -= 1

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        if self._function_scopes:
            self._check_local_assignment(node)
            return
        self.generic_visit(node)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        if self._function_scopes:
            self._check_local_assignment(node)
            return
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if self._function_scopes:
            self._record_annotated_assignment(node.target)
            if node.value is not None:
                self.visit(node.value)
            return
        self.generic_visit(node)

    def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        self._check_function_signature(node)
        annotated_names: set[str] = self._annotated_parameter_names(node)
        self._function_scopes.append(annotated_names)
        try:
            for statement in node.body:
                self.visit(statement)
        finally:
            self._function_scopes.pop()

    def _check_function_signature(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        positional_args: list[ast.arg] = [*node.args.posonlyargs, *node.args.args]
        exempt_parameter_name: str | None = None
        if self._class_depth > 0 and positional_args and positional_args[0].arg in {"self", "cls"}:
            exempt_parameter_name = positional_args[0].arg
        for parameter in [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]:
            if parameter.annotation is not None or parameter.arg == exempt_parameter_name:
                continue
            self._append_fault(
                code=AnnotationCode.PARAMETER_ANNOTATION,
                node=parameter,
                message=f"function parameter '{parameter.arg}' must define a type annotation",
            )
        for parameter in [node.args.vararg, node.args.kwarg]:
            if parameter is None or parameter.annotation is not None:
                continue
            self._append_fault(
                code=AnnotationCode.PARAMETER_ANNOTATION,
                node=parameter,
                message=f"function parameter '{parameter.arg}' must define a type annotation",
            )
        if node.returns is None:
            self._append_fault(
                code=AnnotationCode.RETURN_ANNOTATION,
                node=node,
                message=f"function '{node.name}' must define a return type annotation",
            )

    def _annotated_parameter_names(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
        names: set[str] = set()
        for parameter in [
            *node.args.posonlyargs,
            *node.args.args,
            *node.args.kwonlyargs,
            node.args.vararg,
            node.args.kwarg,
        ]:
            if parameter is None:
                continue
            if parameter.annotation is not None or parameter.arg in {"self", "cls"}:
                names.add(parameter.arg)
        return names

    def _check_module_assignment(self, node: ast.Assign | ast.AugAssign) -> None:
        for target in _iter_simple_name_targets(node):
            if _is_exempt_module_name(target.id):
                continue
            self._append_fault(
                code=AnnotationCode.MODULE_VARIABLE_ANNOTATION,
                node=target,
                message=f"module-level variable '{target.id}' must define a type annotation",
            )
        self.generic_visit(node)

    def _check_class_assignment(self, node: ast.Assign | ast.AugAssign) -> None:
        for target in _iter_simple_name_targets(node):
            if _is_exempt_class_name(target.id):
                continue
            self._append_fault(
                code=AnnotationCode.CLASS_ATTRIBUTE_ANNOTATION,
                node=target,
                message=f"class attribute '{target.id}' must define a type annotation",
            )
        self.generic_visit(node)

    def _check_local_assignment(self, node: ast.Assign | ast.AugAssign) -> None:
        current_scope: set[str] = self._function_scopes[-1]
        for target in _iter_simple_name_targets(node):
            if target.id == "_" or target.id in current_scope:
                continue
            self._append_fault(
                code=AnnotationCode.LOCAL_VARIABLE_ANNOTATION,
                node=target,
                message=(
                    f"local variable '{target.id}' must define a type annotation on first binding"
                ),
            )
            current_scope.add(target.id)
        self.generic_visit(node)

    def _record_annotated_assignment(self, target: ast.expr) -> None:
        if self._function_scopes and isinstance(target, ast.Name):
            self._function_scopes[-1].add(target.id)

    def _append_fault(self, *, code: AnnotationCode, node: ast.AST, message: str) -> None:
        if code == self._code:
            self._faults.append(self._ctx.fault(node, message=message))


def _iter_simple_name_targets(node: ast.Assign | ast.AugAssign) -> list[ast.Name]:
    targets: list[ast.expr] = node.targets if isinstance(node, ast.Assign) else [node.target]
    return [target for target in targets if isinstance(target, ast.Name)]


def _is_exempt_module_name(name: str) -> bool:
    return name in {"__all__", "__match_args__", "__slots__", "__version__"}


def _is_exempt_class_name(name: str) -> bool:
    return name in {"__match_args__", "__slots__", "__test__"}


def _is_enum_class(node: ast.ClassDef) -> bool:
    for base in node.bases:
        if isinstance(base, ast.Name) and base.id in {"Enum", "StrEnum"}:
            return True
        if isinstance(base, ast.Attribute) and base.attr in {"Enum", "StrEnum"}:
            return True
    return False
