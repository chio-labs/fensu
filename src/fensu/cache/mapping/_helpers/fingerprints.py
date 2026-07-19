"""Call-map cache fingerprint construction."""

import platform
from pathlib import Path

from fensu.cache.fingerprints.main._canonical import fingerprint_canonical
from fensu.cache.fingerprints.main._implementation import fingerprint_implementation
from fensu.cache.fingerprints.types import CanonicalValue
from fensu.cache.mapping.constants import MAP_CACHE_CONTRACT_VERSION
from fensu.cache.mapping.models import MappingIdentity
from fensu.mapping.models import SourceSnapshot


def build_mapping_identity() -> MappingIdentity:
    """Return the complete implementation identity for mapping records."""

    package_root: Path = Path(__file__).resolve().parents[3]
    return MappingIdentity(
        contract=MAP_CACHE_CONTRACT_VERSION,
        python_implementation=platform.python_implementation(),
        python_version=platform.python_version(),
        fensu_implementation=fingerprint_implementation(package_root=package_root).value,
    )


def file_declaration_identity(
    *, snapshot: SourceSnapshot, mapping_identity: MappingIdentity
) -> str:
    """Return the content-addressed declaration identity for one source."""

    return fingerprint_canonical(
        {
            "contract": mapping_identity.contract,
            "import_root": snapshot.import_root_identity,
            "module": snapshot.module_name,
            "path": snapshot.relative_path,
            "python_implementation": mapping_identity.python_implementation,
            "python_version": mapping_identity.python_version,
            "source": snapshot.source_fingerprint,
            "fensu_implementation": mapping_identity.fensu_implementation,
        }
    ).value


def project_input_fingerprint(
    *, snapshots: tuple[SourceSnapshot, ...], mapping_identity: MappingIdentity
) -> str:
    """Return the exact map-index input identity for one project snapshot."""

    sources: list[CanonicalValue] = [
        [
            snapshot.relative_path,
            snapshot.module_name,
            snapshot.import_root_identity,
            snapshot.source_fingerprint,
        ]
        for snapshot in snapshots
    ]
    payload: CanonicalValue = {
        "contract": mapping_identity.contract,
        "implementation": mapping_identity.fensu_implementation,
        "python_implementation": mapping_identity.python_implementation,
        "python_version": mapping_identity.python_version,
        "sources": sources,
    }
    return fingerprint_canonical(payload).value
