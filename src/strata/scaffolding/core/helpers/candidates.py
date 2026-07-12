"""Normalize, bound, and deduplicate detected path candidates."""

from __future__ import annotations

from pathlib import Path

from strata.scaffolding.core.models import PathCandidate
from strata.scaffolding.core.types import CandidateInput


def ordered_candidates(
    *, repository: Path, inputs: tuple[CandidateInput, ...], allow_absent: bool = False
) -> tuple[PathCandidate, ...]:
    """Keep first-ranked aliases and render paths relative to the repository."""

    candidates: list[PathCandidate] = []
    seen: set[Path] = set()
    for path, provenance in inputs:
        resolved: Path = path.resolve()
        if not _is_within(repository=repository, path=resolved):
            continue
        present: bool = resolved.is_dir()
        if not present and not allow_absent:
            continue
        if resolved in seen:
            continue
        seen.add(resolved)
        relative: Path = resolved.relative_to(repository)
        relative_text: str = relative.as_posix()
        candidates.append(PathCandidate(path=relative_text, provenance=provenance, present=present))
    return tuple(candidates)


def _is_within(*, repository: Path, path: Path) -> bool:
    try:
        path.relative_to(repository)
    except ValueError:
        return False
    return True
