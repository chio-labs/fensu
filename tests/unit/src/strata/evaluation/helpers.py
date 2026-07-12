"""Helpers and fake rules for evaluation tests."""

from __future__ import annotations

import ast
from pathlib import Path
from types import MappingProxyType

from strata.analysis.models import SourceRange, SyntaxHandle
from strata.analysis.types import Analysis
from strata.config.models import Config, RuleExceptionEntry
from strata.discovery.main.discover_files import discover_files
from strata.discovery.models import (
    DiscoveredTree,
    ProjectLayout,
    ProjectPath,
    ProjectSource,
    ScopedFile,
)
from strata.evaluation.models import ParsedModule
from strata.evaluation.types import EvaluationProjectAnalysis
from strata.rules.authoring.models import Fault, RuleSpec
from strata.rules.authoring.types import Family, RuleContext, RuleKind, Threshold


def write_sources(*, repo_root: Path, files: tuple[tuple[str, str], ...]) -> None:
    """Write source files under a temp repo."""

    for relative_path, source in files:
        path: Path = repo_root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding="utf-8")


def direct_ast_parse_paths(*, root: Path) -> tuple[str, ...]:
    """Return Python modules containing direct ast.parse calls."""

    return tuple(
        str(candidate.relative_to(root))
        for candidate in root.rglob("*.py")
        if "ast.parse" in candidate.read_text(encoding="utf-8")
    )


def write_exception_target(*, repo_root: Path, path: str, create_path: bool) -> None:
    """Write a target function only when an exception-target test requests it."""

    if create_path:
        write_sources(
            repo_root=repo_root,
            files=((path, "def run() -> None:\n    pass\n"),),
        )


def discover_test_tree(*, config: Config) -> DiscoveredTree:
    """Discover files for an evaluation test config."""

    return discover_files(config=config)


def make_project_layout(
    *,
    repo_root: Path,
    runtime_roots: tuple[str, ...] = ("src/pkg",),
    test_roots: tuple[str, ...] = (),
    tooling_roots: tuple[str, ...] = (),
) -> ProjectLayout:
    """Build resolved project layout facts for direct evaluation tests."""

    return ProjectLayout(
        runtime_sources=tuple(
            _project_source(repo_root=repo_root, relative_path=value) for value in runtime_roots
        ),
        test_roots=tuple(
            ProjectPath(
                path=(repo_root / value).resolve(),
                relative_parts=Path(value).parts,
            )
            for value in test_roots
        ),
        tooling_sources=tuple(
            _project_source(repo_root=repo_root, relative_path=value) for value in tooling_roots
        ),
    )


def _project_source(*, repo_root: Path, relative_path: str) -> ProjectSource:
    path: Path = (repo_root / relative_path).resolve()
    return ProjectSource(
        path=path,
        relative_parts=Path(relative_path).parts,
        import_root=path.parent,
        package_name=path.name,
    )


def exercise_project_parse_order(
    *,
    project: EvaluationProjectAnalysis,
    scoped_file: ScopedFile,
    query_first: bool,
) -> tuple[Analysis | None, ParsedModule]:
    """Run tolerant and strict project access in the selected order."""

    if query_first:
        analysis: Analysis | None = project.analysis(
            requester=scoped_file.path,
            path=scoped_file.path,
        )
        return analysis, project.parsed_module(scoped_file)
    parsed: ParsedModule = project.parsed_module(scoped_file)
    return (
        project.analysis(requester=scoped_file.path, path=scoped_file.path),
        parsed,
    )


def direct_module_walk_paths(*, root: Path) -> tuple[str, ...]:
    """Return rule files that directly call ast.walk(module)."""

    paths: list[str] = []
    for path in sorted(root.rglob("*.py")):
        module: ast.Module = ast.parse(path.read_text(encoding="utf-8"))
        has_direct_module_walk: bool = any(
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "ast"
            and node.func.attr == "walk"
            and len(node.args) == 1
            and isinstance(node.args[0], ast.Name)
            and node.args[0].id == "module"
            for node in ast.walk(module)
        )
        if has_direct_module_walk:
            paths.append(str(path))
    return tuple(paths)


def make_config_with_entry_threshold(*, roots: tuple[str, ...] = ("src/pkg",)) -> Config:
    """Build config with a role override for entry-module threshold tests."""

    return Config(
        roots=roots,
        role_thresholds=MappingProxyType(
            {"main": MappingProxyType({Threshold.MAX_STATEMENTS: 30})}
        ),
    )


def make_rule_exception_config(*, path: str, symbols: tuple[str, ...], reason: str) -> Config:
    """Build config selecting SFS120 with one grouped rule exception."""

    return Config(
        roots=("src/pkg",),
        tests=(),
        select=("SFS120",),
        rule_exceptions=(
            RuleExceptionEntry(
                rule="SFS120",
                path=path,
                symbols=symbols,
                reason=reason,
            ),
        ),
    )


def make_node_count_rule() -> RuleSpec:
    """Build a fake rule that reports all call nodes via ctx.nodes."""

    def check(module: ast.Module, ctx: RuleContext) -> list[Fault]:
        return [ctx.fault(node=node, message="call found") for node in ctx.nodes(ast.Call)]

    return RuleSpec(
        code="XEV001", family=Family.CUSTOM, slug="node-count", message="call found", check=check
    )


def make_runtime_fault_rule() -> RuleSpec:
    """Build a fake runtime-only rule that reports the first module node."""

    def check(module: ast.Module, ctx: RuleContext) -> list[Fault]:
        return [ctx.fault(node=module.body[0])]

    return RuleSpec(
        code="SFH999",
        family=Family.HYGIENE,
        slug="runtime-fault",
        message="runtime fault",
        check=check,
    )


