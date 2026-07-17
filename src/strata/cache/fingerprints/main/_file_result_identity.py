"""Build one file-result identity from its generation and stored bytes."""

from strata.cache.fingerprints.constants import FILE_RESULT_FINGERPRINT_DOMAIN
from strata.cache.fingerprints.main.source import fingerprint_source
from strata.cache.fingerprints.models import CacheFingerprint


def file_result_identity(
    *,
    global_fingerprint: CacheFingerprint,
    record_fingerprint: CacheFingerprint,
) -> CacheFingerprint:
    """Return the identity binding one result record to its cache generation."""

    return fingerprint_source(
        FILE_RESULT_FINGERPRINT_DOMAIN
        + global_fingerprint.value.encode("ascii")
        + record_fingerprint.value.encode("ascii")
    )
