"""Operation names and the process-wide counter for performance tests."""

from strata.instrumentation.classes.operation_counters import OperationCounters

OPERATION_COUNTERS: OperationCounters = OperationCounters()
PARSE_OPERATION: str = "parse_python_source"
DEPENDENCY_RECORD_OPERATION: str = "dependency_record"
RELATIVE_PATH_COMPUTE_OPERATION: str = "relative_path_compute"
CANONICAL_ENCODE_OPERATION: str = "canonical_encode"
FRESH_EVALUATION_OPERATION: str = "fresh_evaluation"
