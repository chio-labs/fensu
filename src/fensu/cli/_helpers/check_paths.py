"""Resolve check invocation path overrides."""

from pathlib import Path


def invocation_path(*, value: str, invocation_dir: Path) -> str:
    """Return one positional check path resolved from the invocation directory."""

    path: Path = Path(value)
    return str(path.resolve() if path.is_absolute() else (invocation_dir / path).resolve())
