"""Load release metadata snapshots from Git revisions."""

from __future__ import annotations

import subprocess
import tomllib
from pathlib import Path

from scripts.release_metadata.constants import ALLOWED_PATHS
from scripts.release_metadata.models import ReleaseDelta


def load_release_delta(*, repo_root: Path, base_ref: str, head_ref: str) -> ReleaseDelta:
    """Read the changed metadata and package versions from two Git revisions."""

    changed: list[str] = _git(
        "diff", "--name-only", base_ref, head_ref, repo_root=repo_root
    ).splitlines()
    base_files: dict[str, str] = {
        path: _git("show", f"{base_ref}:{path}", repo_root=repo_root) for path in ALLOWED_PATHS
    }
    head_files: dict[str, str] = {
        path: _git("show", f"{head_ref}:{path}", repo_root=repo_root) for path in ALLOWED_PATHS
    }
    old_version: str = tomllib.loads(base_files["pyproject.toml"])["project"]["version"]
    new_version: str = tomllib.loads(head_files["pyproject.toml"])["project"]["version"]
    return ReleaseDelta(
        old_version=old_version,
        new_version=new_version,
        changed_paths=frozenset(changed),
        base_files=base_files,
        head_files=head_files,
    )


def _git(*arguments: str, repo_root: Path) -> str:
    result: subprocess.CompletedProcess[str] = subprocess.run(
        ["git", *arguments],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout
