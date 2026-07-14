"""Parse many decoded sources in parallel through the native fact backend."""

from __future__ import annotations

import sys
from collections.abc import Sequence
from importlib import import_module
from types import ModuleType

from strata.analysis.constants import NATIVE_FACT_MODULE_NAME
from strata.analysis.main.select_fact_backend import select_fact_backend
from strata.analysis.types import FactBackend
from strata.instrumentation.constants import NATIVE_PARSE_OPERATION, OPERATION_COUNTERS


def parse_native_programs(*, sources: Sequence[str]) -> tuple[object | None, ...]:
    """Return one native program handle per source, or None where unavailable."""

    if select_fact_backend().backend is not FactBackend.NATIVE:
        return tuple(None for _ in sources)
    native: ModuleType = import_module(NATIVE_FACT_MODULE_NAME)
    for _ in sources:
        OPERATION_COUNTERS.record(operation=NATIVE_PARSE_OPERATION)
    programs: list[object | None] = native.parse_programs(
        list(sources),
        sys.version_info[0],
        sys.version_info[1],
    )
    return tuple(programs)
