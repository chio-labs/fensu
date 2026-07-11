"""Rule check functions for the tests family."""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path

from strata.analysis.core.models import ParametrizeFact, PytestFunctionFact, PytestModuleFacts
from strata.discovery.core.types import ScopeName
from strata.rules.authoring.models import Fault
from strata.rules.authoring.types import RuleContext
from strata.rules.tests.types import SftCode, TestPathName, TestScope, TestSymbol

_test_name_pattern: re.Pattern[str] = re.compile(r"^test_given_.+_when_.+_then_.+$")
_valid_test_scopes: frozenset[str] = frozenset(TestScope)
_minimum_test_layout_parts: int = 3
_minimum_src_layout_parts: int = 5
_minimum_scripts_layout_parts: int = 4
_minimum_parametrize_arguments: int = 2
_test_function_rule_codes: frozenset[SftCode] = frozenset(
    {
        SftCode.TEST_FUNCTION_NAME,
        SftCode.DATACLASS_PARAMETRIZE,
        SftCode.ACCEPTS_TEST_CASE,
        SftCode.TEST_CASE_ANNOTATION,
        SftCode.EXPECTED_FIELD_ASSERTION,
        SftCode.PARAMETRIZE_ARGUMENTS,
        SftCode.PARAMETRIZE_TEST_CASE,
        SftCode.PARAMETRIZE_IDS,
        SftCode.INLINE_PARAMETRIZE_VALUES,
        SftCode.INLINE_PARAMETRIZE_SEQUENCE,
        SftCode.NONEMPTY_PARAMETRIZE_VALUES,
        SftCode.NO_DICT_TEST_CASES,
        SftCode.LOCAL_TEST_CASE_CONSTRUCTORS,
        SftCode.DESCRIPTION_LAMBDA_IDS,
    }
)


@dataclass(frozen=True)
class _LocalTestTypes:
    module_name: str
    dataclass_names: frozenset[str]


@dataclass(frozen=True)
class _TestModuleContext:
    imported_local_test_case_types: frozenset[str]
    test_case_annotation_names: frozenset[str]


@dataclass(frozen=True)
class _LayoutIssue:
    code: SftCode
    message: str


def test_faults(*, module: ast.Module, ctx: RuleContext, code: SftCode) -> list[Fault]:
    """Collect faults for a single tests-family rule."""

    if ctx.scope() is not ScopeName.TEST:
        return []
    if code == SftCode.NO_IF_IN_TESTS:
        if not _is_test_module(ctx.path):
            return []
        faults: list[Fault] = []
        for fact in ctx._analysis.facts.test_functions():
            if fact.parametrize is not None:
                faults.extend(ctx.fault_at(location) for location in fact.conditional_locations)
        return faults
    if code == SftCode.NO_COMPLEX_COMPREHENSIONS:
        return [ctx.fault_at(location) for location in ctx._analysis.facts.complex_comprehensions()]
    if ctx.path.name == TestPathName.SCENARIO_MODELS and code == SftCode.TEST_LAYOUT:
        return _scenario_models_faults(module=module, ctx=ctx)
    if code in _layout_codes():
        return _layout_faults(ctx=ctx, code=code)
    if code == SftCode.INIT_MODULE_EMPTY:
        return _init_module_faults(module=module, ctx=ctx)
    if code == SftCode.ABSOLUTE_IMPORTS:
        return _relative_import_faults(module=module, ctx=ctx)
    if ctx.path.name == TestPathName.TEST_TYPES:
        return _test_types_faults(module=module, ctx=ctx, code=code)
    if code in {SftCode.TEST_TYPES_DESCRIPTION, SftCode.TEST_TYPES_EXPECTED_FIELD}:
        return []
    if ctx.path.name.endswith(".py"):
        return _test_file_faults(module=module, ctx=ctx, code=code)
    return []


def _layout_faults(*, ctx: RuleContext, code: SftCode) -> list[Fault]:
    if ctx.path.name in {TestPathName.INIT_MODULE, TestPathName.CONFTEST}:
        return []
    issue: _LayoutIssue | None = ctx._memoize(
        key="tests.layout_issue",
        operation=lambda: _layout_issue(ctx=ctx),
    )
    if issue is None:
        return []
    return _selected_path_faults(
        ctx=ctx,
        code=code,
        actual_code=issue.code,
        message=issue.message,
    )


