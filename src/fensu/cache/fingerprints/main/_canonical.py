"""Build a fingerprint from one canonical value."""

from fensu.cache.fingerprints._helpers.fingerprints import canonical_fingerprint
from fensu.cache.fingerprints.models import CacheFingerprint
from fensu.cache.fingerprints.types import CanonicalValue


def fingerprint_canonical(value: CanonicalValue) -> CacheFingerprint:
    """Return the SHA-256 identity of canonical JSON data."""

    return canonical_fingerprint(value)
