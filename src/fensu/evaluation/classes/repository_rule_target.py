"""Explicit target-local fact handles for one repository-rule invocation."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import NoReturn, cast

from fensu.analysis.models import SourceLocation
from fensu.config.types import AnalyzerId
from fensu.evaluation.classes.repository_dependency_observer import (
    RepositoryDependencyObserver,
)
from fensu.evaluation.constants import REPOSITORY_TARGET_PAYLOAD_FIELDS
from fensu.evaluation.exceptions import RepositoryRuleError
from fensu.evaluation.types import RepositoryDependencyKind
from fensu.rules.authoring.constants import PROJECT_ROOT
from fensu.rules.authoring.main.architecture_graph import architecture_graph
from fensu.rules.authoring.main.build_python_repository_facts import (
    build_python_repository_facts,
)
from fensu.rules.authoring.main.build_rust_project_tree import build_rust_project_tree
from fensu.rules.authoring.main.build_rust_workspace_facts import build_rust_workspace_facts
from fensu.rules.authoring.main.build_web_architecture_graph import (
    build_web_architecture_graph,
)
from fensu.rules.authoring.main.build_web_project_tree import build_web_project_tree
from fensu.rules.authoring.main.build_web_workspace_facts import build_web_workspace_facts
from fensu.rules.authoring.main.project_root_path import project_root_path
from fensu.rules.authoring.main.select_rust_workspace_facts import select_rust_workspace_facts
from fensu.rules.authoring.models import (
    ArchitectureGraph,
    AuthoredImport,
    File,
    FilePosition,
    ImportEdge,
    ModuleNode,
    ProjectPath,
    ProjectTree,
    PythonWorkspaceFacts,
    RustFileFacts,
    RustWorkspaceFacts,
    Target,
    WebWorkspaceFacts,
)
from fensu.rules.authoring.types import ImportResolution, ModuleVisibility, SourceKind


class RepositoryRuleTargetView:
    """One target identity and its isolated typed query surfaces."""

    def __init__(  # noqa: PLR0913
        self,
        *,
        identity: Target,
        tree: ProjectTree,
        graph: ArchitectureGraph,
        python: PythonWorkspaceFacts | None,
        rust: RustWorkspaceFacts | None,
        web: WebWorkspaceFacts | None,
        observations: list[dict[str, str]] | None = None,
        allowed_analyzers: frozenset[AnalyzerId] | None = None,
    ) -> None:
        self.identity = identity
        self._tree = tree
        self._graph = graph
        self._python = python
        self._rust = rust
        self._web = web
        self._observations = observations
        self._allowed_analyzers = allowed_analyzers

    @property
    def tree(self) -> ProjectTree:
        """Return the observed target-local tree."""

        self._require_declared()
        return self._tree.observed(self._observer())

    @property
    def graph(self) -> ArchitectureGraph:
        """Return the observed target-local graph."""

        self._require_declared()
        return self._graph.observed(self._observer())

    @property
    def python(self) -> PythonWorkspaceFacts:
        """Return target-local Python facts."""

        self._require_declared()
        if self._python is None:
            return self._unavailable("python")
        return self._python.observed(self._observer())

    @property
    def rust(self) -> RustWorkspaceFacts:
        """Return target-local Rust facts."""

        self._require_declared()
        if self._rust is None:
            return self._unavailable("rust")
        return self._rust.observed(self._observer())

    @property
    def web(self) -> WebWorkspaceFacts:
        """Return target-local web facts."""

        self._require_declared()
        if self._web is None:
            return self._unavailable("web")
        return self._web.observed(self._observer())

    def repository_path(self, value: File | ProjectPath) -> ProjectPath:
        """Translate one target-local identity to repository-relative form."""

        path: ProjectPath = value.path if isinstance(value, File) else value
        if not isinstance(path, ProjectPath):
            from fensu.rules.authoring.exceptions import TargetFactQueryTypeError

            raise TargetFactQueryTypeError("repository_path requires a File or ProjectPath")
        if self.identity.root.value == PROJECT_ROOT:
            return path
        return ProjectPath(f"{self.identity.root.value}/{path.value}")

    def repository_location(self, value: SourceLocation) -> SourceLocation:
        """Translate one target-local source location to repository-relative form."""

        if not isinstance(value, SourceLocation):
            from fensu.rules.authoring.exceptions import TargetFactQueryTypeError

            raise TargetFactQueryTypeError("repository_location requires a SourceLocation")
        path: ProjectPath = ProjectPath(value.path.as_posix())
        return SourceLocation(
            path=Path(self.repository_path(path).value),
            line=value.line,
            column=value.column,
        )

    def observed(
        self,
        *,
        observations: list[dict[str, str]],
        allowed_analyzers: frozenset[AnalyzerId] | None = None,
    ) -> RepositoryRuleTargetView:
        """Bind every target-local query to one repository-rule observation list."""

        return RepositoryRuleTargetView(
            identity=self.identity,
            tree=self._tree,
            graph=self._graph,
            python=self._python,
            rust=self._rust,
            web=self._web,
            observations=observations,
            allowed_analyzers=allowed_analyzers,
        )

    def replay(self, *, kind: str, query: str, answer: str) -> str | None:
        """Re-run one previously observed query and return its current answer."""

        observations: list[dict[str, str]] = []
        target: RepositoryRuleTargetView = self.observed(observations=observations)
        try:
            dependency_kind: RepositoryDependencyKind = RepositoryDependencyKind(kind)
        except ValueError:
            return None
        if dependency_kind is RepositoryDependencyKind.TREE_PATHS:
            _ = target.tree.paths
        elif dependency_kind is RepositoryDependencyKind.TREE_FILES:
            _ = target.tree.files
        elif dependency_kind is RepositoryDependencyKind.TREE_CHILDREN:
            _ = target.tree.children(query)
        elif dependency_kind is RepositoryDependencyKind.TREE_DESCENDANTS:
            _ = target.tree.descendants(query)
        elif dependency_kind is RepositoryDependencyKind.TREE_GLOB:
            _ = target.tree.glob(answer.partition("\0")[0])
        elif dependency_kind is RepositoryDependencyKind.TREE_FILES_UNDER:
            _ = target.tree.files_under(query)
        elif dependency_kind is RepositoryDependencyKind.TREE_POSITION:
            _ = target.tree.position(ProjectPath(query))
        elif dependency_kind is RepositoryDependencyKind.GRAPH_NODES:
            _ = target.graph.nodes
        elif dependency_kind is RepositoryDependencyKind.GRAPH_NODE:
            _ = target.graph.node(ProjectPath(query))
        elif dependency_kind is RepositoryDependencyKind.GRAPH_IMPORTS:
            _ = target.graph.imports(ProjectPath(query))
        elif dependency_kind is RepositoryDependencyKind.GRAPH_DEPENDENCIES:
            _ = target.graph.dependencies(ProjectPath(query))
        elif dependency_kind is RepositoryDependencyKind.GRAPH_DEPENDENTS:
            _ = target.graph.dependents(ProjectPath(query))
        elif dependency_kind is RepositoryDependencyKind.GRAPH_CYCLES:
            _ = target.graph.cycles()
        elif dependency_kind is RepositoryDependencyKind.PYTHON_FILES:
            _ = target.python.files
        elif dependency_kind is RepositoryDependencyKind.PYTHON_FILE:
            _ = target.python.file(ProjectPath(query))
        elif dependency_kind is RepositoryDependencyKind.RUST_CRATES:
            _ = target.rust.crates
        elif dependency_kind is RepositoryDependencyKind.RUST_FILES:
            _ = target.rust.files
        elif dependency_kind is RepositoryDependencyKind.RUST_CRATE:
            _ = target.rust.crate(query)
        elif dependency_kind is RepositoryDependencyKind.RUST_FILE:
            _ = target.rust.file(ProjectPath(query))
        elif dependency_kind is RepositoryDependencyKind.WEB_FILES:
            _ = target.web.files
        elif dependency_kind is RepositoryDependencyKind.WEB_FILE:
            _ = target.web.file(ProjectPath(query))
        return observations[0]["answer"] if len(observations) == 1 else None

    def _observer(self) -> RepositoryDependencyObserver:
        return RepositoryDependencyObserver(
            target=self.identity.name,
            observations=[] if self._observations is None else self._observations,
        )

    def _unavailable(self, name: str) -> NoReturn:
        from fensu.rules.authoring.exceptions import TargetFactsUnavailableError

        raise TargetFactsUnavailableError(
            f"Target {self.identity.name!r} uses {self.identity.analyzer.value}, not {name} facts"
        )

    def _require_declared(self) -> None:
        if (
            self._allowed_analyzers is not None
            and self.identity.analyzer not in self._allowed_analyzers
        ):
            from fensu.rules.authoring.exceptions import TargetFactsUnavailableError

            raise TargetFactsUnavailableError(
                f"Repository rule did not declare {self.identity.analyzer.value} target facts"
            )


def build_repository_rule_target(*, payload: object) -> RepositoryRuleTargetView:
    """Build one strict target-local fact view from the native repository payload."""

    value: Mapping[str, object] = _mapping(value=payload)
    if set(value) != REPOSITORY_TARGET_PAYLOAD_FIELDS:
        raise RepositoryRuleError("Repository target payload contains incompatible fields")
    name: str = _string(value=value["name"], name="target name")
    analyzer: AnalyzerId = AnalyzerId(_string(value=value["analyzer"], name="target analyzer"))
    root_text: str = _string(value=value["root"], name="target root")
    root: ProjectPath = project_root_path() if root_text == PROJECT_ROOT else ProjectPath(root_text)
    ownership_roots: tuple[str, ...] = _string_sequence(
        value=value["ownership_roots"], name="target ownership roots"
    )
    identity: Target = Target(name=name, analyzer=analyzer, root=root)
    if analyzer is AnalyzerId.PYTHON:
        python, tree, graph = build_python_repository_facts(
            payload=value["facts"], subjects=value["subjects"]
        )
        return RepositoryRuleTargetView(
            identity=identity, tree=tree, graph=graph, python=python, rust=None, web=None
        )
    if analyzer is AnalyzerId.RUST:
        workspace: RustWorkspaceFacts = build_rust_workspace_facts(payload=value["facts"])
        selected: Mapping[ProjectPath, RustFileFacts]
        tree, selected = build_rust_project_tree(
            subjects=value["subjects"],
            workspace=workspace,
            ownership_roots=ownership_roots,
        )
        workspace = select_rust_workspace_facts(workspace=workspace, files=selected)
        return RepositoryRuleTargetView(
            identity=identity,
            tree=tree,
            graph=_rust_graph(tree=tree, workspace=workspace),
            python=None,
            rust=workspace,
            web=None,
        )
    workspace = build_web_workspace_facts(payload=value["facts"])
    tree: ProjectTree = build_web_project_tree(
        subjects=value["subjects"],
        workspace=workspace,
        ownership_roots=ownership_roots,
    )
    return RepositoryRuleTargetView(
        identity=identity,
        tree=tree,
        graph=build_web_architecture_graph(
            workspace=workspace,
            ownership_roots=ownership_roots,
            subjects=value["subjects"],
        ),
        python=None,
        rust=None,
        web=workspace,
    )


def _rust_graph(*, tree: ProjectTree, workspace: RustWorkspaceFacts) -> ArchitectureGraph:
    nodes: list[ModuleNode] = []
    for facts in workspace.files:
        position: FilePosition | None = tree.position(facts.file.path)
        if position is None:
            continue
        nodes.append(
            ModuleNode(
                file=facts.file,
                analyzer=AnalyzerId.RUST,
                source_kind=SourceKind.RUST_MODULE,
                module="::".join(facts.module_parts),
                scope=position.scope,
                scope_root=position.scope_root,
                package=facts.crate_name,
                domain_parts=position.domain_parts,
                role=position.role,
                visibility=ModuleVisibility.PUBLIC,
                ownership_root=position.ownership_root,
            )
        )
    by_path: dict[ProjectPath, ModuleNode] = {item.file.path: item for item in nodes}
    facts_by_path: dict[ProjectPath, RustFileFacts] = {
        item.file.path: item for item in workspace.files
    }
    imports: dict[ProjectPath, tuple[ImportEdge, ...]] = {}
    for node in nodes:
        edges: list[ImportEdge] = []
        for use in facts_by_path[node.file.path].uses:
            target: ModuleNode | None = None if use.target is None else by_path.get(use.target.path)
            edges.append(
                ImportEdge(
                    source=node,
                    authored=AuthoredImport(
                        module_parts=use.authored_parts,
                        imported_parts=use.authored_parts,
                        bound_name=use.authored_parts[-1] if use.authored_parts else "",
                        relative_level=0,
                        from_import=False,
                    ),
                    module=(
                        None
                        if use.target_module_parts is None
                        else "::".join(use.target_module_parts)
                    ),
                    location=use.location,
                    status=(
                        ImportResolution.RESOLVED
                        if target is not None
                        else ImportResolution.UNRESOLVED
                    ),
                    target=target,
                )
            )
        imports[node.file.path] = tuple(edges)
    return architecture_graph(nodes=tuple(nodes), imports=imports)


def _mapping(*, value: object) -> Mapping[str, object]:
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise RepositoryRuleError("Repository target payload must be an object")
    return cast("Mapping[str, object]", value)


def _string(*, value: object, name: str) -> str:
    if not isinstance(value, str):
        raise RepositoryRuleError(f"Repository {name} must be a string")
    return value


def _string_sequence(*, value: object, name: str) -> tuple[str, ...]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise RepositoryRuleError(f"Repository {name} must be an array of strings")
    return tuple(cast("list[str]", value))
