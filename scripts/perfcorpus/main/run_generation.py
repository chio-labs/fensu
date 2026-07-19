"""Run one corpus generation request and report its summary."""

from __future__ import annotations

from pathlib import Path

from scripts.perfcorpus.main.generate_corpus import generate_corpus
from scripts.perfcorpus.models import CorpusSpec, CorpusSummary


def run_generation(*, target: Path, files: int, seed: int) -> int:
    """Generate one seeded corpus, print its summary, and return an exit code."""

    summary: CorpusSummary = generate_corpus(
        spec=CorpusSpec(target=target, file_target=files, seed=seed)
    )
    print(
        f"files={summary.files_written} domains={summary.domains} faults={summary.faults_expected}"
    )
    return 0
