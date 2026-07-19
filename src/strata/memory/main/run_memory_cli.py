"""Load the Strata Memory CLI adapter on explicit command dispatch."""

from __future__ import annotations

from strata.cli.main.memory import run_memory


def run_memory_cli(*, argv: tuple[str, ...] | None = None) -> int:
    """Run the stream-oriented Strata Memory CLI adapter."""

    return run_memory(argv=argv)
