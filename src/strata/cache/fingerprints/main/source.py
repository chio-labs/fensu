"""Build a complete source-content fingerprint."""

from strata.cache.fingerprints.helpers.fingerprints import source_fingerprint
from strata.cache.fingerprints.models import CacheFingerprint


def fingerprint_source(content: bytes) -> CacheFingerprint:
    """Return the SHA-256 identity of complete source bytes."""

    return source_fingerprint(content)