def _layout_issue(*, ctx: RuleContext) -> _LayoutIssue | None:
    try:
        relative_parts: tuple[str, ...] = ctx.path.parent.relative_to(ctx.repo_root).parts
    except ValueError:
        return _LayoutIssue(code=SftCode.TEST_LAYOUT, message="test path is outside repo")
    if len(relative_parts) < _minimum_test_layout_parts or relative_parts[0] != TestPathName.TESTS:
        return _LayoutIssue(
            code=SftCode.TEST_LAYOUT,
            message="test directories must live under tests/<scope>/...",
        )
    scope: str = relative_parts[1]
    if scope not in _valid_test_scopes:
        return _LayoutIssue(
            code=SftCode.TEST_SCOPE,
            message="test scope must be unit, integration, or e2e",
        )
    mirrored_root: str = relative_parts[2]
    if mirrored_root == TestPathName.SRC:
        return _src_layout_issue(ctx=ctx, relative_parts=relative_parts)
    if mirrored_root == TestPathName.SCRIPTS:
        return _scripts_layout_issue(ctx=ctx, relative_parts=relative_parts)
    return _LayoutIssue(
        code=SftCode.TEST_MIRRORED_ROOT,
        message="test directories must mirror src or scripts",
    )


def _src_layout_issue(*, ctx: RuleContext, relative_parts: tuple[str, ...]) -> _LayoutIssue | None:
    if len(relative_parts) < _minimum_src_layout_parts:
        return _LayoutIssue(
            code=SftCode.SRC_MIRROR_DEPTH,
            message="src-backed tests must live under tests/<scope>/src/<package>/<area>/...",
        )
    package_path: Path = ctx.repo_root / "src" / relative_parts[3]
    if not ctx._project.is_dir(requester=ctx.path, path=package_path):
        return _LayoutIssue(
            code=SftCode.SRC_PACKAGE_EXISTS,
            message="tests under tests/<scope>/src must mirror a real package under src/",
        )
    if relative_parts[3] == TestPathName.STRATA and relative_parts[4] == TestPathName.ROOT_SURFACE:
        return None
    area_path: Path = package_path / relative_parts[4]
    if not ctx._project.exists(requester=ctx.path, path=area_path):
        return _LayoutIssue(
            code=SftCode.SRC_AREA_EXISTS,
            message="tests under tests/<scope>/src must mirror a real src package area",
        )
    return None


def _scripts_layout_issue(
    *, ctx: RuleContext, relative_parts: tuple[str, ...]
) -> _LayoutIssue | None:
    if len(relative_parts) < _minimum_scripts_layout_parts:
        return _LayoutIssue(
            code=SftCode.SCRIPTS_MIRROR_DEPTH,
            message="script-backed tests must live under tests/<scope>/scripts/<area>/...",
        )
    area_path: Path = ctx.repo_root / "scripts" / relative_parts[3]
    if not ctx._project.exists(requester=ctx.path, path=area_path):
        return _LayoutIssue(
            code=SftCode.SCRIPTS_AREA_EXISTS,
            message="tests under tests/<scope>/scripts must mirror a real scripts area",
        )
    return None


def _selected_path_faults(
    *, ctx: RuleContext, code: SftCode, actual_code: SftCode, message: str
) -> list[Fault]:
    if code != actual_code:
        return []
    return [_path_fault(ctx=ctx, code=actual_code, message=message)]


def _path_fault(*, ctx: RuleContext, code: SftCode, message: str) -> Fault:
    del code
    return ctx.path_fault(message=message)


