"""Convert scoped Python files into importable dotted module paths."""

from __future__ import annotations

from pathlib import Path

from strata.discovery.core.helpers.position import relative_parts


def module_path(*, path: Path, root: Path) -> str:
    """Return the dotted module path for a Python file relative to its scope root."""

    parts: tuple[str, ...] = relative_parts(path=path, root=root)
    module_parts: tuple[str, ...] = (*parts[:-1], parts[-1].removesuffix(".py"))
    if module_parts[-1] == "__init__":
        module_parts = module_parts[:-1]
    return ".".join(module_parts)
