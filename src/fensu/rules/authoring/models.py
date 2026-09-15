"""Authoring structured runtime models: the fault and the compiled rule spec."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

from fensu.analysis.models import SourceLocation
from fensu.config.types import AnalyzerId
from fensu.discovery.types import ScopeName
from fensu.rules.authoring.constants import MISSING, PROJECT_ROOT
from fensu.rules.authoring.exceptions import (
    ArchitectureGraphQueryError,
    ArchitectureGraphQueryTypeError,
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
    Severity,
    SourceKind,
    Threshold,
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
    """Stable architecture identity and ownership of one discovered Python module."""

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
    """Resolved static imports from authoritative discovered Python sources."""

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
                f"graph path is not a discovered Python module: {path}"
            )
        return path

    def _record(self, *, kind: str, path: ProjectPath, answer: str) -> None:
        if self._observe is not None:
            self._observe(kind, path, answer)


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
