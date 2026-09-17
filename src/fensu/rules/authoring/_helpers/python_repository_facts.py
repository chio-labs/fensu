"""Build target-local Python facts, tree, and graph from a native snapshot."""

from __future__ import annotations

import ast
from collections.abc import Mapping
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import cast

from fensu.analysis.main.build import build_analysis
from fensu.analysis.models import ImportAliasFact, ImportFact
from fensu.analysis.types import Analysis, FactAnalysis
from fensu.config.constants import MINIMUM_OWNERSHIP_DEPTH
from fensu.config.exceptions import ConfigError
from fensu.config.types import AnalyzerId
from fensu.discovery.constants import (
    INIT_MODULE_FILE_NAME,
    ROLE_DIRECTORY_TO_NAME,
    ROLE_FILE_TO_NAME,
    STRUCTURAL_MODULE_PART_TO_NAME,
)
from fensu.discovery.types import RoleName, ScopeName
from fensu.evaluation.constants import (
    ARCHITECTURE_PUBLIC_ROLES,
    PYTHON_REPOSITORY_FACT_FIELDS,
    PYTHON_REPOSITORY_FACT_SCHEMA_VERSION,
)
from fensu.rules.authoring.constants import PROJECT_ROOT
from fensu.rules.authoring.main.architecture_graph import architecture_graph
from fensu.rules.authoring.models import (
    ArchitectureGraph,
    AuthoredImport,
    File,
    FilePosition,
    ImportEdge,
    ModuleNode,
    ProjectPath,
    ProjectTree,
    PythonFileFacts,
    PythonWorkspaceFacts,
)
from fensu.rules.authoring.types import ImportResolution, ModuleVisibility, SourceKind

_INIT_STEM: str = INIT_MODULE_FILE_NAME.removesuffix(".py")


def build_python_repository_facts(
    *, payload: object, subjects: object
) -> tuple[PythonWorkspaceFacts, ProjectTree, ArchitectureGraph]:
    """Decode one Python target snapshot into public immutable query surfaces."""

    envelope: dict[str, object] = _mapping(value=payload, name="Python target facts")
    if set(envelope) != PYTHON_REPOSITORY_FACT_FIELDS:
        raise ConfigError("Python target facts contain incompatible fields.")
    if envelope["schema_version"] != PYTHON_REPOSITORY_FACT_SCHEMA_VERSION:
        raise ConfigError("Python target facts use an unsupported schema.")
    parser_contract: str = _string(value=envelope["parser_contract"], name="Python parser contract")
    ownership_depth: int = _ownership_depth(envelope["ownership_depth"])
    files: list[object] = _sequence(value=envelope["files"], name="Python target files")
    values: list[PythonFileFacts] = []
    metadata: dict[ProjectPath, dict[str, object]] = {}
    for item in files:
        fact, details = _python_file(payload=item)
        values.append(fact)
        metadata[fact.file.path] = details
    values.sort(key=lambda item: item.file.path.value)
    workspace: PythonWorkspaceFacts = PythonWorkspaceFacts(
        schema_version=PYTHON_REPOSITORY_FACT_SCHEMA_VERSION,
        parser_contract=parser_contract,
        _file_values=tuple(values),
        _files_by_path=MappingProxyType({item.file.path: item for item in values}),
    )
    tree: ProjectTree = _project_tree(
        subjects=subjects,
        metadata=metadata,
        ownership_depth=ownership_depth,
    )
    graph: ArchitectureGraph = _architecture_graph(workspace=workspace, tree=tree)
    return workspace, tree, graph


def _python_file(*, payload: object) -> tuple[PythonFileFacts, dict[str, object]]:
    value: dict[str, object] = _mapping(value=payload, name="Python target file")
    expected: set[str] = {
        "path",
        "scope",
        "scope_root",
        "relative_parts",
        "purpose",
        "source",
    }
    if set(value) != expected:
        raise ConfigError("Python target file contains incompatible fields.")
    path: ProjectPath = ProjectPath(_string(value=value["path"], name="Python file path"))
    source: str = _string(value=value["source"], name="Python source")
    try:
        module: ast.Module = ast.parse(source, filename=path.value)
    except SyntaxError as error:
        raise ConfigError(
            f"Could not parse repository-rule Python source {path}: {error.msg}"
        ) from error
    analysis: Analysis = build_analysis(path=Path(path.value), source=source, module=module)
    return (
        PythonFileFacts(
            file=File(path),
            source=source,
            facts=analysis.facts,
            text=analysis.text,
            syntax=analysis.syntax,
            relations=analysis.relations,
        ),
        {
            "scope": _string(value=value["scope"], name="Python file scope"),
            "scope_root": _string(value=value["scope_root"], name="Python scope root"),
            "relative_parts": tuple(
                _string(value=part, name="Python relative path part")
                for part in _sequence(
                    value=value["relative_parts"], name="Python relative path parts"
                )
            ),
            "purpose": _string(value=value["purpose"], name="Python source purpose"),
        },
    )


