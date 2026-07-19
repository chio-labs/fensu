"""Generate one deterministic SQLBuild-shaped performance corpus."""

from __future__ import annotations

import random
from types import MappingProxyType

from scripts.perfcorpus._helpers.layout import (
    domain_count,
    scaffolding_files,
    write_corpus_files,
)
from scripts.perfcorpus._helpers.naming import build_domain_names
from scripts.perfcorpus._helpers.runtime_sources import render_runtime_domain
from scripts.perfcorpus._helpers.test_sources import render_domain_tests
from scripts.perfcorpus.constants import HELPER_MODULE_NAMES
from scripts.perfcorpus.models import CorpusSpec, CorpusSummary, RenderedFiles


def generate_corpus(*, spec: CorpusSpec) -> CorpusSummary:
    """Write one seeded corpus and return its deterministic summary."""

    domains: tuple[str, ...] = build_domain_names(count=domain_count(file_target=spec.file_target))
    rng: random.Random = random.Random(spec.seed)
    files: dict[str, str] = dict(scaffolding_files())
    faults: int = 0
    for index, domain in enumerate(domains):
        dependency: str = _choose_dependency(domains=domains, index=index, rng=rng)
        runtime: RenderedFiles = render_runtime_domain(
            domain=domain,
            dependency=dependency,
            helper_offset=index * len(HELPER_MODULE_NAMES),
            annotation_fault_every=spec.annotation_fault_every,
            magic_fault_every=spec.magic_fault_every,
        )
        tests: RenderedFiles = render_domain_tests(domain=domain)
        files.update(runtime.files)
        files.update(tests.files)
        faults += runtime.faults
    written: int = write_corpus_files(target=spec.target, files=MappingProxyType(files))
    return CorpusSummary(files_written=written, domains=len(domains), faults_expected=faults)


def _choose_dependency(
    *,
    domains: tuple[str, ...],
    index: int,
    rng: random.Random,
) -> str:
    choice: int = rng.randrange(len(domains) - 1)
    adjusted: int = choice + 1 if choice >= index else choice
    return domains[adjusted]
