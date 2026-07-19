"""Corpus scaffolding and deterministic file writing."""

from __future__ import annotations

from pathlib import Path
from types import MappingProxyType

from scripts.perfcorpus.constants import (
    FENSU_CONFIG,
    FILES_PER_DOMAIN,
    MINIMUM_DOMAINS,
    PACKAGE_NAME,
    SOURCE_ROOT,
    TEST_SCOPE,
    TESTS_ROOT,
)

_SCAFFOLD_INIT_CONTENT: str = '"""Generated corpus package."""\n'


def domain_count(*, file_target: int) -> int:
    """Return how many domains approximate the requested file count."""

    return max(MINIMUM_DOMAINS, file_target // FILES_PER_DOMAIN)


def scaffolding_files() -> MappingProxyType[str, str]:
    """Return the corpus-level configuration and package scaffolding."""

    files: dict[str, str] = {
        "fensu.toml": FENSU_CONFIG,
        f"{SOURCE_ROOT}/{PACKAGE_NAME}/__init__.py": _SCAFFOLD_INIT_CONTENT,
        f"{TESTS_ROOT}/__init__.py": _SCAFFOLD_INIT_CONTENT,
        f"{TESTS_ROOT}/{TEST_SCOPE}/__init__.py": _SCAFFOLD_INIT_CONTENT,
        f"{TESTS_ROOT}/{TEST_SCOPE}/{SOURCE_ROOT}/__init__.py": _SCAFFOLD_INIT_CONTENT,
        f"{TESTS_ROOT}/{TEST_SCOPE}/{SOURCE_ROOT}/{PACKAGE_NAME}/__init__.py": (
            _SCAFFOLD_INIT_CONTENT
        ),
    }
    return MappingProxyType(files)


def write_corpus_files(*, target: Path, files: MappingProxyType[str, str]) -> int:
    """Write rendered files beneath the target and return the count written."""

    written: int = 0
    for relative_path in sorted(files):
        destination: Path = target / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(files[relative_path], encoding="utf-8")
        written += 1
    return written
