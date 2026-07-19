"""Load the Fensu Memory CLI adapter on explicit command dispatch."""

from __future__ import annotations

from fensu.cli.main.memory import run_memory


def run_memory_cli(*, argv: tuple[str, ...] | None = None) -> int:
    """Run the stream-oriented Fensu Memory CLI adapter."""

    return run_memory(argv=argv)
