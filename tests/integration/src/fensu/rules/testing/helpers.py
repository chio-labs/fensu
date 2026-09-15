"""Custom rule declarations exercised by the public harness integration tests."""

from __future__ import annotations

import ast
from collections.abc import Callable
from pathlib import Path

from fensu import (
    Family,
    Fault,
    File,
    FilePosition,
    FunctionFacts,
    Project,
    ProjectFunctionFact,
    ProjectPath,
    RuleContext,
    RuleOption,
    SourceKind,
    SyntaxHandle,
    Threshold,
    rule,
)

_REPORT_FINDING_OPTION: RuleOption[bool] = RuleOption.boolean(
    name="report_finding",
    default=False,
)
_LABELS_OPTION: RuleOption[tuple[str, ...]] = RuleOption.string_list(
    name="labels",
    default=("default",),
)
_REQUIRED_COUNT_OPTION: RuleOption[int] = RuleOption.integer(
    name="required_count",
    required=True,
    minimum=0,
)
_OWNER_ONLY_OPTION: RuleOption[bool] = RuleOption.boolean(
    name="owner_only",
    default=True,
)
_LOCAL_OPTION: RuleOption[bool] = RuleOption.boolean(
    name="local_option",
    default=True,
)


def _assert_check_position(position: FilePosition) -> None:
    assert position.scope_root == ProjectPath("src/example")
    assert position.module == "example.orders.fulfillment.main.internal.check"
    assert position.package == "example.orders.fulfillment.main.internal"
    assert position.domain_parts == ("orders", "fulfillment")
    assert position.role == "main"
    assert position.role_depth == 1
    assert position.is_entry_module
    assert position.is_main_module


def _assert_models_position(position: FilePosition) -> None:
    assert position.role == "models"
    assert position.role_depth == 0


def _assert_other_position(position: FilePosition) -> None:
    del position


_POSITION_ASSERTIONS: dict[str, Callable[[FilePosition], None]] = {
    "check.py": _assert_check_position,
    "models.py": _assert_models_position,
}


@rule(
    code="XTS001",
    family=Family.CUSTOM,
    slug="typed-file-subject",
    message="typed file",
)
def typed_file_subject(*, subject: File, context: RuleContext) -> list[Fault]:
    """Report complete stable position facts supplied for each file identity."""

    position: FilePosition | None = context.project.tree.position(subject.path)
    assert position is not None
    assert position.path == subject.path
    assert position.analyzer.value == "python"
    assert position.source_kind is SourceKind.PYTHON_MODULE
    assertion: Callable[[FilePosition], None] = _POSITION_ASSERTIONS.get(
        subject.path.name, _assert_other_position
    )
    assertion(position)
    return [context.path_fault(message=f"{subject.path}:{position.role}")]


@rule(
    code="XTS002",
    family=Family.CUSTOM,
    slug="typed-project-subject",
    message="typed project",
)
def typed_project_subject(*, owner: Project, context: RuleContext) -> list[Fault]:
    """Report deterministic tree and requester-bound cross-file facts once."""

    del owner
    support: ProjectPath = ProjectPath("tests/test_checkout.py")
    position: FilePosition | None = context.project.tree.position(support)
    assert position is not None
    assert context.project.exists(path=support)
    assert context.project.tree.children("tests") == (support,)
    assert support in context.project.tree.descendants()
    assert support in context.project.tree.glob("**/*.py")
    assert context.project.tree.files_under("tests") == (File(path=support),)
    return [
        context.path_fault(
            path=support,
            message=f"{len(context.project.tree.files)}:{position.scope.value}",
        )
    ]


@rule(
    code="XTS003",
    family=Family.CUSTOM,
    slug="anchor-free-project",
    message="anchor free",
)
def anchor_free_project(*, project: Project, ctx: RuleContext) -> list[Fault]:
    """Report without reading any current-file state."""

    del project
    return [ctx.path_fault(path="src/example/main/example.py")]


@rule(
    code="XTS004",
    family=Family.CUSTOM,
    slug="invalid-project-context-read",
    message="invalid project context read",
)
def invalid_project_context_read(*, project: Project, ctx: RuleContext) -> list[Fault]:
    """Exercise clear failure for current-file-only context state."""

    del project
    _ = ctx.source
    return []


@rule(
    code="XTS005",
    family=Family.CUSTOM,
    slug="invalid-project-glob",
    message="invalid project glob",
)
def invalid_project_glob(*, project: Project, ctx: RuleContext) -> list[Fault]:
    """Exercise confinement validation on tree glob inputs."""

    del project
    _ = ctx.project.tree.glob("../*.py")
    return []


@rule(
    code="XTS007",
    family=Family.CUSTOM,
    slug="invalid-project-tree-path",
    message="invalid project tree path",
)
def invalid_project_tree_path(*, project: Project, ctx: RuleContext) -> list[Fault]:
    """Exercise rejection of pathlib and absolute tree inputs."""

    del project
    _ = ctx.project.tree.position(Path("/outside.py"))  # ty: ignore[invalid-argument-type]
    return []


