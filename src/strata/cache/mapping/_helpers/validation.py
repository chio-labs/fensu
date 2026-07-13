"""Validate mapping manifests against current source identities."""

from strata.cache.mapping.models import FileDeclarations, FunctionDeclaration, MapManifest
from strata.mapping.constants import QUALIFIED_NAME_SEPARATOR
from strata.mapping.models import SourceSnapshot


def manifest_is_current(
    *,
    manifest: MapManifest,
    snapshots: tuple[SourceSnapshot, ...],
    identities: tuple[str, ...],
) -> bool:
    """Return whether every manifest lookup exactly derives from current files."""

    if len(manifest.files) != len(snapshots) or len(snapshots) != len(identities):
        return False
    seen_identities: set[str] = set()
    seen_paths: set[str] = set()
    functions: dict[str, str] = {}
    classes: dict[str, str] = {}
    metadata: dict[str, FunctionDeclaration] = {}
    for declaration, snapshot, identity in zip(manifest.files, snapshots, identities, strict=True):
        if not file_declarations_are_current(
            declaration=declaration, snapshot=snapshot, identity=identity
        ):
            return False
        if identity in seen_identities or declaration.path in seen_paths:
            return False
        seen_identities.add(identity)
        seen_paths.add(declaration.path)
        for function in declaration.functions:
            functions[function.key] = identity
            metadata[function.key] = function
        for class_key in declaration.class_keys:
            classes[class_key] = identity
    bare: dict[str, list[str]] = {}
    for key in functions:
        bare.setdefault(metadata[key].name, []).append(key)
    expected_bare: dict[str, tuple[str, ...]] = {name: tuple(keys) for name, keys in bare.items()}
    return (
        manifest.functions == functions
        and manifest.classes == classes
        and manifest.bare_functions == expected_bare
    )


def file_declarations_are_current(
    *, declaration: FileDeclarations, snapshot: SourceSnapshot, identity: str
) -> bool:
    if (
        declaration.identity != identity
        or declaration.path != snapshot.relative_path
        or declaration.module_name != snapshot.module_name
        or len(set(declaration.class_keys)) != len(declaration.class_keys)
    ):
        return False
    class_prefix: str = f"{declaration.module_name}."
    if any(
        not key.startswith(class_prefix)
        or QUALIFIED_NAME_SEPARATOR in key.removeprefix(class_prefix)
        for key in declaration.class_keys
    ):
        return False
    if len({item.key for item in declaration.functions}) != len(declaration.functions):
        return False
    class_keys: frozenset[str] = frozenset(declaration.class_keys)
    for function in declaration.functions:
        qualified_name: str = (
            function.name
            if function.owning_class is None
            else f"{function.owning_class}.{function.name}"
        )
        if function.qualified_name != qualified_name:
            return False
        if function.key != f"{declaration.module_name}.{qualified_name}":
            return False
        if (
            function.owning_class is not None
            and f"{declaration.module_name}.{function.owning_class}" not in class_keys
        ):
            return False
    return True
