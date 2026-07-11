"""Persistent cache fingerprint models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CacheFingerprint:
    """One lowercase hexadecimal SHA-256 cache identity."""

    value: str


@dataclass(frozen=True, slots=True)
class FileResultFingerprints:
    """Correctness identity and full-record integrity for one file result."""

    result: CacheFingerprint
    record: CacheFingerprint
