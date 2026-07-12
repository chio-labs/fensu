"""Test case types for repository scaffolding."""

from __future__ import annotations

from dataclasses import dataclass

from strata.scaffolding.types import AdoptionMode, InteractionDecision


@dataclass(frozen=True)
class DetectionTestCase:
    """Repository contents and expected detected layout."""

    description: str
    files: tuple[tuple[str, str], ...]
    directories: tuple[str, ...]
    expected_roots: tuple[tuple[str, str], ...]
    expected_tests: tuple[tuple[str, str, bool], ...]
    expected_tooling: tuple[str, ...]
    expected_python_state: tuple[int, int, bool]


@dataclass(frozen=True)
class DetectionErrorTestCase:
    """Invalid repository input and its expected detection error."""

    description: str
    pyproject_text: str
    expected_error_type: type[Exception]
    expected_error_fragment: str


@dataclass(frozen=True)
class RenderConfigTestCase:
    """Initialization choices and exact rendered configuration."""

    description: str
    roots: tuple[str, ...]
    tests: tuple[str, ...]
    tooling: tuple[str, ...]
    adoption: AdoptionMode
    expected_text: str
    expected_select: tuple[str, ...]


@dataclass(frozen=True)
class InteractionDecisionTestCase:
    """Detected state and options completeness with expected interaction need."""

    description: str
    is_empty: bool
    has_tooling: bool
    yes: bool
    roots: tuple[str, ...] | None
    tests: tuple[str, ...] | None
    tooling: tuple[str, ...] | None
    skills: bool | None
    name: str | None
    expected_decision: InteractionDecision


@dataclass(frozen=True)
class NormalizeNameTestCase:
    """Raw project name and expected Python package name."""

    description: str
    value: str
    expected_name: str


@dataclass(frozen=True)
class InvalidNameTestCase:
    """Raw project name that cannot produce an identifier."""

    description: str
    value: str
    expected_error_type: type[Exception]
    expected_error_fragment: str


@dataclass(frozen=True)
class RuntimeCountTestCase:
    """Repository Python files, chosen roots, and expected runtime count."""

    description: str
    files: tuple[str, ...]
    roots: tuple[str, ...]
    expected_count: int


@dataclass(frozen=True)
class MissingAnswerTestCase:
    """Non-interactive incomplete choices and expected planning failure."""

    description: str
    expected_error_type: type[Exception]
    expected_error_fragment: str


@dataclass(frozen=True)
class DriftTestCase:
    """Tiny real project and expected selected-family drift aggregation."""

    description: str
    source_text: str
    select: tuple[str, ...]
    expected_family_codes: tuple[str, ...]
    expected_family_counts: tuple[int, ...]
    expected_fault_count: int
    expected_file_count: int


@dataclass(frozen=True)
class ExecutionTestCase:
    """Empty scaffold plan and exact written artifacts."""

    description: str
    project_name: str
    expected_created_paths: tuple[str, ...]
    expected_config_text: str
    expected_file_mode: int


@dataclass(frozen=True)
class ExecutionFailureTestCase:
    """Unsafe execution setup and expected all-or-nothing result."""

    description: str
    project_name: str | None
    roots: tuple[str, ...]
    blocking_directory: str | None
    expected_error_type: type[Exception]
    expected_absent_paths: tuple[str, ...]
    expected_preserved_paths: tuple[str, ...]


@dataclass(frozen=True)
class ConfigPathRefusalTestCase:
    """Existing config path kind and expected atomic refusal state."""

    description: str
    path_kind: str
    expected_error_type: type[Exception]
    expected_error_fragment: str
    expected_temp_paths: tuple[str, ...]


@dataclass(frozen=True)
class AtomicRaceTestCase:
    """Concurrent config destination and expected no-overwrite result."""

    description: str
    destination_kind: str
    expected_error_type: type[Exception]
    expected_error_fragment: str
    expected_temp_paths: tuple[str, ...]
    expected_destination_kind: str
    expected_destination_value: str


