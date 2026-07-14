"""Select the fact backend used to construct semantic file facts."""

from __future__ import annotations

import os
from functools import cache
from importlib import import_module
from importlib.util import find_spec
from types import ModuleType

from strata.analysis.constants import FACT_BACKEND_ENV_VARIABLE, NATIVE_FACT_MODULE_NAME
from strata.analysis.models import FactBackendSelection
from strata.analysis.types import FactBackend


@cache
def select_fact_backend() -> FactBackendSelection:
    """Return the process-wide resolved fact backend selection."""

    requested: str = os.environ.get(FACT_BACKEND_ENV_VARIABLE, "").strip().lower()
    native_version: str | None = _native_backend_version()
    default_backend: FactBackend = (
        FactBackend.PYTHON if native_version is None else FactBackend.NATIVE
    )
    if requested == FactBackend.PYTHON:
        return FactBackendSelection(
            backend=FactBackend.PYTHON,
            native_version=native_version,
            warning=None,
        )
    if requested == FactBackend.NATIVE and native_version is None:
        return FactBackendSelection(
            backend=FactBackend.PYTHON,
            native_version=None,
            warning=(
                f"The {FactBackend.NATIVE.value} fact backend was requested but "
                f"{NATIVE_FACT_MODULE_NAME} is not installed; using the "
                f"{FactBackend.PYTHON.value} backend."
            ),
        )
    if requested == FactBackend.NATIVE:
        return FactBackendSelection(
            backend=FactBackend.NATIVE,
            native_version=native_version,
            warning=None,
        )
    if requested:
        return FactBackendSelection(
            backend=default_backend,
            native_version=native_version,
            warning=(
                f"Unknown {FACT_BACKEND_ENV_VARIABLE} value {requested!r}; expected "
                f"{FactBackend.PYTHON.value!r} or {FactBackend.NATIVE.value!r}."
            ),
        )
    return FactBackendSelection(
        backend=default_backend,
        native_version=native_version,
        warning=None,
    )


def _native_backend_version() -> str | None:
    if find_spec(NATIVE_FACT_MODULE_NAME) is None:
        return None
    module: ModuleType = import_module(NATIVE_FACT_MODULE_NAME)
    return str(module.backend_version())
