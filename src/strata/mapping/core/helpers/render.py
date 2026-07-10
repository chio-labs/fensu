"""Render call-map trees as deterministic terminal text."""

from __future__ import annotations

from pathlib import Path

from strata.mapping.core.models import CallMapNode, UnresolvedCall


def render_tree(*, root: CallMapNode, repo_root: Path) -> str:
    """Render one call tree with locations, cycle markers, and depth markers."""

    child_lines: tuple[str, ...] = _child_lines(node=root, repo_root=repo_root, prefix="")
    return "\n".join((_label(node=root, repo_root=repo_root), *child_lines)) + "\n"


def _child_lines(*, node: CallMapNode, repo_root: Path, prefix: str) -> tuple[str, ...]:
    lines: list[str] = []
    entries: tuple[CallMapNode | UnresolvedCall, ...] = (*node.children, *node.unresolved_calls)
    for index, entry in enumerate(entries):
        last: bool = index == len(entries) - 1
        connector: str = "└── " if last else "├── "
        if isinstance(entry, UnresolvedCall):
            location: Path = node.definition.path.relative_to(repo_root)
            lines.append(
                f"{prefix}{connector}{entry.name}(...)  {location}:{entry.line}  "
                f"(unresolved {entry.reason})"
            )
            continue
        lines.append(f"{prefix}{connector}{_label(node=entry, repo_root=repo_root)}")
        child_prefix: str = f"{prefix}{'    ' if last else '│   '}"
        lines.extend(_child_lines(node=entry, repo_root=repo_root, prefix=child_prefix))
    return tuple(lines)


def _label(*, node: CallMapNode, repo_root: Path) -> str:
    location: Path = node.definition.path.relative_to(repo_root)
    marker: str = "  (cycle)" if node.cycle else "  (depth limit)" if node.truncated else ""
    return f"{node.definition.name}(...)  {location}:{node.definition.node.lineno}{marker}"
