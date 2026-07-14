"""Build correctness and integrity identities for one cached file result."""

from strata.cache.fingerprints._helpers.fingerprints import file_result_fingerprint
from strata.cache.fingerprints.main.source import fingerprint_source
from strata.cache.fingerprints.models import CacheFingerprint, FileResultFingerprints
from strata.cache.results.models import CachedFileResult


def file_result_fingerprints(
    *,
    global_fingerprint: CacheFingerprint,
    result: CachedFileResult,
    encoded: bytes,
) -> FileResultFingerprints:
    """Return the correctness identity and exact stored-bytes identity."""

    return FileResultFingerprints(
        result=file_result_fingerprint(global_fingerprint=global_fingerprint, result=result),
        record=fingerprint_source(encoded),
    )
