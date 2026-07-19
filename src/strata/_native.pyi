"""Type stubs for Strata's private native extension."""

from pathlib import Path
from typing import Any

type MemorySummary = tuple[int, int, int, int, int, int, int, int, int]
type SyncSummary = tuple[int, int, int, int, int, bool, bool, int, int, int]
type MemoryOverview = tuple[int, int, int, int, int, int, int, int, int, int, int, int]
type MemorySchemaRelationSummary = tuple[str, str, str]
type MemorySchema = tuple[int, int, tuple[MemorySchemaRelationSummary, ...]]
type MemorySchemaColumn = tuple[str, str, bool, str]
type MemoryRelationSchema = tuple[str, str, str, tuple[MemorySchemaColumn, ...]]
type MemoryDiagnostic = tuple[str, str, int | None, int | None, str, str]
type MemoryCheckResult = tuple[tuple[MemoryDiagnostic, ...], MemorySummary | None]
type MemoryArchiveResult = tuple[tuple[tuple[str, str], ...], SyncSummary | None]
type MemoryGraphNode = tuple[str, str, str, str, str, str, str | None, int, bool]
type MemoryGraphEdge = tuple[str, int, str, str, str, str | None, bool]
type MemoryGraphResult = tuple[
    str,
    tuple[str, ...],
    tuple[MemoryGraphNode, ...],
    tuple[MemoryGraphEdge, ...],
    bool,
    bool,
]
type MemoryGraphQuery = tuple[str, str, list[str], int, int, int, bool]
type MemoryQueryValue = (
    None | bool | int | float | str | list[MemoryQueryValue] | dict[str, MemoryQueryValue]
)

class ProgramHandle: ...

type NativeCacheRecord = tuple[str, object, str]
type NativeCacheMetrics = tuple[int, int, int, int, int, int]
type NativeCacheWrite = tuple[str, str, bytes, bool]

