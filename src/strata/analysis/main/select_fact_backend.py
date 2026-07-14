"""Select the fact backend used to construct semantic file facts."""

from __future__ import annotations

import os
from functools import cache
from importlib import import_module
from importlib.util import find_spec
from types import ModuleType

from strata.analysis.constants import FACT_BACKEND_ENV_VARIABLE, NATIVE_FACT_MODULE_NAME
from strata.analysis.exceptions import NativeBackendUnavailableError
from strata.analysis.models import FactBackendSelection
from strata.analysis.types import FactBackend


@cache
def select_fact_backend() -> FactBackendSelection:
    """Return the process-wide resolved fact backend selection."""

    requested: str = os.environ.get(FACT_BACKEND_ENV_VARIABLE, "").strip().lower()
    native_version: str | None = _native_backend_version()
    if requested == FactBackend.PYTHON:
        return FactBackendSelection(
            backend=FactBackend.PYTHON,
            native_version=native_version,
            warning=None,
        )
    if requested and requested != FactBackend.NATIVE:
        if native_version is None:
            raise _unavailable_error()
        return FactBackendSelection(
            backend=FactBackend.NATIVE,
            native_version=native_version,
            warning=(
                f"Unknown {FACT_BACKEND_ENV_VARIABLE} value {requested!r}; expected "
                f"{FactBackend.PYTHON.value!r} or {FactBackend.NATIVE.value!r}."
            ),
        )
    if native_version is None:
        raise _unavailable_error()
    return FactBackendSelection(
        backend=FactBackend.NATIVE,
        native_version=native_version,
        warning=None,
    )


def _unavailable_error() -> NativeBackendUnavailableError:
    return NativeBackendUnavailableError(
        f"The required native analysis module {NATIVE_FACT_MODULE_NAME!r} is not "
        "importable. Reinstall stratalint to repair the installation, or set "
        f"{FACT_BACKEND_ENV_VARIABLE}={FactBackend.PYTHON.value} to run the "
        "unsupported pure-Python reference backend."
    )


def _native_backend_version() -> str | None:
    if find_spec(NATIVE_FACT_MODULE_NAME) is None:
        return None
    module: ModuleType = import_module(NATIVE_FACT_MODULE_NAME)
    return str(module.backend_version())
