"""Temporary repository helpers for native Strata Memory integration."""

from __future__ import annotations

from pathlib import Path


def write_enabled_memory_project(*, root: Path) -> None:
    """Write the minimum enabled Strata project used by native memory tests."""

    source_root: Path = root / "src" / "pkg"
    source_root.mkdir(parents=True)
    (source_root / "__init__.py").write_text("", encoding="utf-8")
    (root / "strata.toml").write_text(
        'roots = ["src/pkg"]\n[memory]\nenabled = true\n',
        encoding="utf-8",
    )