def make_threshold_rule(*, threshold: Threshold) -> RuleSpec:
    """Build a fake rule that reports the threshold value in its message."""

    def check(module: ast.Module, ctx: RuleContext) -> list[Fault]:
        node: ast.AST = module.body[0]
        return [ctx.fault(node=node, message=str(ctx.threshold(name=threshold)))]

    return RuleSpec(
        code="XTH001", family=Family.CUSTOM, slug="threshold", message="threshold", check=check
    )


def make_position_rule() -> RuleSpec:
    """Build a fake rule that reports position facts in its message."""

    def check(module: ast.Module, ctx: RuleContext) -> list[Fault]:
        node: ast.AST = module.body[0]
        message: str = f"{ctx.domain()}:{ctx.subdomain()}:{ctx.role_of()}:{ctx.is_main_module()}"
        return [ctx.fault(node=node, message=message)]

    return RuleSpec(
        code="XPO001", family=Family.CUSTOM, slug="position", message="position", check=check
    )


def make_loop_rule() -> RuleSpec:
    """Build a fake rule that reports calls inside loops."""

    def check(module: ast.Module, ctx: RuleContext) -> list[Fault]:
        faults: list[Fault] = []
        for node in ctx.nodes(ast.Call):
            if isinstance(node, ast.Call) and ctx.inside_loop(node):
                faults.append(ctx.fault(node=node, message=ctx.call_name(node) or "call"))
        return faults

    return RuleSpec(code="XLP001", family=Family.CUSTOM, slug="loop", message="loop", check=check)


def make_static_fault_rule(
    *, code: str, line: int, message: str, family: Family = Family.CUSTOM
) -> RuleSpec:
    """Build a fake rule that returns a static line-positioned fault."""

    def check(module: ast.Module, ctx: RuleContext) -> list[Fault]:
        return [Fault(code=code, path=ctx.path, message=message, line=line, column=0)]

    return RuleSpec(
        code=code,
        family=family,
        slug=message,
        message=message,
        check=check,
        kind=RuleKind.CUSTOM if code.startswith("X") else RuleKind.CORE,
    )


def make_none_location_rule() -> RuleSpec:
    """Build a fake rule returning a fault with no line/column."""

    def check(module: ast.Module, ctx: RuleContext) -> list[Fault]:
        return [Fault(code="XNO001", path=ctx.path, message="none location")]

    return RuleSpec(
        code="XNO001", family=Family.CUSTOM, slug="none-location", message="none", check=check
    )


def make_context_property_rule() -> RuleSpec:
    """Build a fake rule reporting source/path/root/relative context facts."""

    def check(module: ast.Module, ctx: RuleContext) -> list[Fault]:
        node: ast.AST = module.body[0]
        message: str = (
            f"{ctx.path.name}|{ctx.repo_root.name}|{len(ctx.source)}|"
            f"{'/'.join(ctx.relative_parts())}"
        )
        return [ctx.fault(node=node, message=message)]

    return RuleSpec(
        code="XCP001", family=Family.CUSTOM, slug="ctx-props", message="ctx", check=check
    )


def make_fault_factory_rule() -> RuleSpec:
    """Build a fake rule exercising default and override fault factory fields."""

    def check(module: ast.Module, ctx: RuleContext) -> list[Fault]:
        node: ast.AST = module.body[0]
        return [
            ctx.fault(node=node),
            ctx.fault(node=node, message="custom message", remediation="custom remediation"),
        ]

    return RuleSpec(
        code="XFF001",
        family=Family.CUSTOM,
        slug="fault-factory",
        message="rule message",
        remediation="rule remediation",
        check=check,
    )


def make_context_ast_helper_rule() -> RuleSpec:
    """Build a fake rule exercising ctx AST helper methods."""

    def check(module: ast.Module, ctx: RuleContext) -> list[Fault]:
        fn: ast.AST = ctx.top_level_functions(module)[0]
        call_nodes: list[ast.Call] = [
            node for node in ctx.nodes(ast.Call) if isinstance(node, ast.Call)
        ]
        call: ast.Call = call_nodes[0]
        message: str = (
            f"{ctx.base_name(call.func) or ''}|{len(ctx.non_docstring_body(module))}|"
            f"{len(ctx.nodes(ast.If))}|{','.join(sorted(ctx.parameter_names(fn)))}"
        )
        return [ctx.fault(node=fn, message=message)]

    return RuleSpec(
        code="XAH001", family=Family.CUSTOM, slug="ast-helpers", message="ast", check=check
    )


def make_analysis_context_rule() -> RuleSpec:
    """Build a fake rule that reports through the private analysis facade."""

    def check(module: ast.Module, ctx: RuleContext) -> list[Fault]:
        handle: SyntaxHandle = ctx._analysis.syntax.handles(kind="Call")[0]
        source_range: SourceRange = ctx._analysis.syntax.range(handle)
        message: str = ctx._analysis.text.slice(source_range)
        return [ctx.fault_at(location=handle, message=message)]

    return RuleSpec(
        code="XAN001", family=Family.CUSTOM, slug="analysis", message="analysis", check=check
    )


def make_project_dependency_rule() -> RuleSpec:
    """Build a fake rule that observes one missing project file."""

    def check(module: ast.Module, ctx: RuleContext) -> list[Fault]:
        del module
        ctx._project.is_file(
            requester=ctx.path,
            path=ctx.repo_root / "missing.py",
        )
        return []

    return RuleSpec(
        code="XPD001",
        family=Family.CUSTOM,
        slug="project-dependency",
        message="project dependency",
        check=check,
    )
