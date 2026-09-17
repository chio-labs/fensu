"""Build immutable public web facts from the native host payload."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import cast

from fensu.analysis.models import SourceLocation
from fensu.config.types import AnalyzerId
from fensu.discovery.types import RoleName, ScopeName
from fensu.rules.authoring._helpers.project_tree import root_path
from fensu.rules.authoring.constants import PROJECT_ROOT
from fensu.rules.authoring.exceptions import WebFactProtocolError
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
    SvelteFileFacts,
    SvelteRuneFact,
    SvelteScriptFact,
    WebBindingFact,
    WebCallFact,
    WebClassFact,
    WebFileFacts,
    WebFunctionFact,
    WebImportBindingFact,
    WebImportFact,
    WebModelFact,
    WebResourceFact,
    WebSyntaxHandle,
    WebWorkspaceFacts,
)
from fensu.rules.authoring.types import (
    ImportResolution,
    ModuleVisibility,
    SourceKind,
    WebModelKind,
    WebScriptContext,
    WebSourceKind,
    WebSourcePurpose,
    WebSyntaxKind,
)

_LIB_DIRECTORY: str = "lib"
_WEB_ROLES: frozenset[str] = frozenset(
    {
        "_adapters",
        "_api",
        "_components",
        "_helpers",
        "_resources",
        "_state",
        "_test",
        "api",
        "components",
        "constants",
        "errors",
        "helpers",
        "main",
        "models",
        "resources",
        "schemas",
        "state",
        "test",
        "types",
    }
)
_PATH_SEPARATOR: str = "/"
_CURRENT_PATH_PART: str = "."
_EMPTY_PATH_PART: str = ""
_PARENT_PATH_PART: str = ".."
_RELATIVE_CURRENT_PREFIX: str = "./"
_RELATIVE_PARENT_PREFIX: str = "../"


def web_workspace_facts(*, payload: object) -> WebWorkspaceFacts:
    """Decode one trusted versioned native web fact payload."""

    value: dict[str, object] = _mapping(value=payload, name="Web facts")
    _keys(
        value=value,
        expected={"schema_version", "parser_contract", "analyzer", "files"},
        name="Web facts",
    )
    analyzer: AnalyzerId = AnalyzerId(_string(value=value["analyzer"], name="Web analyzer"))
    if analyzer not in {AnalyzerId.TYPESCRIPT, AnalyzerId.SVELTE}:
        raise WebFactProtocolError("Web facts require a TypeScript or Svelte analyzer")
    files: tuple[WebFileFacts, ...] = tuple(
        _file(payload=item, analyzer=analyzer)
        for item in _sequence(value=value["files"], name="Web files")
    )
    if len({item.file.path for item in files}) != len(files):
        raise WebFactProtocolError("Web facts contain duplicate file paths")
    return WebWorkspaceFacts(
        schema_version=_string(value=value["schema_version"], name="Web fact schema"),
        parser_contract=_string(value=value["parser_contract"], name="Web parser contract"),
        analyzer=analyzer,
        _file_values=files,
        _files_by_path=MappingProxyType({item.file.path: item for item in files}),
    )


def web_project_tree(
    *, subjects: object, workspace: WebWorkspaceFacts, ownership_roots: tuple[str, ...] = ()
) -> ProjectTree:
    """Build a deterministic common tree from authoritative direct web subjects."""

    del ownership_roots

    facts_by_path: dict[ProjectPath, WebFileFacts] = {
        item.file.path: item for item in workspace._file_values
    }
    positions: dict[ProjectPath, FilePosition] = {}
    for raw_subject in _sequence(value=subjects, name="Web subjects"):
        subject: dict[str, object] = _mapping(value=raw_subject, name="Web subject")
        _keys(
            value=subject,
            expected={
                "path",
                "scope",
                "scope_root",
                "relative_parts",
                "ownership_root",
                "ownership_root_declaration",
                "ownership_relative_parts",
            },
            name="Web subject",
        )
        path: ProjectPath = ProjectPath(_string(value=subject["path"], name="Web subject path"))
        fact: WebFileFacts | None = facts_by_path.get(path)
        if fact is None:
            raise WebFactProtocolError(f"Web subject has no matching facts: {path}")
        relative_parts: tuple[str, ...] = _strings(
            value=subject["relative_parts"], name="Web relative parts"
        )
        directories: tuple[str, ...] = relative_parts[:-1]
        role_index: int | None = next(
            (index for index, part in enumerate(directories) if part in _WEB_ROLES), None
        )
        role: str | None = None if role_index is None else directories[role_index]
        scope_root_text: str = _string(value=subject["scope_root"], name="Web scope root")
        scope_root: ProjectPath = (
            root_path() if scope_root_text == PROJECT_ROOT else ProjectPath(scope_root_text)
        )
        ownership_relative_parts: tuple[str, ...] = _strings(
            value=subject["ownership_relative_parts"], name="Web ownership-relative parts"
        )
        ownership_directories: tuple[str, ...] = ownership_relative_parts[:-1]
        ownership_role_index: int | None = next(
            (index for index, part in enumerate(ownership_directories) if part in _WEB_ROLES),
            None,
        )
        positions[path] = FilePosition(
            path=path,
            analyzer=workspace.analyzer,
            source_kind=_position_source_kind(fact.source_kind),
            scope=ScopeName(_string(value=subject["scope"], name="Web scope")),
            scope_root=scope_root,
            module=fact.module,
            package=_package(module=fact.module),
            domain_parts=(
                ownership_directories
                if ownership_role_index is None
                else ownership_directories[:ownership_role_index]
            ),
            role=role,
            role_depth=None if role_index is None else len(directories) - role_index - 1,
            is_entry_module=relative_parts[-1].startswith("+") if relative_parts else False,
            is_main_module=role == RoleName.MAIN,
            ownership_root=(
                None
                if subject["ownership_root"] is None
                else ProjectPath(_string(value=subject["ownership_root"], name="ownership root"))
            ),
            ownership_root_declaration=(
                None
                if subject["ownership_root_declaration"] is None
                else _string(
                    value=subject["ownership_root_declaration"],
                    name="ownership root declaration",
                )
            ),
            ownership_relative_parts=ownership_relative_parts,
        )
    all_paths: set[ProjectPath] = set(positions)
    for file_path in tuple(all_paths):
        for depth in range(1, len(file_path.parts)):
            all_paths.add(ProjectPath(PurePosixPath(*file_path.parts[:depth]).as_posix()))
    ordered_paths: tuple[ProjectPath, ...] = tuple(sorted(all_paths, key=lambda item: item.value))
    children: dict[ProjectPath, list[ProjectPath]] = {}
    for path in ordered_paths:
        parent: ProjectPath = root_path() if len(path.parts) == 1 else path.parent
        children.setdefault(parent, []).append(path)
    return ProjectTree(
        _paths=ordered_paths,
        _files=tuple(File(path=path) for path in sorted(positions, key=lambda item: item.value)),
        _children=MappingProxyType({key: tuple(value) for key, value in children.items()}),
        _positions=MappingProxyType(positions),
    )


def web_architecture_graph(
    *,
    workspace: WebWorkspaceFacts,
    ownership_roots: tuple[str, ...] = (),
    subjects: object | None = None,
) -> ArchitectureGraph:
    """Build the common graph from native-resolved web import targets."""

    subject_ownership: dict[ProjectPath, tuple[ProjectPath | None, tuple[str, ...]]] = (
        {} if subjects is None else _subject_ownership(subjects=subjects)
    )
    nodes: tuple[ModuleNode, ...] = tuple(
        _node(
            value=item,
            ownership_roots=ownership_roots,
            subject_ownership=subject_ownership.get(item.file.path),
        )
        for item in workspace._file_values
    )
    nodes_by_path: dict[ProjectPath, ModuleNode] = {item.file.path: item for item in nodes}
    imports: dict[ProjectPath, tuple[ImportEdge, ...]] = {}
    for facts in workspace._file_values:
        source: ModuleNode = nodes_by_path[facts.file.path]
        imports[facts.file.path] = tuple(
            _edge(source=source, imported=item, nodes=nodes_by_path) for item in facts.imports
        )
    return architecture_graph(nodes=nodes, imports=imports)


def _file(*, payload: object, analyzer: AnalyzerId) -> WebFileFacts:
    value: dict[str, object] = _mapping(value=payload, name="Web file")
    _keys(
        value=value,
        expected={
            "path",
            "source_kind",
            "purpose",
            "module",
            "source_root",
            "scope",
            "source",
            "parse_error",
            "imports",
            "functions",
            "classes",
            "models",
            "bindings",
            "calls",
            "resources",
            "re_exports",
            "public_export_count",
            "runtime_declaration_count",
            "syntax_handles",
            "svelte",
        },
        name="Web file",
    )
    path: ProjectPath = ProjectPath(_string(value=value["path"], name="Web file path"))
    source_root: ProjectPath = _project_path(value=value["source_root"], name="Web source root")
    if source_root.parts and path.parts[: len(source_root.parts)] != source_root.parts:
        raise WebFactProtocolError(f"Web file {path} is outside its source root {source_root}")
    parse_error: object = value["parse_error"]
    svelte: object = value["svelte"]
    return WebFileFacts(
        file=File(path=path),
        analyzer=analyzer,
        source_kind=WebSourceKind(_string(value=value["source_kind"], name="Web source kind")),
        purpose=WebSourcePurpose(_string(value=value["purpose"], name="Web source purpose")),
        module=_string(value=value["module"], name="Web module"),
        source_root=source_root,
        scope=ScopeName(_string(value=value["scope"], name="Web scope")),
        source=_string(value=value["source"], name="Web source"),
        parse_error=(
            None if parse_error is None else _string(value=parse_error, name="Web parse error")
        ),
        imports=tuple(
            _import(payload=item, path=path)
            for item in _sequence(value=value["imports"], name="Web imports")
        ),
        functions=tuple(
            _function(payload=item, path=path)
            for item in _sequence(value=value["functions"], name="Web functions")
        ),
        classes=tuple(
            _class(payload=item, path=path)
            for item in _sequence(value=value["classes"], name="Web classes")
        ),
        models=tuple(
            _model(payload=item, path=path)
            for item in _sequence(value=value["models"], name="Web models")
        ),
        bindings=tuple(
            _binding_declaration(payload=item, path=path)
            for item in _sequence(value=value["bindings"], name="Web bindings")
        ),
        calls=tuple(
            _call(payload=item, path=path)
            for item in _sequence(value=value["calls"], name="Web calls")
        ),
        resources=tuple(
            _resource(payload=item, path=path)
            for item in _sequence(value=value["resources"], name="Web resources")
        ),
        re_exports=tuple(
            _location(payload=item, expected_path=path)
            for item in _sequence(value=value["re_exports"], name="Web re-exports")
        ),
        public_export_count=_integer(
            value=value["public_export_count"], name="Web public export count"
        ),
        runtime_declaration_count=_integer(
            value=value["runtime_declaration_count"], name="Web runtime declaration count"
        ),
        syntax_handles=tuple(
            _syntax_handle(payload=item, path=path)
            for item in _sequence(value=value["syntax_handles"], name="Web syntax handles")
        ),
        svelte=None if svelte is None else _svelte(payload=svelte, path=path),
    )


def _import(*, payload: object, path: ProjectPath) -> WebImportFact:
    value: dict[str, object] = _mapping(value=payload, name="Web import")
    _keys(
        value=value,
        expected={"specifier", "bindings", "type_only", "namespace", "target_path", "location"},
        name="Web import",
    )
    target: object = value["target_path"]
    return WebImportFact(
        specifier=_string(value=value["specifier"], name="Web import specifier"),
        bindings=tuple(
            _binding(payload=item)
            for item in _sequence(value=value["bindings"], name="Web import bindings")
        ),
        type_only=_boolean(value=value["type_only"], name="Web type-only import"),
        namespace=_boolean(value=value["namespace"], name="Web namespace import"),
        location=_location(payload=value["location"], expected_path=path),
        target=(
            None
            if target is None
            else File(path=ProjectPath(_string(value=target, name="Web import target")))
        ),
    )


def _binding(*, payload: object) -> WebImportBindingFact:
    value: dict[str, object] = _mapping(value=payload, name="Web import binding")
    _keys(value=value, expected={"local_name", "imported_name"}, name="Web import binding")
    return WebImportBindingFact(
        local_name=_string(value=value["local_name"], name="Web local import name"),
        imported_name=_string(value=value["imported_name"], name="Web imported name"),
    )


def _function(*, payload: object, path: ProjectPath) -> WebFunctionFact:
    value: dict[str, object] = _mapping(value=payload, name="Web function")
    _keys(
        value=value,
        expected={
            "name",
            "qualified_name",
            "exported",
            "export_owner",
            "parameter_count",
            "parameters_annotated",
            "return_type",
            "statement_count",
            "distinct_call_count",
            "local_count",
            "location",
        },
        name="Web function",
    )
    owner: object = value["export_owner"]
    return_type: object = value["return_type"]
    return WebFunctionFact(
        name=_string(value=value["name"], name="Web function name"),
        qualified_name=_string(value=value["qualified_name"], name="Web qualified function"),
        exported=_boolean(value=value["exported"], name="Web function export"),
        export_owner=None if owner is None else _string(value=owner, name="Web export owner"),
        parameter_count=_integer(value=value["parameter_count"], name="Web parameter count"),
        parameters_annotated=_boolean(
            value=value["parameters_annotated"], name="Web parameter annotations"
        ),
        return_type=(
            None
            if return_type is None
            else _string(value=return_type, name="Web function return type")
        ),
        statement_count=_integer(value=value["statement_count"], name="Web statement count"),
        distinct_call_count=_integer(
            value=value["distinct_call_count"], name="Web distinct call count"
        ),
        local_count=_integer(value=value["local_count"], name="Web local count"),
        location=_location(payload=value["location"], expected_path=path),
    )


def _class(*, payload: object, path: ProjectPath) -> WebClassFact:
    value: dict[str, object] = _mapping(value=payload, name="Web class")
    _keys(value=value, expected={"name", "exported", "error_class", "location"}, name="Web class")
    return WebClassFact(
        name=_string(value=value["name"], name="Web class name"),
        exported=_boolean(value=value["exported"], name="Web class export"),
        error_class=_boolean(value=value["error_class"], name="Web error class"),
        location=_location(payload=value["location"], expected_path=path),
    )


def _model(*, payload: object, path: ProjectPath) -> WebModelFact:
    value: dict[str, object] = _mapping(value=payload, name="Web model")
    _keys(
        value=value,
        expected={
            "name",
            "kind",
            "exported",
            "readonly_properties",
            "readonly_shape",
            "property_names",
            "location",
        },
        name="Web model",
    )
    return WebModelFact(
        name=_string(value=value["name"], name="Web model name"),
        kind=WebModelKind(_string(value=value["kind"], name="Web model kind")),
        exported=_boolean(value=value["exported"], name="Web model export"),
        readonly_properties=_boolean(
            value=value["readonly_properties"], name="Web readonly properties"
        ),
        readonly_shape=_boolean(value=value["readonly_shape"], name="Web readonly shape"),
        property_names=_strings(value=value["property_names"], name="Web property names"),
        location=_location(payload=value["location"], expected_path=path),
    )


def _call(*, payload: object, path: ProjectPath) -> WebCallFact:
    value: dict[str, object] = _mapping(value=payload, name="Web call")
    _keys(
        value=value,
        expected={
            "name",
            "function_name",
            "ancestor_calls",
            "function_argument",
            "returned_cleanup",
            "location",
        },
        name="Web call",
    )
    function: object = value["function_name"]
    return WebCallFact(
        name=_string(value=value["name"], name="Web call name"),
        function_name=(
            None if function is None else _string(value=function, name="Web call function")
        ),
        ancestor_calls=_strings(value=value["ancestor_calls"], name="Web ancestor calls"),
        function_argument=_boolean(value=value["function_argument"], name="Web call argument"),
        returned_cleanup=_boolean(value=value["returned_cleanup"], name="Web cleanup return"),
        location=_location(payload=value["location"], expected_path=path),
    )


def _binding_declaration(*, payload: object, path: ProjectPath) -> WebBindingFact:
    value: dict[str, object] = _mapping(value=payload, name="Web binding")
    _keys(
        value=value,
        expected={"name", "initializer_call", "location"},
        name="Web binding",
    )
    initializer: object = value["initializer_call"]
    return WebBindingFact(
        name=_string(value=value["name"], name="Web binding name"),
        initializer_call=(
            None
            if initializer is None
            else _string(value=initializer, name="Web binding initializer")
        ),
        location=_location(payload=value["location"], expected_path=path),
    )


def _resource(*, payload: object, path: ProjectPath) -> WebResourceFact:
    value: dict[str, object] = _mapping(value=payload, name="Web resource")
    _keys(
        value=value,
        expected={"family", "binding_name", "ancestor_calls", "location"},
        name="Web resource",
    )
    binding: object = value["binding_name"]
    return WebResourceFact(
        family=_string(value=value["family"], name="Web resource family"),
        binding_name=(
            None if binding is None else _string(value=binding, name="Web resource binding")
        ),
        ancestor_calls=_strings(value=value["ancestor_calls"], name="Web resource ancestors"),
        location=_location(payload=value["location"], expected_path=path),
    )


def _svelte(*, payload: object, path: ProjectPath) -> SvelteFileFacts:
    value: dict[str, object] = _mapping(value=payload, name="Svelte facts")
    _keys(
        value=value,
        expected={"scripts", "module_runes", "has_component_markup", "route", "state_module"},
        name="Svelte facts",
    )
    return SvelteFileFacts(
        scripts=tuple(
            _svelte_script(payload=item, path=path)
            for item in _sequence(value=value["scripts"], name="Svelte scripts")
        ),
        module_runes=tuple(
            _svelte_rune(payload=item, path=path)
            for item in _sequence(value=value["module_runes"], name="Svelte runes")
        ),
        has_component_markup=_boolean(
            value=value["has_component_markup"], name="Svelte component markup"
        ),
        route=_boolean(value=value["route"], name="Svelte route"),
        state_module=_boolean(value=value["state_module"], name="Svelte state module"),
    )


def _svelte_script(*, payload: object, path: ProjectPath) -> SvelteScriptFact:
    value: dict[str, object] = _mapping(value=payload, name="Svelte script")
    _keys(value=value, expected={"context", "location"}, name="Svelte script")
    return SvelteScriptFact(
        context=WebScriptContext(_string(value=value["context"], name="Svelte script context")),
        location=_location(payload=value["location"], expected_path=path),
    )


def _svelte_rune(*, payload: object, path: ProjectPath) -> SvelteRuneFact:
    value: dict[str, object] = _mapping(value=payload, name="Svelte rune")
    _keys(value=value, expected={"name", "location"}, name="Svelte rune")
    return SvelteRuneFact(
        name=_string(value=value["name"], name="Svelte rune name"),
        location=_location(payload=value["location"], expected_path=path),
    )


def _syntax_handle(*, payload: object, path: ProjectPath) -> WebSyntaxHandle:
    value: dict[str, object] = _mapping(value=payload, name="Web syntax handle")
    _keys(
        value=value,
        expected={"kind", "name", "start", "end", "location"},
        name="Web syntax handle",
    )
    name: object = value["name"]
    start: int = _integer(value=value["start"], name="Web syntax start")
    end: int = _integer(value=value["end"], name="Web syntax end")
    if end < start:
        raise WebFactProtocolError("Web syntax handle end must not precede its start")
    return WebSyntaxHandle(
        file=File(path=path),
        kind=WebSyntaxKind(_string(value=value["kind"], name="Web syntax kind")),
        name=None if name is None else _string(value=name, name="Web syntax name"),
        start=start,
        end=end,
        location=_location(payload=value["location"], expected_path=path),
    )


def _node(
    *,
    value: WebFileFacts,
    ownership_roots: tuple[str, ...],
    subject_ownership: tuple[ProjectPath | None, tuple[str, ...]] | None,
) -> ModuleNode:
    source_root_depth: int = len(value.source_root.parts)
    directories: tuple[str, ...] = value.file.path.parts[source_root_depth:-1]
    role_index: int | None = next(
        (index for index, part in enumerate(directories) if part in _WEB_ROLES), None
    )
    role: str | None = None if role_index is None else directories[role_index]
    return ModuleNode(
        file=value.file,
        analyzer=value.analyzer,
        source_kind=_position_source_kind(value.source_kind),
        module=value.module,
        scope=value.scope,
        scope_root=value.source_root,
        package=_package(module=value.module),
        domain_parts=_node_domain_parts(
            value=value,
            directories=directories,
            ownership_roots=ownership_roots,
            subject_ownership=subject_ownership,
        ),
        role=role,
        visibility=(
            ModuleVisibility.INTERNAL
            if any(part.startswith("_") for part in value.file.path.parts)
            else ModuleVisibility.PUBLIC
        ),
        ownership_root=(
            subject_ownership[0]
            if subject_ownership is not None
            else _effective_ownership_root(path=value.file.path, ownership_roots=ownership_roots)
        ),
    )


def _node_domain_parts(
    *,
    value: WebFileFacts,
    directories: tuple[str, ...],
    ownership_roots: tuple[str, ...],
    subject_ownership: tuple[ProjectPath | None, tuple[str, ...]] | None,
) -> tuple[str, ...]:
    owned: tuple[str, ...] = (
        subject_ownership[1][:-1]
        if subject_ownership is not None
        else _ownership_directories(
            path=value.file.path,
            directories=directories,
            ownership_roots=ownership_roots,
        )
    )
    owned_role_index: int | None = next(
        (index for index, part in enumerate(owned) if part in _WEB_ROLES), None
    )
    return owned if owned_role_index is None else owned[:owned_role_index]


def _ownership_directories(
    *,
    path: ProjectPath,
    directories: tuple[str, ...],
    ownership_roots: tuple[str, ...],
) -> tuple[str, ...]:
    matches: tuple[str, ...] = tuple(
        root for root in ownership_roots if path.value == root or path.value.startswith(f"{root}/")
    )
    if matches:
        root: str = max(matches, key=lambda item: len(PurePosixPath(item).parts))
        return PurePosixPath(path.value).relative_to(PurePosixPath(root)).parts[:-1]
    if ownership_roots:
        return ()
    if directories and directories[0] == _LIB_DIRECTORY:
        return directories[1:]
    return directories


def _effective_ownership_root(
    *, path: ProjectPath, ownership_roots: tuple[str, ...]
) -> ProjectPath | None:
    matches: tuple[str, ...] = tuple(
        root for root in ownership_roots if path.value == root or path.value.startswith(f"{root}/")
    )
    if not matches:
        return None
    return ProjectPath(max(matches, key=lambda item: len(PurePosixPath(item).parts)))


def _subject_ownership(
    *, subjects: object
) -> dict[ProjectPath, tuple[ProjectPath | None, tuple[str, ...]]]:
    values: dict[ProjectPath, tuple[ProjectPath | None, tuple[str, ...]]] = {}
    for raw_subject in _sequence(value=subjects, name="Web subjects"):
        subject: dict[str, object] = _mapping(value=raw_subject, name="Web subject")
        path: ProjectPath = ProjectPath(_string(value=subject.get("path"), name="Web subject path"))
        raw_root: object = subject.get("ownership_root")
        root: ProjectPath | None = (
            None
            if raw_root is None
            else ProjectPath(_string(value=raw_root, name="ownership root"))
        )
        relative: tuple[str, ...] = _strings(
            value=subject.get("ownership_relative_parts"),
            name="Web ownership-relative parts",
        )
        values[path] = (root, relative)
    return values


def _edge(
    *, source: ModuleNode, imported: WebImportFact, nodes: Mapping[ProjectPath, ModuleNode]
) -> ImportEdge:
    target: ModuleNode | None = None if imported.target is None else nodes.get(imported.target.path)
    specifier_parts: tuple[str, ...] = tuple(
        part
        for part in imported.specifier.split(_PATH_SEPARATOR)
        if part not in {_EMPTY_PATH_PART, _CURRENT_PATH_PART, _PARENT_PATH_PART}
    )
    return ImportEdge(
        source=source,
        authored=AuthoredImport(
            module_parts=specifier_parts,
            imported_parts=tuple(binding.imported_name for binding in imported.bindings),
            bound_name=imported.bindings[0].local_name if imported.bindings else "",
            relative_level=_relative_level(imported.specifier),
            from_import=True,
        ),
        module=target.module if target is not None else imported.specifier,
        location=imported.location,
        status=ImportResolution.RESOLVED if target is not None else ImportResolution.UNRESOLVED,
        target=target,
    )


def _relative_level(specifier: str) -> int:
    level: int = 0
    remaining: str = specifier
    while remaining.startswith(_RELATIVE_PARENT_PREFIX):
        level += 1
        remaining = remaining[len(_RELATIVE_PARENT_PREFIX) :]
    return level + 1 if remaining.startswith(_RELATIVE_CURRENT_PREFIX) else level


def _position_source_kind(value: WebSourceKind) -> SourceKind:
    if value is WebSourceKind.SVELTE:
        return SourceKind.SVELTE_COMPONENT
    if value.value.startswith("javascript"):
        return SourceKind.JAVASCRIPT_MODULE
    return SourceKind.TYPESCRIPT_MODULE


def _package(*, module: str) -> str:
    return module.split(".", maxsplit=1)[0] if module else ""


def _location(*, payload: object, expected_path: ProjectPath) -> SourceLocation:
    value: dict[str, object] = _mapping(value=payload, name="Web location")
    _keys(value=value, expected={"path", "line", "column"}, name="Web location")
    path: ProjectPath = ProjectPath(_string(value=value["path"], name="Web location path"))
    if path != expected_path:
        raise WebFactProtocolError(
            f"Web location path {path} does not match owning file {expected_path}"
        )
    return SourceLocation(
        path=Path(path.value),
        line=_integer(value=value["line"], name="Web location line"),
        column=_integer(value=value["column"], name="Web location column"),
    )


def _project_path(*, value: object, name: str) -> ProjectPath:
    text: str = _string(value=value, name=name)
    return root_path() if text == PROJECT_ROOT else ProjectPath(text)


def _mapping(*, value: object, name: str) -> dict[str, object]:
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise WebFactProtocolError(f"{name} must be an object")
    return cast("dict[str, object]", value)


def _sequence(*, value: object, name: str) -> list[object]:
    if not isinstance(value, list):
        raise WebFactProtocolError(f"{name} must be an array")
    return cast("list[object]", value)


def _keys(*, value: dict[str, object], expected: set[str], name: str) -> None:
    if set(value) != expected:
        raise WebFactProtocolError(f"{name} fields do not match the supported web fact schema")


def _string(*, value: object, name: str) -> str:
    if not isinstance(value, str):
        raise WebFactProtocolError(f"{name} must be a string")
    return value


def _strings(*, value: object, name: str) -> tuple[str, ...]:
    values: list[object] = _sequence(value=value, name=name)
    if any(not isinstance(item, str) for item in values):
        raise WebFactProtocolError(f"{name} must contain only strings")
    return cast("tuple[str, ...]", tuple(values))


def _boolean(*, value: object, name: str) -> bool:
    if not isinstance(value, bool):
        raise WebFactProtocolError(f"{name} must be a boolean")
    return value


def _integer(*, value: object, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise WebFactProtocolError(f"{name} must be a non-negative integer")
    return value
