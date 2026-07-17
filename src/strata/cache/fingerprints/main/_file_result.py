"""Build correctness and integrity identities for one cached file result."""

from strata.cache.fingerprints.main._file_result_identity import file_result_identity
from strata.cache.fingerprints.main.source import fingerprint_source
from strata.cache.fingerprints.models import CacheFingerprint, FileResultFingerprints


def file_result_fingerprints(
    *,
    global_fingerprint: CacheFingerprint,
    encoded: bytes,
) -> FileResultFingerprints:
    """Return the correctness identity and exact stored-bytes identity."""

    record_fingerprint: CacheFingerprint = fingerprint_source(encoded)
    return FileResultFingerprints(
        result=file_result_identity(
            global_fingerprint=global_fingerprint,
            record_fingerprint=record_fingerprint,
        ),
        record=record_fingerprint,
    )
