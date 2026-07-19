"""Public custom test-layout decision shared by FFT001-FFT008 exemplars."""

from pathlib import Path

from fensu import RuleContext, ScopeName
from fensu.rules.exemplars.types import (
    ExemplarTestAreaName,
    ExemplarTestLimit,
    ExemplarTestScopeName,
    LayoutIssue,
)


def layout_issue(*, ctx: RuleContext) -> LayoutIssue | None:
    """Return the first test mirror issue using public roots and existence queries."""

    directories: tuple[str, ...] = ctx.relative_parts()[:-1]
    if len(directories) < int(ExemplarTestLimit.MINIMUM_PATH_PARTS):
        return "FFT001", "test directories must live under <configured-tests>/<scope>/..."
    if directories[0] not in set(ExemplarTestScopeName):
        return "FFT002", "test scope must be unit, integration, or e2e"
    mirrored: tuple[str, ...] = directories[1:]
    root_items: list[tuple[ScopeName, Path]] = []
    for candidate_scope in (ScopeName.ROOT, ScopeName.TOOLING):
        root_items.extend((candidate_scope, root) for root in ctx.scope_roots(candidate_scope))
    roots: tuple[tuple[ScopeName, Path], ...] = tuple(root_items)
    matches: tuple[tuple[ScopeName, Path], ...] = tuple(
        (scope, root)
        for scope, root in roots
        if mirrored[: len(root.relative_to(ctx.repo_root).parts)]
        == root.relative_to(ctx.repo_root).parts
    )
    if matches:
        scope, root = max(matches, key=lambda item: len(item[1].parts))
        root_parts: tuple[str, ...] = root.relative_to(ctx.repo_root).parts
        if len(mirrored) <= len(root_parts):
            return (
                ("FFT004", "runtime tests must include an area beneath the configured source root")
                if scope is ScopeName.ROOT
                else (
                    "FFT007",
                    "tooling tests must include an area beneath the configured tooling root",
                )
            )
        area: str = mirrored[len(root_parts)]
        if scope is ScopeName.ROOT and area == ExemplarTestAreaName.ROOT:
            return None
        if not ctx.project.exists(requester=ctx.path, path=root / area):
            return (
                ("FFT006", "runtime tests must mirror a real configured source package area")
                if scope is ScopeName.ROOT
                else ("FFT008", "tooling tests must mirror a real configured tooling area")
            )
        return None
    for root in ctx.scope_roots(ScopeName.ROOT):
        root_parts = root.relative_to(ctx.repo_root).parts
        container: tuple[str, ...] = root_parts[:-1]
        if mirrored[: len(container)] == container:
            if len(mirrored) <= len(container):
                return "FFT004", "runtime tests must mirror a configured package and area"
            return "FFT005", "runtime tests must mirror a configured source package"
    return "FFT003", "test directories must mirror a configured runtime or tooling root"
