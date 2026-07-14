"""Parse one decoded source through the active native fact backend."""

from __future__ import annotations

import sys
from importlib import import_module
from types import ModuleType

from strata.analysis.constants import NATIVE_FACT_MODULE_NAME
from strata.analysis.main.select_fact_backend import select_fact_backend
from strata.analysis.types import FactBackend
from strata.instrumentation.constants import NATIVE_PARSE_OPERATION, OPERATION_COUNTERS


def parse_native_program(*, source: str) -> object | None:
    """Return a native program handle, or None when native parsing is unavailable."""

    if select_fact_backend().backend is not FactBackend.NATIVE:
        return None
    native: ModuleType = import_module(NATIVE_FACT_MODULE_NAME)
    OPERATION_COUNTERS.record(operation=NATIVE_PARSE_OPERATION)
    try:
        return native.parse_program(source, sys.version_info[0], sys.version_info[1])
    except ValueError:
        return None
