"""Authoring structured runtime models: the fault and the compiled rule spec."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

from fensu.analysis.models import SourceLocation
from fensu.analysis.types import FactAnalysis, RelationAnalysis, SyntaxAnalysis, TextAnalysis
from fensu.config.types import AnalyzerId
from fensu.discovery.types import ScopeName
from fensu.rules.authoring.constants import MISSING, PROJECT_ROOT
from fensu.rules.authoring.exceptions import (
    ArchitectureGraphQueryError,
    ArchitectureGraphQueryTypeError,
    RustFactQueryTypeError,
)
from fensu.rules.authoring.types import (
    ExecutionOwner,
    Family,
    ImportResolution,
    Missing,
    ModuleVisibility,
    RuleCheck,
    RuleKind,
    RuleOptionKind,
    RuleSubjectKind,
    RustItemKind,
    RustUseResolution,
    RustVisibility,
    Severity,
    SourceKind,
    Threshold,
    WebModelKind,
    WebScriptContext,
    WebSourceKind,
    WebSourcePurpose,
    WebSyntaxKind,
)


@dataclass(frozen=True, slots=True, order=True)
class ProjectPath:
    """A normalized POSIX path confined to the analyzed project."""

    value: str

    def __post_init__(self) -> None:
        """Reject absolute, platform-specific, and escaping path spellings."""

        from fensu.rules.authoring._helpers.project_tree import validate_project_path

        validate_project_path(value=self.value)

    @property
    def parts(self) -> tuple[str, ...]:
        """Return normalized path components."""

        return PurePosixPath(self.value).parts

    @property
    def name(self) -> str:
        """Return the final path component."""

        return PurePosixPath(self.value).name

    @property
    def parent(self) -> ProjectPath:
        """Return the containing project path."""

        return ProjectPath(PurePosixPath(self.value).parent.as_posix())

    def as_posix(self) -> str:
        """Return the portable project-relative spelling."""

        return self.value

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class File:
    """Stable identity of one discovered source file."""

    path: ProjectPath


@dataclass(frozen=True, slots=True)
class Project:
    """Stable identity of the analyzed project."""


@dataclass(frozen=True, slots=True)
class Repository:
    """Stable identity of the configured multi-target repository."""


@dataclass(frozen=True, slots=True, order=True)
class Target:
    """Stable identity of one named analyzer target in a repository."""

    name: str
    analyzer: AnalyzerId
    root: ProjectPath


@dataclass(frozen=True, slots=True)
class PythonFileFacts:
    """One Python source identity, text, and analyzer-neutral analysis zones."""

    file: File
    source: str
    facts: FactAnalysis
    text: TextAnalysis
    syntax: SyntaxAnalysis
    relations: RelationAnalysis


@dataclass(frozen=True, slots=True)
class PythonWorkspaceFacts:
    """Requester-observed Python facts for one named repository target."""

    schema_version: str
    parser_contract: str
    _file_values: tuple[PythonFileFacts, ...] = field(repr=False)
    _files_by_path: Mapping[ProjectPath, PythonFileFacts] = field(repr=False, compare=False)
    _observe: Callable[[str, str, str], None] | None = field(
        default=None, repr=False, compare=False
    )

    @property
    def files(self) -> tuple[PythonFileFacts, ...]:
        """Return every discovered Python file and observe the broad inventory."""

        from fensu.rules.authoring._helpers.project_tree import python_file_identity

        self._record(
            kind="python_files",
            query=PROJECT_ROOT,
            answer="\n".join(python_file_identity(value=item) for item in self._file_values),
        )
        return self._file_values

    def file(self, value: File | ProjectPath) -> PythonFileFacts | None:
        """Return one focused Python file without observing the broad inventory."""

        path: ProjectPath = value.path if isinstance(value, File) else value
        if not isinstance(path, ProjectPath):
            from fensu.rules.authoring.exceptions import PythonFactQueryTypeError

            raise PythonFactQueryTypeError("Python file queries require a File or ProjectPath")
        answer: PythonFileFacts | None = self._files_by_path.get(path)
        from fensu.rules.authoring._helpers.project_tree import python_file_identity

        self._record(
            kind="python_file",
            query=path.value,
            answer="" if answer is None else python_file_identity(value=answer),
        )
        return answer

    def observed(self, observer: Callable[[str, str, str], None]) -> PythonWorkspaceFacts:
        """Return a fact view whose query answers are recorded for one invocation."""

        return PythonWorkspaceFacts(
            schema_version=self.schema_version,
            parser_contract=self.parser_contract,
            _file_values=self._file_values,
            _files_by_path=self._files_by_path,
            _observe=observer,
        )

    def _record(self, *, kind: str, query: str, answer: str) -> None:
        if self._observe is not None:
            self._observe(kind, query, answer)


@dataclass(frozen=True, slots=True)
class FilePosition:
    """Stable analyzer-neutral architecture position of one discovered file."""

    path: ProjectPath
    analyzer: AnalyzerId
    source_kind: SourceKind
    scope: ScopeName
    scope_root: ProjectPath
    module: str | None
    package: str | None
    domain_parts: tuple[str, ...]
    role: str | None
    role_depth: int | None
    is_entry_module: bool
    is_main_module: bool
    ownership_root: ProjectPath | None = None
    ownership_root_declaration: str | None = None
    ownership_relative_parts: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ProjectTree:
    """Immutable facts derived only from the authoritative discovered tree."""

    _paths: tuple[ProjectPath, ...]
    _files: tuple[File, ...]
    _children: Mapping[ProjectPath, tuple[ProjectPath, ...]] = field(repr=False, compare=False)
    _positions: Mapping[ProjectPath, FilePosition] = field(repr=False, compare=False)
    _repository_prefix: str = field(default=PROJECT_ROOT, repr=False, compare=False)
    _observe: (
        Callable[[str, ProjectPath, str | tuple[ProjectPath, ...], str | None], None] | None
    ) = field(default=None, repr=False, compare=False)

    @property
    def paths(self) -> tuple[ProjectPath, ...]:
        """Return all discovered paths and observe the broad inventory query."""

        from fensu.rules.authoring._helpers.project_tree import root_path

        self._record(kind="tree_paths", query=root_path(), answer=self._paths)
        return self._paths

    @property
    def files(self) -> tuple[File, ...]:
        """Return all discovered files and observe the broad file inventory query."""

        from fensu.rules.authoring._helpers.project_tree import root_path

        self._record(
            kind="tree_files", query=root_path(), answer=tuple(file.path for file in self._files)
        )
        return self._files

    def children(self, path: ProjectPath | str = PROJECT_ROOT) -> tuple[ProjectPath, ...]:
        """Return immediate discovered children in lexical POSIX order."""

        from fensu.rules.authoring._helpers.project_tree import project_path

        query: ProjectPath = project_path(value=path, allow_root=True)
        answer: tuple[ProjectPath, ...] = self._children.get(query, ())
        self._record(kind="tree_children", query=query, answer=answer)
        return answer

    def descendants(self, path: ProjectPath | str = PROJECT_ROOT) -> tuple[ProjectPath, ...]:
        """Return every discovered descendant in lexical POSIX order."""

        from fensu.rules.authoring._helpers.project_tree import project_path

        parent: ProjectPath = project_path(value=path, allow_root=True)
        prefix: tuple[str, ...] = () if parent.value == PROJECT_ROOT else parent.parts
        answer: tuple[ProjectPath, ...] = tuple(
            candidate
            for candidate in self._paths
            if len(candidate.parts) > len(prefix) and candidate.parts[: len(prefix)] == prefix
        )
        self._record(kind="tree_descendants", query=parent, answer=answer)
        return answer

    def glob(self, pattern: str) -> tuple[ProjectPath, ...]:
        """Return paths matching one confined project-relative POSIX glob."""

        from fensu.rules.authoring._helpers.project_tree import root_path, validate_project_glob

        validate_project_glob(pattern=pattern)
        answer: tuple[ProjectPath, ...] = tuple(
            path for path in self._paths if PurePosixPath(path.value).match(pattern)
        )
        self._record(kind="tree_glob", query=root_path(), answer=answer, pattern=pattern)
        return answer

    def files_under(self, path: ProjectPath | str = PROJECT_ROOT) -> tuple[File, ...]:
        """Return discovered files at or below a project path."""

        from fensu.rules.authoring._helpers.project_tree import project_path

        parent: ProjectPath = project_path(value=path, allow_root=True)
        prefix: tuple[str, ...] = () if parent.value == PROJECT_ROOT else parent.parts
        answer: tuple[File, ...] = tuple(
            file
            for file in self._files
            if file.path == parent
            or (len(file.path.parts) > len(prefix) and file.path.parts[: len(prefix)] == prefix)
        )
        self._record(
            kind="tree_files_under", query=parent, answer=tuple(file.path for file in answer)
        )
        return answer

    def position(self, path: ProjectPath | str) -> FilePosition | None:
        """Return complete architecture position facts for a discovered file."""

        from fensu.rules.authoring._helpers.project_tree import position_identity, project_path

        query: ProjectPath = project_path(value=path)
        answer: FilePosition | None = self._positions.get(query)
        self._record(kind="tree_position", query=query, answer=position_identity(position=answer))
        return answer

    def observed(
        self,
        observer: Callable[[str, ProjectPath, str | tuple[ProjectPath, ...], str | None], None],
    ) -> ProjectTree:
        """Return an immutable view whose accesses are bound to one requester."""

        return ProjectTree(
            _paths=self._paths,
            _files=self._files,
            _children=self._children,
            _positions=self._positions,
            _repository_prefix=self._repository_prefix,
            _observe=observer,
        )

    def _record(
        self,
        *,
        kind: str,
        query: ProjectPath,
        answer: str | tuple[ProjectPath, ...],
        pattern: str | None = None,
    ) -> None:
        if self._observe is not None:
            self._observe(kind, query, answer, pattern)


@dataclass(frozen=True, slots=True, order=True)
class ModuleNode:
    """Stable architecture identity and ownership of one discovered source module."""

    file: File
    analyzer: AnalyzerId
    source_kind: SourceKind
    module: str
    scope: ScopeName
    scope_root: ProjectPath
    package: str
    domain_parts: tuple[str, ...]
    role: str | None
    visibility: ModuleVisibility
    ownership_root: ProjectPath | None = None


@dataclass(frozen=True, slots=True, order=True)
class AuthoredImport:
    """The import identity written by an author, before project resolution."""

    module_parts: tuple[str, ...]
    imported_parts: tuple[str, ...]
    bound_name: str
    relative_level: int
    from_import: bool


@dataclass(frozen=True, slots=True, order=True)
class ImportEdge:
    """One static authored import and its explicit project-resolution result."""

    source: ModuleNode
    authored: AuthoredImport
    module: str | None
    location: SourceLocation
    status: ImportResolution
    target: ModuleNode | None


@dataclass(frozen=True, slots=True, order=True)
class ImportCycle:
    """One statically proven strongly-connected import component."""

    nodes: tuple[ModuleNode, ...]


@dataclass(frozen=True, slots=True)
class ArchitectureGraph:
    """Resolved static imports from authoritative discovered analyzer sources."""

    _node_values: tuple[ModuleNode, ...] = field(repr=False)
    _nodes_by_path: Mapping[ProjectPath, ModuleNode] = field(repr=False, compare=False)
    _imports: Mapping[ProjectPath, tuple[ImportEdge, ...]] = field(repr=False, compare=False)
    _dependencies: Mapping[ProjectPath, tuple[ModuleNode, ...]] = field(repr=False, compare=False)
    _dependents: Mapping[ProjectPath, tuple[ModuleNode, ...]] = field(repr=False, compare=False)
    _cycles: tuple[ImportCycle, ...] = field(repr=False)
    _observe: Callable[[str, ProjectPath, str], None] | None = field(
        default=None, repr=False, compare=False
    )

    @property
    def nodes(self) -> tuple[ModuleNode, ...]:
        """Return all graph nodes and observe the broad module inventory."""

        from fensu.rules.authoring._helpers.architecture_graph import nodes_identity, root_path

        self._record(kind="graph_nodes", path=root_path(), answer=nodes_identity(self._node_values))
        return self._node_values

    def node(self, value: File | ProjectPath) -> ModuleNode | None:
        """Return one discovered module identity without observing the broad inventory."""

        from fensu.rules.authoring._helpers.architecture_graph import optional_node_identity

        path: ProjectPath = value.path if isinstance(value, File) else value
        if not isinstance(path, ProjectPath):
            raise ArchitectureGraphQueryTypeError(
                "graph node queries require a File or ProjectPath"
            )
        answer: ModuleNode | None = self._nodes_by_path.get(path)
        self._record(kind="graph_node", path=path, answer=optional_node_identity(answer))
        return answer

    def dependencies(self, value: ModuleNode | File | ProjectPath) -> tuple[ModuleNode, ...]:
        """Return resolved direct targets in stable module order."""

        from fensu.rules.authoring._helpers.architecture_graph import nodes_identity

        path: ProjectPath = self._path(value)
        answer: tuple[ModuleNode, ...] = self._dependencies.get(path, ())
        self._record(kind="graph_dependencies", path=path, answer=nodes_identity(answer))
        return answer

    def dependents(self, value: ModuleNode | File | ProjectPath) -> tuple[ModuleNode, ...]:
        """Return resolved direct importers in stable module order."""

        from fensu.rules.authoring._helpers.architecture_graph import nodes_identity

        path: ProjectPath = self._path(value)
        answer: tuple[ModuleNode, ...] = self._dependents.get(path, ())
        self._record(kind="graph_dependents", path=path, answer=nodes_identity(answer))
        return answer

    def imports(self, value: ModuleNode | File | ProjectPath) -> tuple[ImportEdge, ...]:
        """Return all represented static imports, including explicitly unresolved imports."""

        from fensu.rules.authoring._helpers.architecture_graph import imports_identity

        path: ProjectPath = self._path(value)
        answer: tuple[ImportEdge, ...] = self._imports.get(path, ())
        self._record(kind="graph_imports", path=path, answer=imports_identity(answer))
        return answer

    def cycles(self) -> tuple[ImportCycle, ...]:
        """Return deterministic statically proven cycles; unresolved imports are excluded."""

        from fensu.rules.authoring._helpers.architecture_graph import cycles_identity, root_path

        self._record(kind="graph_cycles", path=root_path(), answer=cycles_identity(self._cycles))
        return self._cycles

    def observed(self, observer: Callable[[str, ProjectPath, str], None]) -> ArchitectureGraph:
        """Return a fact view whose query answers are recorded for one rule invocation."""

        return ArchitectureGraph(
            _node_values=self._node_values,
            _nodes_by_path=self._nodes_by_path,
            _imports=self._imports,
            _dependencies=self._dependencies,
            _dependents=self._dependents,
            _cycles=self._cycles,
            _observe=observer,
        )

    def snapshot(self, *, repository_prefix: str) -> dict[str, object]:
        """Return repository-relative replay identities for every supported graph query."""

        from fensu.rules.authoring._helpers.architecture_graph import (
            cycles_identity,
            imports_identity,
            nodes_identity,
            optional_node_identity,
            repository_graph_path,
        )

        return {
            "root_prefix": repository_prefix,
            "nodes": nodes_identity(self._node_values),
            "node": {
                repository_graph_path(
                    path=node.file.path, repository_prefix=repository_prefix
                ): optional_node_identity(node)
                for node in self._node_values
            },
            "dependencies": {
                repository_graph_path(
                    path=path, repository_prefix=repository_prefix
                ): nodes_identity(value)
                for path, value in self._dependencies.items()
            },
            "dependents": {
                repository_graph_path(
                    path=path, repository_prefix=repository_prefix
                ): nodes_identity(value)
                for path, value in self._dependents.items()
            },
            "imports": {
                repository_graph_path(
                    path=path, repository_prefix=repository_prefix
                ): imports_identity(value)
                for path, value in self._imports.items()
            },
            "cycles": cycles_identity(self._cycles),
        }

    def _path(self, value: ModuleNode | File | ProjectPath) -> ProjectPath:
        path: ProjectPath
        if isinstance(value, ModuleNode):
            path = value.file.path
        elif isinstance(value, File):
            path = value.path
        elif isinstance(value, ProjectPath):
            path = value
        else:
            raise ArchitectureGraphQueryTypeError(
                "graph queries require a ModuleNode, File, or ProjectPath"
            )
        if path not in self._nodes_by_path:
            raise ArchitectureGraphQueryError(
                f"graph path is not a discovered source module: {path}"
            )
        return path

    def _record(self, *, kind: str, path: ProjectPath, answer: str) -> None:
        if self._observe is not None:
            self._observe(kind, path, answer)


@dataclass(frozen=True, slots=True, order=True)
class RustTargetFact:
    """One stable Cargo target identity owned by a workspace crate."""

    identity: str
    name: str
    kinds: tuple[str, ...]
    source_root: ProjectPath
    entry_path: ProjectPath
    test: bool


@dataclass(frozen=True, slots=True, order=True)
class RustDependencyFact:
    """One Cargo dependency identity and its strongest resolution evidence."""

    package_name: str
    source_name: str
    kinds: tuple[str, ...]
    local_crate_identity: str | None
    resolved: bool


@dataclass(frozen=True, slots=True, order=True)
class RustCrateFact:
    """One Cargo workspace package with immutable targets and dependencies."""

    identity: str
    name: str
    directory: ProjectPath
    manifest_path: ProjectPath
    library_name: str | None
    targets: tuple[RustTargetFact, ...]
    dependencies: tuple[RustDependencyFact, ...]


@dataclass(frozen=True, slots=True, order=True)
class RustItemFact:
    """One parser-independent Rust declaration and stable source location."""

    kind: RustItemKind
    name: str | None
    module_parts: tuple[str, ...]
    visibility: RustVisibility
    visibility_path: str | None
    derives: tuple[str, ...]
    implemented_trait: str | None
    implementation_target: str | None
    location: SourceLocation


@dataclass(frozen=True, slots=True, order=True)
class RustUseFact:
    """One authored Rust use path and its explicit resolution result."""

    source: File
    source_module_parts: tuple[str, ...]
    authored_parts: tuple[str, ...]
    target_module_parts: tuple[str, ...] | None
    target: File | None
    target_crate_identity: str | None
    resolution: RustUseResolution
    location: SourceLocation


@dataclass(frozen=True, slots=True, order=True)
class RustFileFacts:
    """Owned immutable source, module, item, and use facts for one Rust file."""

    file: File
    crate_identity: str
    crate_name: str
    module_parts: tuple[str, ...]
    source_root: ProjectPath
    test: bool
    source: str
    parse_error: str | None
    items: tuple[RustItemFact, ...]
    uses: tuple[RustUseFact, ...]


@dataclass(frozen=True, slots=True)
class RustWorkspaceFacts:
    """Versioned requester-observed Rust facts for one Cargo workspace."""

    schema_version: str
    parser_contract: str
    _crate_values: tuple[RustCrateFact, ...] = field(repr=False)
    _file_values: tuple[RustFileFacts, ...] = field(repr=False)
    _crates_by_identity: Mapping[str, RustCrateFact] = field(repr=False, compare=False)
    _files_by_path: Mapping[ProjectPath, RustFileFacts] = field(repr=False, compare=False)
    _observe: Callable[[str, str, str], None] | None = field(
        default=None, repr=False, compare=False
    )

    @property
    def crates(self) -> tuple[RustCrateFact, ...]:
        """Return all workspace crates and observe the broad Cargo inventory."""

        from fensu.rules.authoring._helpers.fact_identity import rust_crate_identity

        self._record(
            kind="rust_crates",
            query=".",
            answer="\n".join(rust_crate_identity(value=item) for item in self._crate_values),
        )
        return self._crate_values

    @property
    def files(self) -> tuple[RustFileFacts, ...]:
        """Return all Rust files and observe the broad source inventory."""

        from fensu.rules.authoring._helpers.fact_identity import rust_file_identity

        self._record(
            kind="rust_files",
            query=".",
            answer="\n".join(rust_file_identity(value=item) for item in self._file_values),
        )
        return self._file_values

    def crate(self, identity: str) -> RustCrateFact | None:
        """Return one crate by stable workspace identity."""

        if not isinstance(identity, str):
            raise RustFactQueryTypeError("Rust crate queries require a string identity")
        value: RustCrateFact | None = self._crates_by_identity.get(identity)
        from fensu.rules.authoring._helpers.fact_identity import rust_crate_identity

        self._record(
            kind="rust_crate",
            query=identity,
            answer="" if value is None else rust_crate_identity(value=value),
        )
        return value

    def file(self, value: File | ProjectPath) -> RustFileFacts | None:
        """Return facts for one discovered Rust file without observing all files."""

        path: ProjectPath = value.path if isinstance(value, File) else value
        if not isinstance(path, ProjectPath):
            raise RustFactQueryTypeError("Rust file queries require a File or ProjectPath")
        answer: RustFileFacts | None = self._files_by_path.get(path)
        from fensu.rules.authoring._helpers.fact_identity import rust_file_identity

        self._record(
            kind="rust_file",
            query=path.value,
            answer="" if answer is None else rust_file_identity(value=answer),
        )
        return answer

    def observed(self, observer: Callable[[str, str, str], None]) -> RustWorkspaceFacts:
        """Return a fact view whose query answers are recorded for one invocation."""

        return RustWorkspaceFacts(
            schema_version=self.schema_version,
            parser_contract=self.parser_contract,
            _crate_values=self._crate_values,
            _file_values=self._file_values,
            _crates_by_identity=self._crates_by_identity,
            _files_by_path=self._files_by_path,
            _observe=observer,
        )

    def _record(self, *, kind: str, query: str, answer: str) -> None:
        if self._observe is not None:
            self._observe(kind, query, answer)


@dataclass(frozen=True, slots=True, order=True)
class WebImportBindingFact:
    """One local binding introduced by a static web import."""

    local_name: str
    imported_name: str


@dataclass(frozen=True, slots=True, order=True)
class WebImportFact:
    """One authored TypeScript, JavaScript, or Svelte script import."""

    specifier: str
    bindings: tuple[WebImportBindingFact, ...]
    type_only: bool
    namespace: bool
    location: SourceLocation
    target: File | None


@dataclass(frozen=True, slots=True, order=True)
class WebFunctionFact:
    """One parser-independent web function declaration."""

    name: str
    qualified_name: str
    exported: bool
    export_owner: str | None
    parameter_count: int
    parameters_annotated: bool
    return_type: str | None
    statement_count: int
    distinct_call_count: int
    local_count: int
    location: SourceLocation


@dataclass(frozen=True, slots=True, order=True)
class WebClassFact:
    """One parser-independent web class declaration."""

    name: str
    exported: bool
    error_class: bool
    location: SourceLocation


@dataclass(frozen=True, slots=True, order=True)
class WebModelFact:
    """One TypeScript interface or type-literal declaration."""

    name: str
    kind: WebModelKind
    exported: bool
    readonly_properties: bool
    readonly_shape: bool
    property_names: tuple[str, ...]
    location: SourceLocation


@dataclass(frozen=True, slots=True, order=True)
class WebCallFact:
    """One statically named call and its lexical owner."""

    name: str
    function_name: str | None
    ancestor_calls: tuple[str, ...]
    function_argument: bool
    returned_cleanup: bool
    location: SourceLocation


@dataclass(frozen=True, slots=True, order=True)
class WebBindingFact:
    """One top-level web binding declaration."""

    name: str
    initializer_call: str | None
    location: SourceLocation


@dataclass(frozen=True, slots=True, order=True)
class WebResourceFact:
    """One statically recognized external resource operation."""

    family: str
    binding_name: str | None
    ancestor_calls: tuple[str, ...]
    location: SourceLocation


@dataclass(frozen=True, slots=True, order=True)
class SvelteScriptFact:
    """One Svelte script block and its ownership context."""

    context: WebScriptContext
    location: SourceLocation


@dataclass(frozen=True, slots=True, order=True)
class SvelteRuneFact:
    """One statically recognized Svelte rune call."""

    name: str
    location: SourceLocation


@dataclass(frozen=True, slots=True, order=True)
class SvelteFileFacts:
    """Svelte-specific extensions kept separate from common web facts."""

    scripts: tuple[SvelteScriptFact, ...]
    module_runes: tuple[SvelteRuneFact, ...]
    has_component_markup: bool
    route: bool
    state_module: bool


@dataclass(frozen=True, slots=True, order=True)
class WebSyntaxHandle:
    """Stable byte range for an analyzer-owned web syntax fact."""

    file: File
    kind: WebSyntaxKind
    name: str | None
    start: int
    end: int
    location: SourceLocation


@dataclass(frozen=True, slots=True, order=True)
class WebFileFacts:
    """Owned immutable semantic facts for one discovered web source file."""

    file: File
    analyzer: AnalyzerId
    source_kind: WebSourceKind
    purpose: WebSourcePurpose
    module: str
    source_root: ProjectPath
    scope: ScopeName
    source: str
    parse_error: str | None
    imports: tuple[WebImportFact, ...]
    functions: tuple[WebFunctionFact, ...]
    classes: tuple[WebClassFact, ...]
    models: tuple[WebModelFact, ...]
    bindings: tuple[WebBindingFact, ...]
    calls: tuple[WebCallFact, ...]
    resources: tuple[WebResourceFact, ...]
    re_exports: tuple[SourceLocation, ...]
    public_export_count: int
    runtime_declaration_count: int
    syntax_handles: tuple[WebSyntaxHandle, ...]
    svelte: SvelteFileFacts | None

    def text(self, handle: WebSyntaxHandle) -> str:
        """Return authored UTF-8 text for one owned stable syntax handle."""

        from fensu.rules.authoring.exceptions import WebFactQueryError

        if handle.file != self.file or handle.start < 0 or handle.end < handle.start:
            raise WebFactQueryError("Web syntax handle does not belong to this file")
        encoded: bytes = self.source.encode("utf-8")
        if handle.end > len(encoded):
            raise WebFactQueryError("Web syntax handle exceeds its source file")
        try:
            return encoded[handle.start : handle.end].decode("utf-8")
        except UnicodeDecodeError as error:
            raise WebFactQueryError("Web syntax handle does not align to UTF-8 text") from error


@dataclass(frozen=True, slots=True)
class WebWorkspaceFacts:
    """Versioned requester-observed facts for one TypeScript or Svelte target."""

    schema_version: str
    parser_contract: str
    analyzer: AnalyzerId
    _file_values: tuple[WebFileFacts, ...] = field(repr=False)
    _files_by_path: Mapping[ProjectPath, WebFileFacts] = field(repr=False, compare=False)
    _observe: Callable[[str, str, str], None] | None = field(
        default=None, repr=False, compare=False
    )

    @property
    def files(self) -> tuple[WebFileFacts, ...]:
        """Return all discovered web files and observe the broad inventory."""

        from fensu.rules.authoring._helpers.fact_identity import web_file_identity

        self._record(
            kind="web_files",
            query=".",
            answer="\n".join(web_file_identity(value=item) for item in self._file_values),
        )
        return self._file_values

    def file(self, value: File | ProjectPath) -> WebFileFacts | None:
        """Return one focused selected web file."""

        path: ProjectPath = value.path if isinstance(value, File) else value
        if not isinstance(path, ProjectPath):
            from fensu.rules.authoring.exceptions import WebFactQueryTypeError

            raise WebFactQueryTypeError("Web file queries require a File or ProjectPath")
        answer: WebFileFacts | None = self._files_by_path.get(path)
        from fensu.rules.authoring._helpers.fact_identity import web_file_identity

        self._record(
            kind="web_file",
            query=path.value,
            answer="" if answer is None else web_file_identity(value=answer),
        )
        return answer

    def observed(self, observer: Callable[[str, str, str], None]) -> WebWorkspaceFacts:
        """Return a fact view whose query answers are recorded for one invocation."""

        return WebWorkspaceFacts(
            schema_version=self.schema_version,
            parser_contract=self.parser_contract,
            analyzer=self.analyzer,
            _file_values=self._file_values,
            _files_by_path=self._files_by_path,
            _observe=observer,
        )

    def _record(self, *, kind: str, query: str, answer: str) -> None:
        if self._observe is not None:
            self._observe(kind, query, answer)


@dataclass(frozen=True, slots=True, eq=False)
class RuleOption[T]:
    """One immutable typed option declaration owned by a rule."""

    name: str
    kind: RuleOptionKind
    default: T | Missing = MISSING
    required: bool = False
    description: str | None = None
    choices: tuple[str, ...] | None = None
    minimum: int | None = None
    maximum: int | None = None
    minimum_items: int | None = None

    def __post_init__(self) -> None:
        """Reject invalid declarations and defaults at authoring time."""

        from fensu.rules.authoring._helpers.options import validate_option_declaration

        validate_option_declaration(option=self)

    @classmethod
    def boolean(
        cls,
        *,
        name: str,
        default: bool | Missing = MISSING,
        required: bool = False,
        description: str | None = None,
    ) -> RuleOption[bool]:
        """Declare a boolean rule option."""

        return RuleOption(
            name=name,
            kind=RuleOptionKind.BOOLEAN,
            default=default,
            required=required,
            description=description,
        )

    @classmethod
    def integer(
        cls,
        *,
        name: str,
        default: int | Missing = MISSING,
        required: bool = False,
        minimum: int | None = None,
        maximum: int | None = None,
        description: str | None = None,
    ) -> RuleOption[int]:
        """Declare a signed 64-bit integer rule option."""

        return RuleOption(
            name=name,
            kind=RuleOptionKind.INTEGER,
            default=default,
            required=required,
            description=description,
            minimum=minimum,
            maximum=maximum,
        )

    @classmethod
    def string(
        cls,
        *,
        name: str,
        default: str | Missing = MISSING,
        required: bool = False,
        choices: tuple[str, ...] | None = None,
        description: str | None = None,
    ) -> RuleOption[str]:
        """Declare a string rule option."""

        return RuleOption(
            name=name,
            kind=RuleOptionKind.STRING,
            default=default,
            required=required,
            description=description,
            choices=choices,
        )

    @classmethod
    def string_list(
        cls,
        *,
        name: str,
        default: tuple[str, ...] | Missing = MISSING,
        required: bool = False,
        minimum_items: int | None = None,
        description: str | None = None,
    ) -> RuleOption[tuple[str, ...]]:
        """Declare an immutable string-list rule option."""

        return RuleOption(
            name=name,
            kind=RuleOptionKind.STRING_LIST,
            default=default,
            required=required,
            description=description,
            minimum_items=minimum_items,
        )

    @classmethod
    def integer_list(
        cls,
        *,
        name: str,
        default: tuple[int, ...] | Missing = MISSING,
        required: bool = False,
        minimum_items: int | None = None,
        description: str | None = None,
    ) -> RuleOption[tuple[int, ...]]:
        """Declare an immutable integer-list rule option."""

        return RuleOption(
            name=name,
            kind=RuleOptionKind.INTEGER_LIST,
            default=default,
            required=required,
            description=description,
            minimum_items=minimum_items,
        )


@dataclass(frozen=True, slots=True)
class RuleConstraint:
    """One immutable exhaustive value set enforced by a rule."""

    name: str
    description: str
    values: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RuleLimit:
    """One immutable numeric cardinality enforced by a rule."""

    name: str
    description: str
    value: int


@dataclass(frozen=True, slots=True)
class Fault:
    """A single rule finding against a file."""

    code: str
    path: Path
    message: str
    line: int | None = None
    column: int | None = None
    remediation: str | None = None

    def format(self, root: Path) -> str:
        """Render the fault as `path:line:col: CODE message` relative to root."""

        try:
            relative_path: Path = self.path.relative_to(root)
        except ValueError:
            relative_path = self.path
        line_text: str = str(self.line) if self.line is not None else "-"
        column_text: str = str(self.column) if self.column is not None else "-"
        return f"{relative_path.as_posix()}:{line_text}:{column_text}: {self.code} {self.message}"


@dataclass(frozen=True, slots=True)
class RuleSpec:
    """The compiled, uniform representation of a core or custom rule."""

    code: str
    family: Family
    slug: str
    message: str
    check: RuleCheck | None = None
    remediation: str | None = None
    severity: Severity = Severity.ERROR
    kind: RuleKind = RuleKind.CORE
    pack: str | None = None
    alias_of: str | None = None
    implementation_code: str | None = None
    source: str | None = None
    enabled_by_default: bool = True
    analyzers: tuple[AnalyzerId, ...] = (AnalyzerId.PYTHON,)
    cacheable: bool | None = None
    uses_module: bool = False
    execution_owner: ExecutionOwner = ExecutionOwner.FILE
    subject_kind: RuleSubjectKind = RuleSubjectKind.LEGACY
    subject_parameter: str | None = None
    context_parameter: str | None = None
    options: tuple[RuleOption[object], ...] = ()
    constraints: tuple[RuleConstraint, ...] = ()
    thresholds: tuple[Threshold, ...] = ()
    contract_behaviors: tuple[str, ...] = ()
    configuration_inputs: tuple[str, ...] = ()
    limits: tuple[RuleLimit, ...] = ()


@dataclass(frozen=True, slots=True)
class CustomRuleRegistration:
    """One configured custom rule tied to its repository declaration owner."""

    rule: RuleSpec
    source_path: Path
    module_name: str
    function_name: str
    declaration_line: int
    declaration_column: int
    owner_key: str