def _project_tree(
    *,
    subjects: object,
    metadata: Mapping[ProjectPath, dict[str, object]],
    ownership_depth: int,
) -> ProjectTree:
    subject_values: list[object] = _sequence(value=subjects, name="Python target subjects")
    positions: dict[ProjectPath, FilePosition] = {}
    for subject in subject_values:
        value: dict[str, object] = _mapping(value=subject, name="Python target subject")
        path: ProjectPath = ProjectPath(_string(value=value.get("path"), name="subject path"))
        details: dict[str, object] | None = metadata.get(path)
        if details is None:
            raise ConfigError(f"Python target subject has no facts: {path}")
        relative_parts: tuple[str, ...] = cast("tuple[str, ...]", details["relative_parts"])
        scope_root: ProjectPath = ProjectPath(cast(str, details["scope_root"]))
        module, package = _module_identity(scope_root=scope_root, relative_parts=relative_parts)
        directories: tuple[str, ...] = relative_parts[:-1]
        role_index: int | None = next(
            (index for index, part in enumerate(directories) if part in ROLE_DIRECTORY_TO_NAME),
            None,
        )
        role: str | None = (
            ROLE_FILE_TO_NAME.get(relative_parts[-1])
            if role_index is None
            else ROLE_DIRECTORY_TO_NAME[directories[role_index]]
        )
        owner_end: int = len(directories) if role_index is None else role_index
        grouping_depth: int = (
            ownership_depth - 2 if ScopeName(cast(str, details["scope"])) is ScopeName.ROOT else 0
        )
        domain_parts: tuple[str, ...] = directories[grouping_depth:owner_end]
        first_runtime_role: str | None = next(
            (
                STRUCTURAL_MODULE_PART_TO_NAME[part]
                for part in directories
                if part in STRUCTURAL_MODULE_PART_TO_NAME
            ),
            None,
        )
        positions[path] = FilePosition(
            path=path,
            analyzer=AnalyzerId.PYTHON,
            source_kind=SourceKind.PYTHON_MODULE,
            scope=ScopeName(cast(str, details["scope"])),
            scope_root=scope_root,
            module=module,
            package=package,
            domain_parts=domain_parts,
            role=role,
            role_depth=(
                None
                if role is None
                else 0
                if role_index is None
                else len(directories) - role_index - 1
            ),
            is_entry_module=(
                first_runtime_role == RoleName.MAIN and relative_parts[-1] != INIT_MODULE_FILE_NAME
            ),
            is_main_module=first_runtime_role == RoleName.MAIN,
        )
    ordered_files: tuple[File, ...] = tuple(File(path) for path in sorted(positions))
    paths: set[ProjectPath] = {_root_path()}
    for path in positions:
        current: PurePosixPath = PurePosixPath(path.value)
        paths.add(path)
        for parent in current.parents:
            paths.add(
                _root_path()
                if parent.as_posix() == PROJECT_ROOT
                else ProjectPath(parent.as_posix())
            )
    ordered_paths: tuple[ProjectPath, ...] = tuple(sorted(paths))
    children: dict[ProjectPath, list[ProjectPath]] = {path: [] for path in ordered_paths}
    for path in ordered_paths:
        if path.value == PROJECT_ROOT:
            continue
        parent_text: str = PurePosixPath(path.value).parent.as_posix()
        parent: ProjectPath = (
            _root_path() if parent_text == PROJECT_ROOT else ProjectPath(parent_text)
        )
        children[parent].append(path)
    return ProjectTree(
        _paths=ordered_paths,
        _files=ordered_files,
        _children=MappingProxyType({key: tuple(sorted(items)) for key, items in children.items()}),
        _positions=MappingProxyType(positions),
    )


