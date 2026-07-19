"""Test case types for project-specific skill identity and root resolution."""

from dataclasses import dataclass


@dataclass(frozen=True)
class SkillNormalizationTestCase:
    """Raw project identity and expected stable kebab value."""

    description: str
    value: str
    expected_identity: str


@dataclass(frozen=True)
class GitMarkerTestCase:
    """Git metadata marker form and expected repository-root discovery."""

    description: str
    marker_kind: str
    expected_found: bool


@dataclass(frozen=True)
class InstallRootTestCase:
    """Install-root option and expected path relative to the workspace."""

    description: str
    value: str | None
    expected_relative_root: str