@dataclass(frozen=True)
class ScaffoldSymlinkTestCase:
    """Scaffold symlink placement and expected rollback state."""

    description: str
    symlink_kind: str
    expected_error_type: type[Exception]
    expected_error_fragment: str
    expected_absent_paths: tuple[str, ...]
    expected_symlink_paths: tuple[str, ...]


@dataclass(frozen=True)
class ScaffoldModeTestCase:
    """Process umask and expected modes for generated scaffold files."""

    description: str
    umask: int
    expected_file_mode: int


@dataclass(frozen=True)
class PublicationFailureTestCase:
    """Direct publication write failure and expected transaction cleanup."""

    description: str
    expected_error_fragment: str
    expected_absent_paths: tuple[str, ...]


@dataclass(frozen=True)
class ParentSwapTestCase:
    """Swapped scaffold parent and expected containment result."""

    description: str
    expected_error_fragment: str
    expected_absent_paths: tuple[str, ...]


@dataclass(frozen=True)
class OptionApplicabilityTestCase:
    """Repository state and options that cannot apply to it."""

    description: str
    is_empty: bool
    roots: tuple[str, ...] | None
    tests: tuple[str, ...] | None
    tooling: tuple[str, ...] | None
    name: str | None
    expected_error_type: type[Exception]
    expected_error_fragment: str


@dataclass(frozen=True)
class EffectiveCandidateTestCase:
    """Partial explicit choices and expected effective candidate transcript."""

    description: str
    explicit_roots: tuple[str, ...]
    expected_plan_roots: tuple[str, ...]
    expected_transcript_fragments: tuple[str, ...]


@dataclass(frozen=True)
class PromptDefaultTestCase:
    """Prompt kind and expected result for an explicit blank line."""

    description: str
    prompt_kind: str
    input_text: str
    expected_result: bool | tuple[str, ...] | str


@dataclass(frozen=True)
class PromptEofTestCase:
    """Prompt kind and expected error for end-of-input."""

    description: str
    prompt_kind: str
    expected_error_type: type[Exception]
    expected_error_fragment: str


@dataclass(frozen=True)
class ScopeSymlinkTestCase:
    """Selected scope containing a Python symlink and expected refusal."""

    description: str
    symlink_path: str
    roots: tuple[str, ...]
    tests: tuple[str, ...]
    tooling: tuple[str, ...]
    expected_error_type: type[Exception]
    expected_error_fragment: str
    expected_config_present: bool


@dataclass(frozen=True)
class GitIgnorePlanTestCase:
    """Initial gitignore bytes and expected cache-ignore update."""

    description: str
    initial: bytes | None
    greenfield: bool
    expected_desired: bytes | None


@dataclass(frozen=True)
class GitIgnoreUnsafeTargetTestCase:
    """Unsafe root gitignore target and expected refusal."""

    description: str
    target_kind: str
    expected_error_fragment: str


@dataclass(frozen=True)
class GitIgnoreExecutionTestCase:
    """Initial root gitignore and expected bytes after complete init execution."""

    description: str
    initial: bytes | None
    expected_gitignore: bytes


@dataclass(frozen=True)
class GitIgnoreMatcherTestCase:
    """Gitignore source and path with expected ordered matcher result."""

    description: str
    initial: bytes
    relative_path: str
    expected_ignored: bool


@dataclass(frozen=True)
class LocalConfigCaptureTestCase:
    """Captured pyproject and racing pathname content with expected local result."""

    description: str
    initial: bytes
    replacement: bytes
    expected_found: bool


@dataclass(frozen=True)
class MetadataMarkerSymlinkTestCase:
    """Metadata-selected package with a symlink marker and expected refusal."""

    description: str
    pyproject_text: str
    marker_path: str
    expected_error_type: type[Exception]
    expected_error_fragment: str
