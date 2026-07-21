"""Build a complete source-content fingerprint."""

from fensu.cache.fingerprints._helpers.fingerprints import source_fingerprint
from fensu.cache.fingerprints.models import CacheFingerprint


def fingerprint_source(content: bytes) -> CacheFingerprint:
    """Return the SHA-256 identity of complete source bytes."""

    return source_fingerprint(content)
