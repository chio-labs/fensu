"""Operation names and the process-wide counter for performance tests."""

from strata.instrumentation.classes.operation_counters import OperationCounters

OPERATION_COUNTERS: OperationCounters = OperationCounters()
PARSE_OPERATION: str = "parse_python_source"
NATIVE_PARSE_OPERATION: str = "parse_native_program"
DEPENDENCY_RECORD_OPERATION: str = "dependency_record"
RELATIVE_PATH_COMPUTE_OPERATION: str = "relative_path_compute"
CANONICAL_ENCODE_OPERATION: str = "canonical_encode"
FRESH_EVALUATION_OPERATION: str = "fresh_evaluation"
CACHE_RECORD_READ_OPERATION: str = "cache_record_read"
CACHE_RECORD_SCAN_OPERATION: str = "cache_record_scan"
CACHE_RECORD_WRITE_OPERATION: str = "cache_record_write"
CACHE_RECORD_DELETE_OPERATION: str = "cache_record_delete"
CACHE_MANIFEST_VALIDATION_OPERATION: str = "cache_manifest_validation"