def _init_module_faults(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    del module
    if (
        ctx.path.name != TestPathName.INIT_MODULE
        or ctx._analysis.facts.test_module().empty_or_docstring_only
    ):
        return []
    return [ctx.path_fault(message="__init__.py must be empty or docstring-only")]


def _relative_import_faults(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    del module
    return [
        ctx.fault_at(fact.location)
        for fact in ctx._analysis.facts.references().imports
        if fact.from_import and fact.relative_level > 0
    ]


def _test_types_faults(*, module: ast.Module, ctx: RuleContext, code: SftCode) -> list[Fault]:
    del module
    faults: list[Fault] = []
    for fact in ctx._analysis.facts.dataclasses():
        if (
            code == SftCode.TEST_TYPES_DESCRIPTION
            and TestSymbol.DESCRIPTION not in fact.field_names
        ):
            faults.append(ctx.fault_at(fact.location))
        if code == SftCode.TEST_TYPES_EXPECTED_FIELD and not any(
            field_name.startswith("expected_") for field_name in fact.field_names
        ):
            faults.append(ctx.fault_at(fact.location))
    return faults


def _scenario_models_faults(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    del module
    return [
        ctx.fault_at(location)
        for location in ctx._analysis.facts.test_module().scenario_invalid_locations
    ]


def _test_file_faults(*, module: ast.Module, ctx: RuleContext, code: SftCode) -> list[Fault]:
    del module
    local_test_types: _LocalTestTypes | None = None
    if code in {
        SftCode.LOCAL_TEST_TYPES_IMPORT,
        SftCode.TEST_CASE_ANNOTATION,
        SftCode.LOCAL_TEST_CASE_CONSTRUCTORS,
    } and _is_test_module(ctx.path):
        local_test_types = _local_test_types(
            ctx=ctx,
            inspect_dataclasses=code != SftCode.LOCAL_TEST_TYPES_IMPORT,
        )
    module_context: _TestModuleContext = _module_context(ctx=ctx, local_test_types=local_test_types)
    faults: list[Fault] = []
    if (
        code == SftCode.LOCAL_TEST_TYPES_FILE
        and _is_test_module(ctx.path)
        and not ctx._project.is_file(
            requester=ctx.path,
            path=ctx.path.parent / "_test_types.py",
        )
    ):
        faults.append(ctx.path_fault())
    if (
        code == SftCode.TEST_FILE_NAME
        and _is_test_module(ctx.path)
        and not ctx.path.name.startswith("test_")
    ):
        faults.append(ctx.path_fault())
    faults.extend(_module_shape_faults(ctx=ctx, code=code))
    faults.extend(_local_import_faults(ctx=ctx, code=code, local_test_types=local_test_types))
    if code in _test_function_rule_codes:
        for fact in ctx._analysis.facts.test_functions():
            faults.extend(
                _test_function_faults(
                    fact=fact,
                    ctx=ctx,
                    code=code,
                    module_context=module_context,
                )
            )
    return faults


def _module_shape_faults(*, ctx: RuleContext, code: SftCode) -> list[Fault]:
    if not _is_test_module(ctx.path):
        return []
    facts: PytestModuleFacts = ctx._analysis.facts.test_module()
    if code == SftCode.NO_TOP_LEVEL_HELPERS:
        return [ctx.fault_at(location) for location in facts.top_level_helper_locations]
    if code == SftCode.NO_MODULE_TEST_CASE_LISTS:
        return [ctx.fault_at(location) for location in facts.test_case_list_locations]
    if code == SftCode.PRIVATE_CONSTANT_ORDER:
        return [ctx.fault_at(location) for location in facts.private_after_test_locations]
    return []


def _local_import_faults(
    *,
    ctx: RuleContext,
    code: SftCode,
    local_test_types: _LocalTestTypes | None,
) -> list[Fault]:
    if code != SftCode.LOCAL_TEST_TYPES_IMPORT or local_test_types is None:
        return []
    faults: list[Fault] = []
    expected_module: str = local_test_types.module_name
    for fact in ctx._analysis.facts.references().imports:
        module_name: str = ".".join(fact.module_parts)
        if (
            fact.top_level
            and fact.from_import
            and module_name.endswith("._test_types")
            and module_name != expected_module
        ):
            faults.append(ctx.fault_at(fact.location))
    return faults


def _test_function_faults(
    *,
    fact: PytestFunctionFact,
    ctx: RuleContext,
    code: SftCode,
    module_context: _TestModuleContext,
) -> list[Fault]:
    faults: list[Fault] = []
    if code == SftCode.TEST_FUNCTION_NAME and not _test_name_pattern.match(fact.name):
        faults.append(ctx.fault_at(fact.location))
    parametrize: ParametrizeFact | None = fact.parametrize
    if parametrize is None:
        if code == SftCode.DATACLASS_PARAMETRIZE:
            faults.append(ctx.fault_at(fact.location))
        return faults
    test_case_present: bool = TestSymbol.TEST_CASE in fact.parameter_names
    if code == SftCode.ACCEPTS_TEST_CASE and not test_case_present:
        faults.append(ctx.fault_at(fact.location))
    if code == SftCode.TEST_CASE_ANNOTATION and (
        not test_case_present
        or fact.test_case_annotation_name not in module_context.test_case_annotation_names
    ):
        faults.append(ctx.fault_at(fact.location))
    faults.extend(
        _parametrize_faults(
            function=fact,
            ctx=ctx,
            code=code,
            decorator=parametrize,
            module_context=module_context,
        )
    )
    if code == SftCode.EXPECTED_FIELD_ASSERTION and not fact.references_expected_field:
        faults.append(ctx.fault_at(fact.location))
    return faults


def _parametrize_faults(
    *,
    function: PytestFunctionFact,
    ctx: RuleContext,
    code: SftCode,
    decorator: ParametrizeFact,
    module_context: _TestModuleContext,
) -> list[Fault]:
    if decorator.argument_count < _minimum_parametrize_arguments:
        return [ctx.fault_at(function.location)] if code == SftCode.PARAMETRIZE_ARGUMENTS else []
    faults: list[Fault] = []
    if code == SftCode.PARAMETRIZE_TEST_CASE and decorator.parameter_name != TestSymbol.TEST_CASE:
        faults.append(ctx.fault_at(function.location))
    if code == SftCode.PARAMETRIZE_IDS and not decorator.ids_present:
        faults.append(ctx.fault_at(function.location))
    if decorator.values_is_name:
        return faults + (
            [ctx.fault_at(function.location)] if code == SftCode.INLINE_PARAMETRIZE_VALUES else []
        )
    if decorator.values_is_list_comprehension:
        if code == SftCode.LOCAL_TEST_CASE_CONSTRUCTORS and not _is_local_constructor(
            constructor_name=decorator.cases[0].constructor_name, context=module_context
        ):
            faults.append(ctx.fault_at(decorator.cases[0].location))
        if code == SftCode.DESCRIPTION_LAMBDA_IDS and not decorator.description_lambda_ids:
            faults.append(ctx.fault_at(function.location))
        return faults
    if not decorator.values_is_sequence:
        return faults + (
            [ctx.fault_at(function.location)] if code == SftCode.INLINE_PARAMETRIZE_SEQUENCE else []
        )
    if code == SftCode.NONEMPTY_PARAMETRIZE_VALUES and decorator.values_empty:
        faults.append(ctx.fault_at(function.location))
    for case in decorator.cases:
        if code == SftCode.NO_DICT_TEST_CASES and case.dictionary:
            faults.append(ctx.fault_at(case.location))
        elif code == SftCode.LOCAL_TEST_CASE_CONSTRUCTORS and not _is_local_constructor(
            constructor_name=case.constructor_name, context=module_context
        ):
            faults.append(ctx.fault_at(case.location))
    if code == SftCode.DESCRIPTION_LAMBDA_IDS and not decorator.description_lambda_ids:
        faults.append(ctx.fault_at(function.location))
    return faults


def _local_test_types(*, ctx: RuleContext, inspect_dataclasses: bool) -> _LocalTestTypes:
    test_types_path: Path = ctx.path.parent / "_test_types.py"
    dataclass_names: frozenset[str] = frozenset()
    if inspect_dataclasses:
        dataclass_names = frozenset(
            fact.name
            for fact in ctx._project.dataclasses(
                requester=ctx.path,
                path=test_types_path,
            )
        )
    return _LocalTestTypes(
        module_name=_module_name_for_file(path=test_types_path, repo_root=ctx.repo_root),
        dataclass_names=dataclass_names,
    )


def _module_context(
    *, ctx: RuleContext, local_test_types: _LocalTestTypes | None
) -> _TestModuleContext:
    if local_test_types is None:
        return _TestModuleContext(
            imported_local_test_case_types=frozenset(),
            test_case_annotation_names=frozenset(),
        )
    imported: set[str] = set()
    for fact in ctx._analysis.facts.references().imports:
        if (
            fact.top_level
            and fact.from_import
            and ".".join(fact.module_parts) == local_test_types.module_name
        ):
            for alias in fact.aliases:
                if alias.imported_name in local_test_types.dataclass_names:
                    imported.add(alias.bound_name)
    return _TestModuleContext(
        imported_local_test_case_types=frozenset(imported),
        test_case_annotation_names=frozenset(imported),
    )


def _module_name_for_file(*, path: Path, repo_root: Path) -> str:
    return ".".join(path.relative_to(repo_root).with_suffix("").parts)


def _is_test_module(path: Path) -> bool:
    return path.name not in {
        TestPathName.TEST_HELPERS,
        TestPathName.TEST_TYPES,
        TestPathName.HELPERS,
        TestPathName.CONFTEST,
        TestPathName.INIT_MODULE,
    }


def _is_local_constructor(*, constructor_name: str | None, context: _TestModuleContext) -> bool:
    return constructor_name in context.imported_local_test_case_types


def _layout_codes() -> frozenset[SftCode]:
    return frozenset(
        {
            SftCode.TEST_LAYOUT,
            SftCode.TEST_SCOPE,
            SftCode.TEST_MIRRORED_ROOT,
            SftCode.SRC_MIRROR_DEPTH,
            SftCode.SRC_PACKAGE_EXISTS,
            SftCode.SRC_AREA_EXISTS,
            SftCode.SCRIPTS_MIRROR_DEPTH,
            SftCode.SCRIPTS_AREA_EXISTS,
        }
    )
