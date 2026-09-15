"""Build Python graph facts from discovered modules and public import facts."""

from __future__ import annotations

from fensu.analysis.models import ImportAliasFact, ImportFact
from fensu.discovery.constants import INIT_MODULE_FILE_NAME
from fensu.discovery.models import DiscoveredTree, ProjectSource, RepoRoot, ScopedFile
from fensu.discovery.types import ScopeName
from fensu.evaluation.constants import ARCHITECTURE_PUBLIC_ROLES
from fensu.evaluation.models import ArchitectureModule, ParsedModule
from fensu.evaluation.types import EvaluationProjectAnalysis
from fensu.rules.authoring.main.architecture_graph import architecture_graph
from fensu.rules.authoring.main.build_project_tree import build_project_tree
from fensu.rules.authoring.models import (
    ArchitectureGraph,
    AuthoredImport,
    File,
    FilePosition,
    ImportEdge,
    ModuleNode,
    ProjectPath,
    ProjectTree,
)
from fensu.rules.authoring.types import ImportResolution, ModuleVisibility


class ArchitectureGraphBuilder:
    """Resolve static imports against authoritative discovered Python sources."""

    def __init__(self, *, tree: DiscoveredTree, analysis: EvaluationProjectAnalysis) -> None:
        self._tree: DiscoveredTree = tree
        self._analysis: EvaluationProjectAnalysis = analysis
        self._project_root: RepoRoot = (
            tree.repo_root if tree.project_root is None else tree.project_root
        )
        self._positions: ProjectTree = build_project_tree(tree=tree)

    def build(self) -> ArchitectureGraph:
        """Build deterministic graph facts from all represented static imports."""

        modules: tuple[ArchitectureModule, ...] = self._modules()
        modules_by_name: dict[str, ModuleNode] = self._unique_modules(modules=modules)
        imports: dict[ProjectPath, tuple[ImportEdge, ...]] = self._imports(
            modules=modules, modules_by_name=modules_by_name
        )
        return architecture_graph(nodes=tuple(item.node for item in modules), imports=imports)

    def _modules(self) -> tuple[ArchitectureModule, ...]:
        modules: list[ArchitectureModule] = []
        for scoped_file in self._tree.files:
            module: ArchitectureModule | None = self._architecture_module(scoped_file=scoped_file)
            if module is not None:
                modules.append(module)
        return tuple(modules)

    def _architecture_module(self, *, scoped_file: ScopedFile) -> ArchitectureModule | None:
        identity: tuple[str, str] | None = self._module_identity(scoped_file=scoped_file)
        if identity is None:
            return None
        parsed: ParsedModule = self._analysis.parsed_module(scoped_file)
        path: ProjectPath = ProjectPath(
            scoped_file.path.relative_to(self._project_root.path).as_posix()
        )
        position: FilePosition | None = self._positions.position(path)
        if position is None:
            return None
        module, package = identity
        return ArchitectureModule(
            scoped_file=scoped_file,
            parsed=parsed,
            node=ModuleNode(
                file=File(path),
                analyzer=position.analyzer,
                source_kind=position.source_kind,
                module=module,
                scope=scoped_file.scope,
                scope_root=ProjectPath(
                    scoped_file.root.relative_to(self._project_root.path).as_posix()
                ),
                package=package,
                domain_parts=position.domain_parts,
                role=position.role,
                visibility=self._visibility(module=module, package=package, role=position.role),
            ),
        )

    def _unique_modules(self, *, modules: tuple[ArchitectureModule, ...]) -> dict[str, ModuleNode]:
        candidates: dict[str, list[ModuleNode]] = {}
        for item in modules:
            candidates.setdefault(item.node.module, []).append(item.node)
        return {module: values[0] for module, values in candidates.items() if len(values) == 1}

    def _imports(
        self,
        *,
        modules: tuple[ArchitectureModule, ...],
        modules_by_name: dict[str, ModuleNode],
    ) -> dict[ProjectPath, tuple[ImportEdge, ...]]:
        imports: dict[ProjectPath, tuple[ImportEdge, ...]] = {}
        for item in modules:
            edges: list[ImportEdge] = []
            for fact in item.parsed.analysis.facts.references().imports:
                edges.extend(
                    self._resolve_fact(
                        source=item.node,
                        fact=fact,
                        modules=modules_by_name,
                    )
                )
            imports[item.node.file.path] = tuple(edges)
        return imports

    def _resolve_fact(
        self, *, source: ModuleNode, fact: ImportFact, modules: dict[str, ModuleNode]
    ) -> tuple[ImportEdge, ...]:
        edges: list[ImportEdge] = []
        for alias in fact.aliases:
            candidates: tuple[tuple[str, ...], ...] = self._candidates(
                source=source, fact=fact, alias=alias
            )
            target: ModuleNode | None = next(
                (modules[".".join(parts)] for parts in candidates if ".".join(parts) in modules),
                None,
            )
            edges.append(
                self._import_edge(
                    source=source,
                    fact=fact,
                    alias=alias,
                    candidates=candidates,
                    target=target,
                )
            )
        return tuple(edges)

    def _import_edge(
        self,
        *,
        source: ModuleNode,
        fact: ImportFact,
        alias: ImportAliasFact,
        candidates: tuple[tuple[str, ...], ...],
        target: ModuleNode | None,
    ) -> ImportEdge:
        authored: AuthoredImport = AuthoredImport(
            module_parts=fact.module_parts,
            imported_parts=alias.imported_parts,
            bound_name=alias.bound_name,
            relative_level=fact.relative_level,
            from_import=fact.from_import,
        )
        return ImportEdge(
            source=source,
            authored=authored,
            module=target.module if target is not None else self._unresolved_module(candidates),
            location=fact.location,
            status=ImportResolution.RESOLVED if target is not None else ImportResolution.UNRESOLVED,
            target=target,
        )

    def _candidates(
        self, *, source: ModuleNode, fact: ImportFact, alias: ImportAliasFact
    ) -> tuple[tuple[str, ...], ...]:
        if not fact.from_import:
            return (alias.imported_parts,)
        package: tuple[str, ...] = tuple(source.package.split(".")) if source.package else ()
        if fact.relative_level:
            parent_count: int = fact.relative_level - 1
            if parent_count > len(package):
                return ()
            base: tuple[str, ...] = (
                *package[: len(package) - parent_count],
                *fact.module_parts,
            )
        else:
            base = fact.module_parts
        imported: tuple[str, ...] = alias.imported_parts
        name_parts: tuple[str, ...] = (
            imported[len(fact.module_parts) :]
            if imported[: len(fact.module_parts)] == fact.module_parts
            else imported
        )
        submodule: tuple[str, ...] = (*base, *name_parts)
        return (submodule, base) if submodule != base else (base,)

    def _module_identity(self, *, scoped_file: ScopedFile) -> tuple[str, str] | None:
        source: ProjectSource | None = next(
            (
                item
                for item in (*self._tree.layout.runtime_sources, *self._tree.layout.tooling_sources)
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
        relative: tuple[str, ...] = scoped_file.relative_parts
        parts: tuple[str, ...] = (source.package_name, *relative[:-1], scoped_file.path.stem)
        if parts[-1] == INIT_MODULE_FILE_NAME.removesuffix(".py"):
            parts = parts[:-1]
        if not parts:
            return None
        package_parts: tuple[str, ...] = (
            parts if scoped_file.path.name == INIT_MODULE_FILE_NAME else parts[:-1]
        )
        return ".".join(parts), ".".join(package_parts)

    def _visibility(self, *, module: str, package: str, role: str | None) -> ModuleVisibility:
        private_part: bool = any(
            part.startswith("_") and part != INIT_MODULE_FILE_NAME.removesuffix(".py")
            for part in module.split(".")
        )
        if private_part or (module != package and role not in ARCHITECTURE_PUBLIC_ROLES):
            return ModuleVisibility.INTERNAL
        return ModuleVisibility.PUBLIC

    @staticmethod
    def _unresolved_module(candidates: tuple[tuple[str, ...], ...]) -> str | None:
        if not candidates or not candidates[-1]:
            return None
        return ".".join(candidates[-1])