def cache_encode_record(
    kind: str, payload: object, payload_is_validated: bool, maximum_decoded_bytes: int
) -> bytes: ...
def cache_decode_record(
    data: bytes, expected_kind: str, maximum_decoded_bytes: int
) -> NativeCacheRecord | None: ...
def cache_read_batch(
    repo_root: Path, reads: list[tuple[str, str]], maximum_decoded_bytes: int
) -> tuple[bool, list[NativeCacheRecord | None], NativeCacheMetrics]: ...
def cache_write_batch(
    repo_root: Path, writes: list[NativeCacheWrite]
) -> tuple[bool, NativeCacheMetrics]: ...
def cache_mutate_batch(
    repo_root: Path,
    reads: list[tuple[str, str]],
    maximum_decoded_bytes: int,
    mutate: Any,
) -> tuple[bool, bool, NativeCacheMetrics]: ...
def cache_replay_generation(
    repo_root: Path,
    global_fingerprint: str,
    targets: list[tuple[str, str | None]],
    maximum_decoded_bytes: int,
) -> tuple[
    tuple[list[str], str, str, int, str] | None,
    NativeCacheMetrics,
]: ...
def cache_plan_generation(
    repo_root: Path,
    global_fingerprint: str,
    targets: list[tuple[str, str | None]],
    allow_edit: bool,
    maximum_decoded_bytes: int,
) -> tuple[
    tuple[
        str,
        str | None,
        list[tuple[str, str, str, str]],
        list[dict[str, object]],
        list[dict[str, object]],
        list[str],
        int,
        int,
        int,
    ]
    | None,
    NativeCacheMetrics,
]: ...
def cache_publish_generation(
    repo_root: Path,
    global_fingerprint: str,
    expected_index_fingerprint: str | None,
    retained_entries: list[tuple[str, str, str, str]],
    evaluations: list[dict[str, object] | None],
    options: tuple[bool, int],
) -> tuple[
    tuple[int, int, bool, bool, str | None],
    NativeCacheMetrics,
]: ...
def cache_store_check_output(
    repo_root: Path,
    global_fingerprint: str,
    expected_index_fingerprint: str,
    surface: tuple[list[str], str, str, int],
    maximum_decoded_bytes: int,
) -> tuple[bool, NativeCacheMetrics]: ...
def annotation_facts(handle: ProgramHandle, path: Path) -> Any: ...
def evaluate_native_core_rules(
    requests: list[
        tuple[
            ProgramHandle,
            list[str],
            str,
            str | None,
            bool,
            dict[str, int],
            str,
            list[tuple[str, str]],
            list[str],
            bool,
            str,
            tuple[
                list[str],
                list[tuple[str, str]],
                dict[str, list[str]],
                list[tuple[str, str, str, str, int, int]],
            ],
        ]
    ],
) -> list[list[tuple[str, str | None, int | None, int | None, str | None, str | None]]]: ...
def plan_native_core_rule_queries(
    requests: list[tuple[Any, ...]],
) -> list[list[tuple[str, str, str, str]]]: ...
def native_rule_fact_families() -> list[tuple[str, list[str]]]: ...
def assignment_reference_facts(handle: ProgramHandle, path: Path) -> tuple[Any, ...]: ...
def backend_version() -> str: ...
def class_declaration_facts(handle: ProgramHandle, path: Path) -> tuple[Any, ...]: ...
def comment_facts(handle: ProgramHandle, path: Path) -> tuple[Any, ...]: ...
def comparison_facts(handle: ProgramHandle, path: Path) -> tuple[Any, ...]: ...
def outer_state_mutation_facts(handle: ProgramHandle, path: Path) -> tuple[Any, ...]: ...
def reference_facts(handle: ProgramHandle, path: Path) -> Any: ...
def evaluate_rule_call_facts(handle: ProgramHandle, path: Path) -> tuple[Any, ...]: ...
def test_function_facts(handle: ProgramHandle, path: Path) -> tuple[Any, ...]: ...
def test_module_facts(handle: ProgramHandle, path: Path) -> Any: ...
def hygiene_facts(handle: ProgramHandle, path: Path) -> Any: ...
def local_call_edge_facts(handle: ProgramHandle, path: Path) -> tuple[Any, ...]: ...
def named_call_facts(handle: ProgramHandle, path: Path) -> tuple[Any, ...]: ...
def control_flow_facts(handle: ProgramHandle, path: Path) -> tuple[Any, Any, Any]: ...
def dataclass_facts(handle: ProgramHandle, path: Path) -> tuple[Any, ...]: ...
def project_facts(handle: ProgramHandle, path: Path) -> tuple[Any, Any]: ...
def parse_program(source: str, major: int, minor: int) -> ProgramHandle: ...
def parse_programs(sources: list[str], major: int, minor: int) -> list[ProgramHandle | None]: ...
def mapping_index_facts(handle: ProgramHandle) -> tuple[Any, Any, Any, Any]: ...
def mapping_declaration_facts(handle: ProgramHandle) -> tuple[Any, Any, Any, Any]: ...
def check_syntax(source: str, major: int, minor: int) -> tuple[int, int, str] | None: ...
def list_syntax_nodes(
    source: str, major: int, minor: int
) -> list[tuple[str, tuple[int, int, int, int] | None]]: ...
def module_declaration_facts(handle: ProgramHandle, path: Path) -> Any: ...
def function_contract_facts(handle: ProgramHandle, path: Path) -> Any | None: ...
def function_facts(handle: ProgramHandle, path: Path) -> Any: ...
def parameter_mutation_facts(handle: ProgramHandle, path: Path) -> tuple[Any, ...]: ...
def parameter_mutation_occurrence_facts(handle: ProgramHandle, path: Path) -> tuple[Any, ...]: ...
def locate_byte_offset(source: str, offset: int) -> tuple[int, int]: ...
def walk_python_files(
    roots: list[Path],
) -> list[list[tuple[Path, Path | None, list[str] | None]]]: ...
def hash_source_files(paths: list[Path]) -> list[str | None]: ...
def memory_summary(repository_root: Path) -> MemorySummary: ...
def memory_rebuild(repository_root: Path, database_path: Path) -> MemorySummary: ...
def memory_check(repository_root: Path, database_path: Path) -> MemoryCheckResult: ...
def memory_archive(
    repository_root: Path,
    database_path: Path,
    requested_paths: list[Path],
    archive_after_days: int,
    confirmed: bool,
) -> MemoryArchiveResult: ...
def memory_sync(repository_root: Path, database_path: Path) -> SyncSummary: ...
def memory_overview(database_path: Path) -> MemoryOverview: ...
def memory_schema_sql() -> str: ...
def memory_schema() -> MemorySchema: ...
def memory_relation_schema(name: str) -> MemoryRelationSchema | None: ...
def memory_query(
    database_path: Path, sql: str, limit: int
) -> tuple[
    tuple[str, ...],
    tuple[str, ...],
    tuple[tuple[MemoryQueryValue, ...], ...],
    bool,
]: ...
def memory_graph(
    database_path: Path,
    request: MemoryGraphQuery,
) -> MemoryGraphResult: ...
def memory_dependency_probe(repository_root: Path) -> str: ...