def _architecture_graph(*, workspace: PythonWorkspaceFacts, tree: ProjectTree) -> ArchitectureGraph:
    nodes: list[ModuleNode] = []
    analyses: dict[ProjectPath, FactAnalysis] = {}
    for item in workspace._file_values:  # noqa: SLF001
        position: FilePosition | None = tree.position(item.file.path)
        if position is None or position.module is None:
            continue
        nodes.append(
            ModuleNode(
                file=item.file,
                analyzer=AnalyzerId.PYTHON,
                source_kind=SourceKind.PYTHON_MODULE,
                module=position.module,
                scope=position.scope,
                scope_root=position.scope_root,
                package=position.package or "",
                domain_parts=position.domain_parts,
                role=position.role,
                visibility=_visibility(
                    module=position.module,
                    package=position.package or "",
                    role=position.role,
                ),
            )
        )
        analyses[item.file.path] = item.facts
    unique: dict[str, ModuleNode] = {}
    candidates: dict[str, list[ModuleNode]] = {}
    for node in nodes:
        candidates.setdefault(node.module, []).append(node)
    for module, values in candidates.items():
        if len(values) == 1:
            unique[module] = values[0]
    imports: dict[ProjectPath, tuple[ImportEdge, ...]] = {}
    for node in nodes:
        edges: list[ImportEdge] = []
        for fact in analyses[node.file.path].references().imports:
            for alias in fact.aliases:
                edges.append(_edge(source=node, fact=fact, alias=alias, modules=unique))
        imports[node.file.path] = tuple(edges)
    return architecture_graph(nodes=tuple(nodes), imports=imports)


def _edge(
    *,
    source: ModuleNode,
    fact: ImportFact,
    alias: ImportAliasFact,
    modules: Mapping[str, ModuleNode],
) -> ImportEdge:
    candidates: tuple[tuple[str, ...], ...] = _import_candidates(
        source=source, fact=fact, alias=alias
    )
    target: ModuleNode | None = next(
        (modules[name] for parts in candidates if (name := ".".join(parts)) in modules), None
    )
    return ImportEdge(
        source=source,
        authored=AuthoredImport(
            module_parts=fact.module_parts,
            imported_parts=alias.imported_parts,
            bound_name=alias.bound_name,
            relative_level=fact.relative_level,
            from_import=fact.from_import,
        ),
        module=(
            target.module
            if target is not None
            else ".".join(candidates[-1])
            if candidates
            else None
        ),
        location=fact.location,
        status=ImportResolution.RESOLVED if target is not None else ImportResolution.UNRESOLVED,
        target=target,
    )


def _import_candidates(
    *, source: ModuleNode, fact: ImportFact, alias: ImportAliasFact
) -> tuple[tuple[str, ...], ...]:
    if not fact.from_import:
        return (alias.imported_parts,)
    package: tuple[str, ...] = tuple(source.package.split(".")) if source.package else ()
    if fact.relative_level:
        parent_count: int = fact.relative_level - 1
        if parent_count > len(package):
            return ()
        base: tuple[str, ...] = (*package[: len(package) - parent_count], *fact.module_parts)
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


def _module_identity(
    *, scope_root: ProjectPath, relative_parts: tuple[str, ...]
) -> tuple[str, str]:
    stem: str = PurePosixPath(relative_parts[-1]).stem
    parts: tuple[str, ...] = (scope_root.name, *relative_parts[:-1], stem)
    if parts[-1] == _INIT_STEM:
        parts = parts[:-1]
    package_parts: tuple[str, ...] = parts if stem == _INIT_STEM else parts[:-1]
    return ".".join(parts), ".".join(package_parts)


def _visibility(*, module: str, package: str, role: str | None) -> ModuleVisibility:
    private: bool = any(part.startswith("_") and part != _INIT_STEM for part in module.split("."))
    return (
        ModuleVisibility.INTERNAL
        if private or module != package and role not in ARCHITECTURE_PUBLIC_ROLES
        else ModuleVisibility.PUBLIC
    )


def _mapping(*, value: object, name: str) -> dict[str, object]:
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise ConfigError(f"{name} must be an object.")
    return cast("dict[str, object]", value)


def _sequence(*, value: object, name: str) -> list[object]:
    if not isinstance(value, list):
        raise ConfigError(f"{name} must be an array.")
    return cast("list[object]", value)


def _string(*, value: object, name: str) -> str:
    if not isinstance(value, str):
        raise ConfigError(f"{name} must be a string.")
    return value


def _ownership_depth(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < MINIMUM_OWNERSHIP_DEPTH:
        raise ConfigError(
            f"Python ownership depth must be an integer of at least {MINIMUM_OWNERSHIP_DEPTH}."
        )
    return value


def _root_path() -> ProjectPath:
    value: ProjectPath = object.__new__(ProjectPath)
    object.__setattr__(value, "value", ".")
    return value
