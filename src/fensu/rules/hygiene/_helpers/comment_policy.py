"""Fixed standalone-comment policy values."""

from __future__ import annotations


def get_allowed_standalone_comment_prefixes() -> tuple[str, ...]:
    """Return exhaustive tooling-directive prefixes accepted by FFH002."""

    return (
        "#!",
        "# -*-",
        "# coding:",
        "# noqa",
        "# type:",
        "# pyright:",
        "# pylint:",
        "# pragma:",
    )
