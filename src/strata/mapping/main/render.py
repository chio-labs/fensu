"""Render one already-resolved call tree."""

from pathlib import Path

from strata.mapping.helpers.render import render_tree
from strata.mapping.models import CallMapNode
from strata.mapping.types import PathMode


def render_call_tree(
    *, root: CallMapNode, repo_root: Path, path_mode: PathMode, use_color: bool
) -> str:
    """Render one call tree with the established byte-stable presentation."""

    return render_tree(root=root, repo_root=repo_root, path_mode=path_mode, use_color=use_color)
