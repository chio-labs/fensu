"""Module fallback for environments where the native console script is unavailable."""

from __future__ import annotations

from strata.cli.main.entry import main

if __name__ == "__main__":
    raise SystemExit(main())
