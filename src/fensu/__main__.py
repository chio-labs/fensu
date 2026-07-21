"""Reject the retired Python module command entrypoint."""

from __future__ import annotations

import sys


def main() -> int:
    """Direct built-in command users to the native CLI package."""

    sys.stderr.write(
        "`python -m fensu` has been retired; install and run the native `fensu` command "
        "from the fensu-cli package.\n"
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
