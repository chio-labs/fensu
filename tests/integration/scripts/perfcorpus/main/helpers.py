"""Local helpers for corpus generation tests."""

from __future__ import annotations

import hashlib
from pathlib import Path


def tree_digest(*, root: Path) -> str:
    """Return one deterministic digest of every file beneath a root."""

    chunks: list[bytes] = []
    for path in sorted(filter(Path.is_file, root.rglob("*"))):
        chunks.append(str(path.relative_to(root)).encode("utf-8"))
        chunks.append(path.read_bytes())
    return hashlib.sha256(b"".join(chunks)).hexdigest()


def counted_files(*, root: Path) -> int:
    """Return how many files exist beneath a root."""

    return len(list(filter(Path.is_file, root.rglob("*"))))
