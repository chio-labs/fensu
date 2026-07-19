"""Render call-map trees as deterministic terminal text."""

from __future__ import annotations

from pathlib import Path

from fensu.mapping.constants import (
    ANSI_CYCLE,
    ANSI_DIM,
    ANSI_FUNCTION,
    ANSI_RESET,
    ANSI_UNRESOLVED,
    MAX_COMPACT_PATH_PARTS,
)
from fensu.mapping.models import CallMapNode, UnresolvedCall
from fensu.mapping.types import PathMode


def render_tree(
    *,
    root: CallMapNode,
    repo_root: Path,
    path_mode: PathMode = PathMode.RELATIVE,
    use_color: bool = False,
) -> str:
    """Render one call tree with locations, cycle markers, and depth markers."""

    child_lines: tuple[str, ...] = _child_lines(
        node=root,
        repo_root=repo_root,
        path_mode=path_mode,
        prefix="",
        use_color=use_color,
    )
    root_label: str = _label(
        node=root, repo_root=repo_root, path_mode=path_mode, use_color=use_color
    )
    return "\n".join((root_label, *child_lines)) + "\n"


def _child_lines(
    *,
    node: CallMapNode,
    repo_root: Path,
    path_mode: PathMode,
    prefix: str,
    use_color: bool,
) -> tuple[str, ...]:
    lines: list[str] = []
    for index, entry in enumerate(node.entries):
        last: bool = index == len(node.entries) - 1
        connector: str = "└── " if last else "├── "
        rendered_connector: str = _color(
            text=f"{prefix}{connector}", style=ANSI_DIM, enabled=use_color
        )
        if isinstance(entry, UnresolvedCall):
            location: str = _location(
                path=node.definition.path,
                line=entry.line,
                repo_root=repo_root,
                path_mode=path_mode,
            )
            label: str = _color(text=f"{entry.name}(...)", style=ANSI_FUNCTION, enabled=use_color)
            rendered_location: str = _color(text=location, style=ANSI_DIM, enabled=use_color)
            marker: str = _color(
                text=f"(unresolved {entry.reason})",
                style=ANSI_UNRESOLVED,
                enabled=use_color,
            )
            lines.append(f"{rendered_connector}{label}{rendered_location}  {marker}")
            continue
        label = _label(
            node=entry,
            repo_root=repo_root,
            path_mode=path_mode,
            use_color=use_color,
        )
        lines.append(f"{rendered_connector}{label}")
        child_prefix: str = f"{prefix}{'    ' if last else '│   '}"
        lines.extend(
            _child_lines(
                node=entry,
                repo_root=repo_root,
                path_mode=path_mode,
                prefix=child_prefix,
                use_color=use_color,
            )
        )
    return tuple(lines)


def _label(*, node: CallMapNode, repo_root: Path, path_mode: PathMode, use_color: bool) -> str:
    display_name: str = (
        f"{node.dispatch_class_name}.{node.definition.name}"
        if node.dispatch_class_name is not None
        else node.definition.display_name
    )
    function: str = _color(text=f"{display_name}(...)", style=ANSI_FUNCTION, enabled=use_color)
    location: str = _location(
        path=node.definition.path,
        line=node.definition.syntax.line,
        repo_root=repo_root,
        path_mode=path_mode,
    )
    rendered_location: str = _color(text=location, style=ANSI_DIM, enabled=use_color)
    if node.cycle:
        marker: str = _color(text="  (cycle)", style=ANSI_CYCLE, enabled=use_color)
    elif node.truncated:
        marker = _color(text="  (depth limit)", style=ANSI_DIM, enabled=use_color)
    else:
        marker = ""
    return f"{function}{rendered_location}{marker}"


def _location(*, path: Path, line: int, repo_root: Path, path_mode: PathMode) -> str:
    if path_mode is PathMode.NONE:
        return ""
    display_path: Path = path
    if path_mode is not PathMode.ABSOLUTE and path.is_relative_to(repo_root):
        display_path = path.relative_to(repo_root)
    path_text: str = display_path.as_posix()
    if path_mode is PathMode.COMPACT:
        path_text = _compact_path(path_text)
    return f"  {path_text}:{line}"


def _compact_path(path: str) -> str:
    parts: tuple[str, ...] = tuple(path.split("/"))
    if len(parts) <= MAX_COMPACT_PATH_PARTS:
        return path
    return "/".join((*parts[:2], "…", *parts[-2:]))


def _color(*, text: str, style: str, enabled: bool) -> str:
    if not text or not enabled:
        return text
    return f"{style}{text}{ANSI_RESET}"
