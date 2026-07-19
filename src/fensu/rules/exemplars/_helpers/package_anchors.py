"""Dependency-recording package anchor helpers for public custom rules."""

from pathlib import Path

from fensu import RuleContext


def is_package_anchor(*, ctx: RuleContext, package_dir: Path) -> bool:
    """Return whether the current file deterministically owns a package diagnostic."""

    init_path: Path = package_dir / "__init__.py"
    if ctx.project.exists(requester=ctx.path, path=init_path):
        return ctx.path == init_path
    modules: tuple[Path, ...] = tuple(
        sorted(
            ctx.project.glob(
                requester=ctx.path,
                path=package_dir,
                pattern="*.py",
                recursive=True,
            )
        )
    )
    return bool(modules) and ctx.path == modules[0]
