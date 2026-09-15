"""Build Python graph facts from discovered module identities and public import facts."""

from __future__ import annotations

from fensu.analysis.models import ImportAliasFact, ImportFact
from fensu.discovery.constants import INIT_MODULE_FILE_NAME
from fensu.discovery.models import DiscoveredTree, ProjectSource, RepoRoot, ScopedFile
from fensu.discovery.types import ScopeName
from fensu.evaluation.models import ParsedModule
from fensu.evaluation.types import EvaluationProjectAnalysis
from fensu.rules.authoring.graph import (
    ArchitectureGraph,
    AuthoredImport,
    ImportEdge,
    ImportResolution,
    ModuleNode,
    ModuleVisibility,
    architecture_graph,
)
from fensu.rules.authoring.subjects import File, ProjectPath, build_project_tree

_PUBLIC_ROLES = frozenset({"main", "classes", "models", "types", "constants", "exceptions"})


def build_architecture_graph(
    *, tree: DiscoveredTree, analysis: EvaluationProjectAnalysis
) -> ArchitectureGraph:
    """Resolve represented static imports only against authoritative discovered sources."""

    project_root: RepoRoot = tree.repo_root if tree.project_root is None else tree.project_root
    positions = build_project_tree(tree=tree)
    modules: list[tuple[ScopedFile, ParsedModule, ModuleNode]] = []
    for scoped_file in tree.files:
        identity = _module_identity(scoped_file=scoped_file, tree=tree)
        if identity is None:
            continue
        parsed = analysis.parsed_module(scoped_file)
        path = ProjectPath(scoped_file.path.relative_to(project_root.path).as_posix())
        position = positions.position(path)
        if position is None:
            continue
        module, package = identity
        node = ModuleNode(
            file=File(path),
            analyzer=position.analyzer,
            source_kind=position.source_kind,
            module=module,
            scope=scoped_file.scope,
            scope_root=ProjectPath(scoped_file.root.relative_to(project_root.path).as_posix()),
            package=package,
            domain_parts=position.domain_parts,
            role=position.role,
            visibility=_visibility(module=module, package=package, role=position.role),
        )
        modules.append((scoped_file, parsed, node))
    candidates_by_module: dict[str, list[ModuleNode]] = {}
    for _, _, node in modules:
        candidates_by_module.setdefault(node.module, []).append(node)
    by_module = {
        module: values[0] for module, values in candidates_by_module.items() if len(values) == 1
    }
    imports: dict[ProjectPath, tuple[ImportEdge, ...]] = {}
    for _scoped_file, parsed, source in modules:
        edges: list[ImportEdge] = []
        for fact in parsed.analysis.facts.references().imports:
            edges.extend(_resolve_fact(source=source, fact=fact, modules=by_module))
        imports[source.file.path] = tuple(edges)
    return architecture_graph(nodes=tuple(node for _, _, node in modules), imports=imports)


def _resolve_fact(
    *, source: ModuleNode, fact: ImportFact, modules: dict[str, ModuleNode]
) -> tuple[ImportEdge, ...]:
    edges: list[ImportEdge] = []
    for alias in fact.aliases:
        authored = AuthoredImport(
            module_parts=fact.module_parts,
            imported_parts=alias.imported_parts,
            bound_name=alias.bound_name,
            relative_level=fact.relative_level,
            from_import=fact.from_import,
        )
        candidates = _candidates(source=source, fact=fact, alias=alias)
        target = next(
            (modules[".".join(parts)] for parts in candidates if ".".join(parts) in modules), None
        )
        module = target.module if target is not None else _unresolved_module(candidates=candidates)
        edges.append(
            ImportEdge(
                source=source,
                authored=authored,
                module=module,
                location=fact.location,
                status=(
                    ImportResolution.RESOLVED if target is not None else ImportResolution.UNRESOLVED
                ),
                target=target,
            )
        )
    return tuple(edges)


def _unresolved_module(*, candidates: tuple[tuple[str, ...], ...]) -> str | None:
    if not candidates or not candidates[-1]:
        return None
    return ".".join(candidates[-1])


def _candidates(
    *, source: ModuleNode, fact: ImportFact, alias: ImportAliasFact
) -> tuple[tuple[str, ...], ...]:
    if not fact.from_import:
        return (alias.imported_parts,)
    package = tuple(source.package.split(".")) if source.package else ()
    if fact.relative_level:
        parent_count = fact.relative_level - 1
        if parent_count > len(package):
            return ()
        base = (*package[: len(package) - parent_count], *fact.module_parts)
    else:
        base = fact.module_parts
    # A from-import names a discovered submodule when one exists, otherwise its module/package.
    imported = alias.imported_parts
    name_parts = (
        imported[len(fact.module_parts) :]
        if imported[: len(fact.module_parts)] == fact.module_parts
        else imported
    )
    submodule = (*base, *name_parts)
    return (submodule, base) if submodule != base else (base,)


def _module_identity(*, scoped_file: ScopedFile, tree: DiscoveredTree) -> tuple[str, str] | None:
    source = next(
        (
            item
            for item in (*tree.layout.runtime_sources, *tree.layout.tooling_sources)
            if item.path == scoped_file.root
        ),
        None,
    )
    if source is None and scoped_file.scope is ScopeName.TEST:
        source = ProjectSource(
            path=scoped_file.root,
            relative_parts=(),
            import_root=scoped_file.root.parent,
            package_name=scoped_file.root.name,
        )
    if source is None:
        return None
    relative = scoped_file.relative_parts
    parts = (source.package_name, *relative[:-1], scoped_file.path.stem)
    if parts[-1] == INIT_MODULE_FILE_NAME.removesuffix(".py"):
        parts = parts[:-1]
    if not parts:
        return None
    package_parts = parts if scoped_file.path.name == INIT_MODULE_FILE_NAME else parts[:-1]
    return ".".join(parts), ".".join(package_parts)


def _visibility(*, module: str, package: str, role: str | None) -> ModuleVisibility:
    private_part = any(part.startswith("_") and part != "__init__" for part in module.split("."))
    if private_part or (module != package and role not in _PUBLIC_ROLES):
        return ModuleVisibility.INTERNAL
    return ModuleVisibility.PUBLIC
