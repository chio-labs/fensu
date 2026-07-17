"""Build a fingerprint from one canonical value."""

from strata.cache.fingerprints._helpers.fingerprints import canonical_fingerprint
from strata.cache.fingerprints.models import CacheFingerprint
from strata.cache.fingerprints.types import CanonicalValue


def fingerprint_canonical(value: CanonicalValue) -> CacheFingerprint:
    """Return the SHA-256 identity of canonical JSON data."""

    return canonical_fingerprint(value)
