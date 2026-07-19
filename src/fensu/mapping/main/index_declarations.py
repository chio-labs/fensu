"""Index mapping declarations through the native batch boundary."""

from fensu.mapping._helpers.native_index import build_declaration_indexes
from fensu.mapping.models import ProjectIndex, SourceSnapshot


def index_mapping_declarations(
    *, snapshots: tuple[SourceSnapshot, ...]
) -> tuple[ProjectIndex, ...]:
    """Return declaration-only native indexes for cache publication."""

    return build_declaration_indexes(snapshots=snapshots)
