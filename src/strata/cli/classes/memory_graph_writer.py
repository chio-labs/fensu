"""CLI output adapter for bounded memory graph retrieval."""

from __future__ import annotations

import argparse
from typing import TextIO

from strata.memory.main.run_memory_graph import run_memory_graph


class MemoryGraphWriter:
    """Write separated graph and synchronization output."""

    @staticmethod
    def write(
        *,
        args: argparse.Namespace,
        stdout: TextIO,
        stderr: TextIO,
        use_color: bool,
    ) -> None:
        """Execute one graph request and write its two output channels."""

        sync_text, graph_text = run_memory_graph(
            pattern=args.pattern,
            direction=args.direction,
            relationships=tuple(args.relationships),
            depth=args.depth,
            max_nodes=args.max_nodes,
            max_edges=args.max_edges,
            include_archived=args.include_archived,
            output_format=args.output_format,
            use_color=use_color,
        )
        stderr.write(sync_text)
        stdout.write(graph_text)
