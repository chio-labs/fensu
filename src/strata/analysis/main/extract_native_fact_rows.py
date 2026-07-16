"""Extract native fact rows for many parsed programs in one parallel batch."""

from __future__ import annotations

from collections.abc import Sequence
from importlib import import_module
from types import ModuleType

from strata.analysis.constants import NATIVE_FACT_MODULE_NAME


def extract_native_fact_rows(*, requests: Sequence[tuple[object, tuple[str, ...]]]) -> int:
    """Cache the requested fact-family rows on each native program handle."""

    if not requests:
        return 0
    native: ModuleType = import_module(NATIVE_FACT_MODULE_NAME)
    prepared: list[tuple[object, list[str]]] = [
        (program, list(families)) for program, families in requests
    ]
    extracted: int = native.extract_fact_rows(prepared)
    return extracted
