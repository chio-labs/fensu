"""Release metadata validation test cases."""

from dataclasses import dataclass

from scripts.release_metadata.models import ReleaseDelta


@dataclass(frozen=True)
class ReleaseDeltaTestCase:
    """One generated or tampered release delta."""

    description: str
    delta: ReleaseDelta
    expected_errors: list[str]
