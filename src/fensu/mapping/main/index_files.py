"""Index mapping files through the native batch boundary."""

from fensu.mapping._helpers.native_index import build_file_indexes
from fensu.mapping.models import ProjectIndex, SourceSnapshot


def index_mapping_files(*, snapshots: tuple[SourceSnapshot, ...]) -> tuple[ProjectIndex, ...]:
    """Return complete native indexes for mapping source snapshots."""

    return build_file_indexes(snapshots=snapshots)
