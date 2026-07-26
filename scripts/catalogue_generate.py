"""Generate the checked-in native core catalogue asset."""

from __future__ import annotations

import sys

from scripts.catalogue.main.generate_catalogue import generate_catalogue


def main() -> int:
    """Delegate catalogue generation to its tooling entry."""

    return generate_catalogue(arguments=sys.argv[1:])


if __name__ == "__main__":
    raise SystemExit(main())
