"""Agent skill installation models."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from strata.agentdocs.types import SkillFreshnessReason, SkillTarget
from strata.config.models import Config, ConfigSource
from strata.rules.authoring.models import RuleSpec


@dataclass(frozen=True, slots=True)
class SkillGenerationContext:
    """Complete immutable input to deterministic skill rendering."""

    config_source: ConfigSource
    project_root: Path
    install_root: Path
    git_root: Path | None
    project_prefix: str
    identity: str
    catalogue: tuple[RuleSpec, ...]
    blocking_rules: tuple[RuleSpec, ...]
    warning_rules: tuple[RuleSpec, ...]
    ignored_rules: tuple[RuleSpec, ...]
    config: Config


@dataclass(frozen=True, slots=True)
class SkillInstallTarget:
    """One agent-specific skill destination."""

    name: SkillTarget
    path: Path


@dataclass(frozen=True, slots=True)
class ProjectSkillFile:
    """One regular file captured from a canonical project skill bundle."""

    relative_path: Path
    content: bytes
    mode: int


@dataclass(frozen=True, slots=True)
class ProjectSkillBundle:
    """One canonical active project skill bundle and all of its files."""

    identity: str
    files: tuple[ProjectSkillFile, ...]


@dataclass(frozen=True, slots=True)
class ProjectSkillInstallTarget:
    """One project bundle destination for one selected agent target."""

    name: SkillTarget
    path: Path
    bundle: ProjectSkillBundle


@dataclass(frozen=True, slots=True)
class SkillUpdateResult:
    """Files written by one skills invocation."""

    written_paths: tuple[Path, ...]


@dataclass(frozen=True, slots=True)
class SkillOwnership:
    """Structured ownership metadata embedded in generated skill files."""

    schema: int
    identity: str
    owner: str
    input_fingerprint: str
    content_fingerprint: str


@dataclass(frozen=True, slots=True)
class SkillInstallPlan:
    """Pure expected installation inputs shared by update and freshness checks."""

    context: SkillGenerationContext
    targets: tuple[SkillInstallTarget, ...]
    project_targets: tuple[ProjectSkillInstallTarget, ...]
    legacy_paths: tuple[Path, ...]
    owner: str
    input_fingerprint: str
    synchronize_project_skills: bool


@dataclass(frozen=True, slots=True)
class SkillFreshnessIssue:
    """One expected target and its deterministic non-current reason."""

    path: Path
    reason: SkillFreshnessReason


@dataclass(frozen=True, slots=True)
class SkillFreshnessResult:
    """Bounded expected-target inspection result."""

    inspected_paths: tuple[Path, ...]
    issues: tuple[SkillFreshnessIssue, ...]