@rule(
    code="XHT001",
    family=Family.CUSTOM,
    slug="all-context-zones",
    message="all public context zones are available",
)
def all_context_zones(module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Exercise facts, project, text, syntax, and relations through the real context."""

    function_facts: FunctionFacts = ctx.facts.functions()
    source_line: str = ctx.text.line(1)
    handles: tuple[SyntaxHandle, ...] = ctx.syntax.handles()
    parent: SyntaxHandle | None = ctx.relations.parent(handles[-1])
    support_function: ProjectFunctionFact | None = ctx.project.module_function(
        requester=ctx.path,
        module_name="example.support",
        function_name="support_value",
    )
    directory_entries: tuple[Path, ...] = ctx.project.directory_entries(
        requester=ctx.path,
        path=ctx.scope_root(),
    )
    del function_facts, source_line, parent, support_function, directory_entries
    return [ctx.fault(node=module.body[0])]


@rule(
    code="XHT002",
    family=Family.CUSTOM,
    slug="always-fault",
    message="one direct target",
)
def always_fault(module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Emit one fault for every direct evaluation target."""

    return [ctx.fault(node=module.body[0])]


@rule(
    code="XHT003",
    family=Family.CUSTOM,
    slug="context-policy",
    message="context policy",
)
def context_policy(module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Expose scope, role, thresholds, and contracts in one observable fault."""

    del module
    message: str = "|".join(
        (
            ctx.scope().value,
            ctx.role_of() or "none",
            str(ctx.threshold(name=Threshold.MAX_STATEMENTS)),
            ctx.contracts().get("inspect_*", "missing"),
            ctx.scope_root().relative_to(ctx.repo_root).as_posix(),
        )
    )
    return [ctx.path_fault(message=message)]


@rule(
    code="XHT004",
    family=Family.CUSTOM,
    slug="ordinary-ordering",
    message="ordinary ordering",
)
def ordinary_ordering(module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Return reverse-source findings so the ordinary collector must order them."""

    return [ctx.fault(node=module.body[1]), ctx.fault(node=module.body[0])]


@rule(
    code="XNF001",
    family=Family.CUSTOM,
    slug="native-class-declarations",
    message="adapter class declaration",
)
def native_class_declarations(module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Exercise class declaration facts without reading the raw module."""

    del module
    return [ctx.fault_at(location=fact.location) for fact in ctx.facts.class_declarations()]


@rule(
    code="XNF002",
    family=Family.CUSTOM,
    slug="native-assignment-references",
    message="base adapter assignment reference",
)
def native_assignment_references(module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Exercise assignment reference facts without reading the raw module."""

    del module
    return [ctx.fault_at(location=fact.location) for fact in ctx.facts.assignment_references()]


@rule(
    code="XNF003",
    family=Family.CUSTOM,
    slug="native-named-calls",
    message="discarded metadata call in loop",
)
def native_named_calls(module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Exercise named call facts without reading the raw module."""

    del module
    return [ctx.fault_at(location=fact.location) for fact in ctx.facts.named_calls()]


@rule(
    code="XNF004",
    family=Family.CUSTOM,
    slug="native-local-call-edges",
    message="metadata query call edge in loop",
)
def native_local_call_edges(module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Exercise local call edges without reading the raw module."""

    del module
    return [ctx.fault_at(location=fact.location) for fact in ctx.facts.local_call_edges()]


@rule(
    code="XNF005",
    family=Family.CUSTOM,
    slug="native-comparisons",
    message="canonical reference comparison",
)
def native_comparisons(module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Exercise comparison facts without reading the raw module."""

    del module
    return [ctx.fault_at(location=fact.location) for fact in ctx.facts.comparisons()]


@rule(
    code="XNF006",
    family=Family.CUSTOM,
    slug="native-parameter-mutation-occurrences",
    message="parameter mutation occurrence",
)
def native_parameter_mutation_occurrences(module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Exercise complete parameter mutation facts without reading the raw module."""

    del module
    return [
        ctx.fault_at(location=fact.location) for fact in ctx.facts.parameter_mutation_occurrences()
    ]


def undecorated_rule(module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Provide an invalid undecorated harness input."""

    del module, ctx
    return []


@rule(
    code="XOP001",
    family=Family.CUSTOM,
    slug="option-finding",
    message="option-controlled finding",
    options=(_REPORT_FINDING_OPTION,),
)
def option_finding(module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Make finding presence observable from the resolved boolean option."""

    del module
    return [ctx.path_fault()] * int(ctx.option(_REPORT_FINDING_OPTION))


@rule(
    code="XOP002",
    family=Family.CUSTOM,
    slug="option-list-value",
    message="resolved list option",
    options=(_LABELS_OPTION,),
)
def option_list_value(module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Expose the canonical container and values received by a custom rule."""

    del module
    labels: tuple[str, ...] = ctx.option(_LABELS_OPTION)
    message: str = f"{type(labels).__name__}:{','.join(labels)}"
    return [ctx.path_fault(message=message)]


@rule(
    code="XOP003",
    family=Family.CUSTOM,
    slug="required-option",
    message="required option",
    options=(_REQUIRED_COUNT_OPTION,),
)
def required_option(module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Declare one required option for harness validation coverage."""

    del module
    _ = ctx.option(_REQUIRED_COUNT_OPTION)
    return []


@rule(
    code="XOP004",
    family=Family.CUSTOM,
    slug="option-owner",
    message="option owner",
    options=(_OWNER_ONLY_OPTION,),
)
def option_owner(module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Own an option that another rule must not access."""

    del module
    _ = ctx.option(_OWNER_ONLY_OPTION)
    return []


@rule(
    code="XOP005",
    family=Family.CUSTOM,
    slug="cross-rule-option-access",
    message="cross-rule option access",
    options=(_LOCAL_OPTION,),
)
def cross_rule_option_access(module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Attempt to access an option declared by a different rule."""

    del module
    _ = ctx.option(_OWNER_ONLY_OPTION)
    return []
