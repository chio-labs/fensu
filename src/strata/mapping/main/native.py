"""Native-substrate conservative call-map provider."""

from strata.mapping._helpers.discovery import discover_source_snapshots
from strata.mapping._helpers.native_index import build_file_indexes
from strata.mapping._helpers.tree import build_tree
from strata.mapping.main.select import select_mapping_function
from strata.mapping.models import (
    CallMapNode,
    ClassDefinition,
    FunctionDefinition,
    MappingSource,
    ProjectIndex,
    SourceSnapshot,
)


def build_native_call_map(
    *, sources: tuple[MappingSource, ...], symbol: str, depth: int
) -> CallMapNode:
    """Resolve project calls over native project-function and local-edge facts."""

    snapshots: tuple[SourceSnapshot, ...] = discover_source_snapshots(
        sources=sources, repo_root=None
    )
    functions: dict[str, FunctionDefinition] = {}
    classes: dict[str, ClassDefinition] = {}
    for indexed in build_file_indexes(snapshots=snapshots):
        functions.update(indexed.functions)
        classes.update(indexed.classes)
    index: ProjectIndex = ProjectIndex(
        functions=functions,
        classes=classes,
        protocol_implementations=ProjectIndex.build_protocol_implementation_keys(
            class_bases={key: definition.base_keys for key, definition in classes.items()},
            protocol_keys=frozenset(
                key for key, definition in classes.items() if definition.protocol
            ),
        ),
    )
    root: FunctionDefinition = select_mapping_function(definitions=functions, symbol=symbol)
    return build_tree(root=root, index=index, depth=depth)
