"""Run trusted release metadata validation from Git revisions."""

from pathlib import Path

from scripts.release_metadata._helpers.loading import load_release_delta
from scripts.release_metadata.main.validate_release_delta import get_release_delta_errors
from scripts.release_metadata.models import ReleaseDelta


def run_release_metadata_check(*, repo_root: Path, base_ref: str, head_ref: str) -> int:
    """Load one release delta, render every error, and return its status."""

    delta: ReleaseDelta = load_release_delta(
        repo_root=repo_root,
        base_ref=base_ref,
        head_ref=head_ref,
    )
    errors: list[str] = get_release_delta_errors(delta)
    for error in errors:
        print(f"release metadata error: {error}")
    return int(bool(errors))
