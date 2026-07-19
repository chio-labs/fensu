"""Build the loaded Fensu implementation identity."""

from pathlib import Path

from fensu.cache.fingerprints._helpers.fingerprints import implementation_fingerprint
from fensu.cache.fingerprints.models import CacheFingerprint


def fingerprint_implementation(*, package_root: Path) -> CacheFingerprint:
    """Return the content identity of implementation files."""

    return implementation_fingerprint(package_root=package_root)
