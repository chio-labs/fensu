"""Index one immutable mapping source snapshot."""

from fensu.mapping._helpers.native_index import build_file_index
from fensu.mapping.models import ProjectIndex, SourceSnapshot


def index_mapping_file(*, snapshot: SourceSnapshot) -> ProjectIndex:
    """Extract declarations and AST-backed facts from one source."""

    return build_file_index(snapshot=snapshot)
