"""Build immutable public Rust facts from the native host payload."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import cast

from fensu.analysis.models import SourceLocation
from fensu.config.types import AnalyzerId
from fensu.discovery.constants import ROLE_DIR_NAMES
from fensu.discovery.types import RoleName, ScopeName
from fensu.rules.authoring._helpers.project_tree import root_path
from fensu.rules.authoring.constants import PROJECT_ROOT
from fensu.rules.authoring.exceptions import RustFactProtocolError
from fensu.rules.authoring.models import (
    File,
    FilePosition,
    ProjectPath,
    ProjectTree,
    RustCrateFact,
    RustDependencyFact,
    RustFileFacts,
    RustItemFact,
    RustTargetFact,
    RustUseFact,
    RustWorkspaceFacts,
)
from fensu.rules.authoring.types import (
    RustItemKind,
    RustUseResolution,
    RustVisibility,
    SourceKind,
)


def rust_workspace_facts(*, payload: object) -> RustWorkspaceFacts:
    """Decode one trusted versioned native Rust fact payload."""

    value: dict[str, object] = _mapping(value=payload, name="Rust facts")
    _keys(
        value=value,
        expected={"schema_version", "parser_contract", "crates", "files"},
        name="Rust facts",
    )
    crates: tuple[RustCrateFact, ...] = tuple(
        _crate(payload=item) for item in _sequence(value=value["crates"], name="Rust crates")
    )
    files: tuple[RustFileFacts, ...] = tuple(
        _file(payload=item) for item in _sequence(value=value["files"], name="Rust files")
    )
    return RustWorkspaceFacts(
        schema_version=_string(value=value["schema_version"], name="Rust fact schema"),
        parser_contract=_string(value=value["parser_contract"], name="Rust parser contract"),
        _crate_values=crates,
        _file_values=files,
        _crates_by_identity=MappingProxyType({item.identity: item for item in crates}),
        _files_by_path=MappingProxyType({item.file.path: item for item in files}),
    )


def rust_project_tree(
    *, subjects: object, workspace: RustWorkspaceFacts, ownership_roots: tuple[str, ...] = ()
) -> tuple[ProjectTree, MappingProxyType[ProjectPath, RustFileFacts]]:
    """Build a deterministic common project tree from native Rust subjects."""

    facts_by_path: dict[ProjectPath, RustFileFacts] = {
        item.file.path: item for item in workspace._file_values
    }
    positions: dict[ProjectPath, FilePosition] = {}
    for raw_subject in _sequence(value=subjects, name="Rust subjects"):
        subject: dict[str, object] = _mapping(value=raw_subject, name="Rust subject")
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
            name="Rust subject",
        )
        path: ProjectPath = ProjectPath(_string(value=subject["path"], name="Rust subject path"))
        fact: RustFileFacts | None = facts_by_path.get(path)
        if fact is None:
            continue
        configured_ownership_relative_parts: tuple[str, ...] = _strings(
            value=subject["ownership_relative_parts"], name="Rust ownership-relative parts"
        )
        subject_ownership_root: ProjectPath | None = (
            None
            if subject["ownership_root"] is None
            else ProjectPath(_string(value=subject["ownership_root"], name="ownership root"))
        )
        ownership_root: ProjectPath | None = subject_ownership_root
        ownership_root_declaration: str | None = (
            None
            if subject["ownership_root_declaration"] is None
            else _string(
                value=subject["ownership_root_declaration"],
                name="ownership root declaration",
            )
        )
        if ownership_root is None and fact.source_root.value in ownership_roots:
            ownership_root = fact.source_root
            ownership_root_declaration = "Cargo source root"
        ownership_relative_parts: tuple[str, ...] = configured_ownership_relative_parts
        if ownership_root is not None and not ownership_relative_parts:
            ownership_relative_parts = path.parts[len(ownership_root.parts) :]
        directories: tuple[str, ...] = ownership_relative_parts[:-1]
        role_index: int | None = next(
            (index for index, part in enumerate(directories) if part in ROLE_DIR_NAMES), None
        )
        role: str | None = None if role_index is None else directories[role_index]
        scope_root_text: str = _string(value=subject["scope_root"], name="Rust scope root")
        scope_root: ProjectPath = (
            root_path() if scope_root_text == PROJECT_ROOT else ProjectPath(scope_root_text)
        )
        positions[path] = FilePosition(
            path=path,
            analyzer=AnalyzerId.RUST,
            source_kind=SourceKind.RUST_MODULE,
            scope=ScopeName(_string(value=subject["scope"], name="Rust scope")),
            scope_root=scope_root,
            module="::".join(fact.module_parts),
            package=fact.crate_name,
            domain_parts=directories if role_index is None else directories[:role_index],
            role=role,
            role_depth=None if role_index is None else len(directories) - role_index - 1,
            is_entry_module=_is_entry_path(path=path, crates=workspace._crate_values),
            is_main_module=RoleName.MAIN.value in directories,
            ownership_root=ownership_root,
            ownership_root_declaration=ownership_root_declaration,
            ownership_relative_parts=ownership_relative_parts,
        )
    all_paths: set[ProjectPath] = set(positions)
    for file_path in tuple(all_paths):
        for depth in range(1, len(file_path.parts)):
            all_paths.add(ProjectPath(PurePosixPath(*file_path.parts[:depth]).as_posix()))
    ordered_paths: tuple[ProjectPath, ...] = tuple(sorted(all_paths, key=lambda item: item.value))
    children: dict[ProjectPath, list[ProjectPath]] = {}
    project_root: ProjectPath = root_path()
    for path in ordered_paths:
        parent: ProjectPath = project_root if len(path.parts) == 1 else path.parent
        children.setdefault(parent, []).append(path)
    tree: ProjectTree = ProjectTree(
        _paths=ordered_paths,
        _files=tuple(File(path=path) for path in sorted(positions, key=lambda item: item.value)),
        _children=MappingProxyType({key: tuple(value) for key, value in children.items()}),
        _positions=MappingProxyType(positions),
    )
    return tree, MappingProxyType(
        {path: fact for path, fact in facts_by_path.items() if path in positions}
    )


def selected_rust_workspace(
    *, workspace: RustWorkspaceFacts, files: Mapping[ProjectPath, RustFileFacts]
) -> RustWorkspaceFacts:
    """Restrict file facts to the authoritative configured source selection."""

    ordered: tuple[RustFileFacts, ...] = tuple(
        files[path] for path in sorted(files, key=lambda item: item.value)
    )
    return RustWorkspaceFacts(
        schema_version=workspace.schema_version,
        parser_contract=workspace.parser_contract,
        _crate_values=workspace._crate_values,
        _file_values=ordered,
        _crates_by_identity=workspace._crates_by_identity,
        _files_by_path=MappingProxyType({item.file.path: item for item in ordered}),
    )


def _crate(*, payload: object) -> RustCrateFact:
    value: dict[str, object] = _mapping(value=payload, name="Rust crate")
    _keys(
        value=value,
        expected={
            "identity",
            "name",
            "directory",
            "manifest_path",
            "library_name",
            "targets",
            "dependencies",
        },
        name="Rust crate",
    )
    library_name: object = value["library_name"]
    return RustCrateFact(
        identity=_string(value=value["identity"], name="Rust crate identity"),
        name=_string(value=value["name"], name="Rust crate name"),
        directory=_project_path(
            value=_string(value=value["directory"], name="Rust crate directory")
        ),
        manifest_path=ProjectPath(_string(value=value["manifest_path"], name="Rust manifest path")),
        library_name=(
            None if library_name is None else _string(value=library_name, name="Rust library name")
        ),
        targets=tuple(
            _target(payload=item) for item in _sequence(value=value["targets"], name="Rust targets")
        ),
        dependencies=tuple(
            _dependency(payload=item)
            for item in _sequence(value=value["dependencies"], name="Rust dependencies")
        ),
    )


def _target(*, payload: object) -> RustTargetFact:
    value: dict[str, object] = _mapping(value=payload, name="Rust target")
    _keys(
        value=value,
        expected={"identity", "name", "kinds", "source_root", "entry_path", "test"},
        name="Rust target",
    )
    return RustTargetFact(
        identity=_string(value=value["identity"], name="Rust target identity"),
        name=_string(value=value["name"], name="Rust target name"),
        kinds=_strings(value=value["kinds"], name="Rust target kinds"),
        source_root=_project_path(
            value=_string(value=value["source_root"], name="Rust source root")
        ),
        entry_path=ProjectPath(_string(value=value["entry_path"], name="Rust entry path")),
        test=_boolean(value=value["test"], name="Rust target test"),
    )


def _dependency(*, payload: object) -> RustDependencyFact:
    value: dict[str, object] = _mapping(value=payload, name="Rust dependency")
    _keys(
        value=value,
        expected={"package_name", "source_name", "kinds", "local_crate_identity", "resolved"},
        name="Rust dependency",
    )
    local: object = value["local_crate_identity"]
    return RustDependencyFact(
        package_name=_string(value=value["package_name"], name="Rust dependency package"),
        source_name=_string(value=value["source_name"], name="Rust dependency source"),
        kinds=_strings(value=value["kinds"], name="Rust dependency kinds"),
        local_crate_identity=(
            None if local is None else _string(value=local, name="Rust local crate identity")
        ),
        resolved=_boolean(value=value["resolved"], name="Rust dependency resolution"),
    )


def _file(*, payload: object) -> RustFileFacts:
    value: dict[str, object] = _mapping(value=payload, name="Rust file")
    _keys(
        value=value,
        expected={
            "path",
            "crate_identity",
            "crate_name",
            "module_parts",
            "source_root",
            "test",
            "source",
            "parse_error",
            "items",
            "uses",
        },
        name="Rust file",
    )
    path: ProjectPath = ProjectPath(_string(value=value["path"], name="Rust file path"))
    parse_error: object = value["parse_error"]
    return RustFileFacts(
        file=File(path=path),
        crate_identity=_string(value=value["crate_identity"], name="Rust file crate identity"),
        crate_name=_string(value=value["crate_name"], name="Rust file crate name"),
        module_parts=_strings(value=value["module_parts"], name="Rust module parts"),
        source_root=_project_path(
            value=_string(value=value["source_root"], name="Rust file source root")
        ),
        test=_boolean(value=value["test"], name="Rust file test"),
        source=_string(value=value["source"], name="Rust source"),
        parse_error=(
            None if parse_error is None else _string(value=parse_error, name="Rust parse error")
        ),
        items=tuple(
            _item(payload=item, path=path)
            for item in _sequence(value=value["items"], name="Rust items")
        ),
        uses=tuple(_use(payload=item) for item in _sequence(value=value["uses"], name="Rust uses")),
    )


def _item(*, payload: object, path: ProjectPath) -> RustItemFact:
    value: dict[str, object] = _mapping(value=payload, name="Rust item")
    _keys(
        value=value,
        expected={
            "kind",
            "name",
            "module_parts",
            "visibility",
            "derives",
            "implemented_trait",
            "implementation_target",
            "location",
        },
        name="Rust item",
    )
    visibility_text: str = _string(value=value["visibility"], name="Rust visibility")
    restricted, separator, visibility_path = visibility_text.partition(":")
    name: object = value["name"]
    implemented_trait: object = value["implemented_trait"]
    implementation_target: object = value["implementation_target"]
    return RustItemFact(
        kind=RustItemKind(_string(value=value["kind"], name="Rust item kind")),
        name=None if name is None else _string(value=name, name="Rust item name"),
        module_parts=_strings(value=value["module_parts"], name="Rust item module"),
        visibility=RustVisibility.RESTRICTED if separator else RustVisibility(restricted),
        visibility_path=visibility_path if separator else None,
        derives=_strings(value=value["derives"], name="Rust derives"),
        implemented_trait=(
            None
            if implemented_trait is None
            else _string(value=implemented_trait, name="Rust implemented trait")
        ),
        implementation_target=(
            None
            if implementation_target is None
            else _string(value=implementation_target, name="Rust implementation target")
        ),
        location=_location(payload=value["location"], expected_path=path),
    )


def _use(*, payload: object) -> RustUseFact:
    value: dict[str, object] = _mapping(value=payload, name="Rust use")
    _keys(
        value=value,
        expected={
            "source_path",
            "source_module_parts",
            "authored_parts",
            "target_module_parts",
            "target_path",
            "target_crate_identity",
            "resolution",
            "location",
        },
        name="Rust use",
    )
    source_path: ProjectPath = ProjectPath(
        _string(value=value["source_path"], name="Rust use source")
    )
    target_path: object = value["target_path"]
    target_module: object = value["target_module_parts"]
    target_crate: object = value["target_crate_identity"]
    return RustUseFact(
        source=File(path=source_path),
        source_module_parts=_strings(value=value["source_module_parts"], name="Rust use module"),
        authored_parts=_strings(value=value["authored_parts"], name="Rust authored use"),
        target_module_parts=(
            None
            if target_module is None
            else _strings(value=target_module, name="Rust target module")
        ),
        target=(
            None
            if target_path is None
            else File(path=ProjectPath(_string(value=target_path, name="Rust use target")))
        ),
        target_crate_identity=(
            None if target_crate is None else _string(value=target_crate, name="Rust target crate")
        ),
        resolution=RustUseResolution(
            _string(value=value["resolution"], name="Rust use resolution")
        ),
        location=_location(payload=value["location"], expected_path=source_path),
    )


def _location(*, payload: object, expected_path: ProjectPath) -> SourceLocation:
    value: dict[str, object] = _mapping(value=payload, name="Rust location")
    _keys(value=value, expected={"path", "start", "end"}, name="Rust location")
    path: ProjectPath = ProjectPath(_string(value=value["path"], name="Rust location path"))
    if path != expected_path:
        raise RustFactProtocolError(
            f"Rust location path {path} does not match owning file {expected_path}"
        )
    start: dict[str, object] = _mapping(value=value["start"], name="Rust location start")
    _keys(value=start, expected={"line", "column"}, name="Rust location start")
    return SourceLocation(
        path=Path(path.value),
        line=_integer(value=start["line"], name="Rust location line"),
        column=_integer(value=start["column"], name="Rust location column"),
    )


def _mapping(*, value: object, name: str) -> dict[str, object]:
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise RustFactProtocolError(f"{name} must be an object")
    return cast("dict[str, object]", value)


def _sequence(*, value: object, name: str) -> list[object]:
    if not isinstance(value, list):
        raise RustFactProtocolError(f"{name} must be an array")
    return cast("list[object]", value)


def _keys(*, value: dict[str, object], expected: set[str], name: str) -> None:
    if set(value) != expected:
        raise RustFactProtocolError(f"{name} fields do not match the supported Rust fact schema")


def _string(*, value: object, name: str) -> str:
    if not isinstance(value, str):
        raise RustFactProtocolError(f"{name} must be a string")
    return value


def _strings(*, value: object, name: str) -> tuple[str, ...]:
    values: list[object] = _sequence(value=value, name=name)
    if any(not isinstance(item, str) for item in values):
        raise RustFactProtocolError(f"{name} must contain only strings")
    return cast("tuple[str, ...]", tuple(values))


def _boolean(*, value: object, name: str) -> bool:
    if not isinstance(value, bool):
        raise RustFactProtocolError(f"{name} must be a boolean")
    return value


def _integer(*, value: object, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise RustFactProtocolError(f"{name} must be a non-negative integer")
    return value


def _project_path(*, value: str) -> ProjectPath:
    return root_path() if not value or value == PROJECT_ROOT else ProjectPath(value)


def _is_entry_path(*, path: ProjectPath, crates: tuple[RustCrateFact, ...]) -> bool:
    for crate in crates:
        if any(target.entry_path == path for target in crate.targets):
            return True
    return False
