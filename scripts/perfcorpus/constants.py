"""Constants shaping the generated performance corpus."""

PACKAGE_NAME: str = "corpusapp"
SOURCE_ROOT: str = "src"
TESTS_ROOT: str = "tests"
TEST_SCOPE: str = "unit"
FILES_PER_DOMAIN: int = 23
SCAFFOLDING_FILE_COUNT: int = 6
MINIMUM_DOMAINS: int = 2
ANNOTATION_FAULT_EVERY: int = 5
MAGIC_NUMBER_FAULT_EVERY: int = 7
HELPER_MODULE_NAMES: tuple[str, ...] = (
    "record_shaping",
    "record_selection",
    "record_reporting",
    "record_auditing",
    "record_pricing",
    "record_settlement",
)
RECORD_STATES: tuple[str, ...] = (
    "draft",
    "pending",
    "settled",
    "archived",
    "disputed",
    "refunded",
)
DOMAIN_FIRST_WORDS: tuple[str, ...] = (
    "billing",
    "catalog",
    "shipping",
    "inventory",
    "payments",
    "accounts",
    "orders",
    "pricing",
    "contracts",
    "returns",
    "loyalty",
    "invoicing",
)
DOMAIN_SECOND_WORDS: tuple[str, ...] = (
    "reports",
    "ledgers",
    "profiles",
    "snapshots",
    "forecasts",
    "audits",
    "schedules",
    "summaries",
    "policies",
    "quotas",
    "journals",
    "digests",
)
STRATA_CONFIG: str = 'roots = ["src/corpusapp"]\ntests = ["tests"]\nselect = ["SF"]\n'
