"""Portable filesystem capability checks for scaffold publication."""

from __future__ import annotations

import os
from collections.abc import Iterable

_DIR_FD_OPERATIONS: tuple[object, ...] = (os.open, os.mkdir, os.stat, os.unlink)


def supports_dir_fd_operations() -> bool:
    """Return whether every operation needed by descriptor traversal supports dir_fd."""

    supported: object = getattr(os, "supports_dir_fd", None)
    if not isinstance(supported, Iterable):
        return False
    supported_operations: frozenset[object] = frozenset(supported)
    return all(operation in supported_operations for operation in _DIR_FD_OPERATIONS)
