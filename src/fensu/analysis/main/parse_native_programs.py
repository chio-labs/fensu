"""Parse many decoded sources in parallel through the required native analyzer."""

from __future__ import annotations

import sys
from collections.abc import Sequence
from importlib import import_module
from types import ModuleType

from fensu.analysis.constants import NATIVE_FACT_MODULE_NAME
from fensu.instrumentation.constants import NATIVE_PARSE_OPERATION, OPERATION_COUNTERS


def parse_native_programs(*, sources: Sequence[str]) -> tuple[object | None, ...]:
    """Return one native program handle per source, or None where parsing fails."""

    native: ModuleType = import_module(NATIVE_FACT_MODULE_NAME)
    for _ in sources:
        OPERATION_COUNTERS.record(operation=NATIVE_PARSE_OPERATION)
    programs: list[object | None] = native.parse_programs(
        list(sources),
        sys.version_info[0],
        sys.version_info[1],
    )
    return tuple(programs)
