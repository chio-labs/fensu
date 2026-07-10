"""Build and render deterministic project call maps."""

from __future__ import annotations

from pathlib import Path

from strata.config.core.models import Config
from strata.mapping.core.helpers.render import render_tree
from strata.mapping.core.models import CallMapNode
from strata.mapping.core.types import CallMapProvider


def build_call_map(
    *,
    config: Config,
    symbol: str,
    depth: int,
    repo_root: Path,
    provider: CallMapProvider,
) -> str:
    """Build and render one downstream project call map."""

    root: CallMapNode = provider(config=config, symbol=symbol, depth=depth)
    return render_tree(root=root, repo_root=repo_root)
