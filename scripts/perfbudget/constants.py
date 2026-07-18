"""Budget scenario names and default ceilings."""

UNCACHED_SCENARIO: str = "uncached"
COLD_SCENARIO: str = "cold"
WARM_SCENARIO: str = "warm"
EDIT_SCENARIO: str = "one_edit"
CHURN_1_PERCENT_SCENARIO: str = "churn_1_percent"
CHURN_25_PERCENT_SCENARIO: str = "churn_25_percent"
CHURN_75_PERCENT_SCENARIO: str = "churn_75_percent"
CHURN_100_PERCENT_SCENARIO: str = "churn_100_percent"
GLOBAL_MISMATCH_SCENARIO: str = "global_mismatch"
GLOBAL_MISMATCH_UNCACHED_SCENARIO: str = "global_mismatch_uncached"
CHURN_UNCACHED_SCENARIO: str = "churn_uncached"
DENSE_COLD_SCENARIO: str = "dense_cold"
DENSE_WARM_SCENARIO: str = "dense_warm"
VERSION_SCENARIO: str = "version"
INIT_SCENARIO: str = "init"
DENSE_FAULT_EVERY: int = 1
DEFAULT_FILE_TARGET: int = 2400
DEFAULT_SEED: int = 0
DEFAULT_UNCACHED_CEILING_SECONDS: float = 5.7
DEFAULT_COLD_CEILING_SECONDS: float = 6.6
DEFAULT_WARM_CEILING_SECONDS: float = 1.4
DEFAULT_EDIT_CEILING_SECONDS: float = 3.4
DEFAULT_VERSION_CEILING_SECONDS: float = 0.15
DEFAULT_INIT_CEILING_SECONDS: float = 6.1
FAULT_EXIT_CODE: int = 1
WARM_MISS_FREE_FRAGMENT: str = "misses=0"
WARM_WRITE_FREE_FRAGMENT: str = "writes=0"
EDITED_HELPER_FILE_NAME: str = "record_shaping.py"
EDIT_APPENDIX: str = "\nEDIT_MARKER: int = 1\n"
CHURN_APPENDIX: str = "\n"
GLOBAL_MISMATCH_CONFIG_APPENDIX: str = (
    '\n[evaluation]\nexclude = ["__strata_performance_no_match__/**"]\n'
)
