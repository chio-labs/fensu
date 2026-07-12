"""Build correctness and integrity identities for one cached file result."""

from strata.cache.fingerprints.helpers.fingerprints import (
    file_result_fingerprint,
    file_result_record_fingerprint,
)
from strata.cache.fingerprints.models import CacheFingerprint, FileResultFingerprints
from strata.cache.results.models import CachedFileResult


def file_result_fingerprints(
    *,
    global_fingerprint: CacheFingerprint,
    result: CachedFileResult,
) -> FileResultFingerprints:
    """Return correctness and full-record identities for one file result."""

    return FileResultFingerprints(
        result=file_result_fingerprint(global_fingerprint=global_fingerprint, result=result),
        record=file_result_record_fingerprint(result),
    )
