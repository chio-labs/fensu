"""Build and render deterministic project call maps."""

from __future__ import annotations

from pathlib import Path

from strata.mapping.core.helpers.render import render_tree
from strata.mapping.core.models import CallMapNode, MappingSource
from strata.mapping.core.types import CallMapProvider, PathMode


def build_call_map(
    *,
    sources: tuple[MappingSource, ...],
    symbol: str,
    depth: int,
    repo_root: Path,
    provider: CallMapProvider,
    path_mode: PathMode = PathMode.RELATIVE,
    use_color: bool = False,
) -> str:
    """Build and render one downstream project call map."""

    root: CallMapNode = provider(sources=sources, symbol=symbol, depth=depth)
    return render_tree(
        root=root,
        repo_root=repo_root,
        path_mode=path_mode,
        use_color=use_color,
    )
