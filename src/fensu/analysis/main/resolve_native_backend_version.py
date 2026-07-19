"""Resolve the required native analysis extension version."""

from __future__ import annotations

from functools import cache
from importlib import import_module
from importlib.util import find_spec
from types import ModuleType

from fensu.analysis.constants import NATIVE_FACT_MODULE_NAME
from fensu.analysis.exceptions import NativeBackendUnavailableError


@cache
def resolve_native_backend_version() -> str:
    """Return the installed native extension version or raise an actionable error."""

    if find_spec(NATIVE_FACT_MODULE_NAME) is None:
        raise NativeBackendUnavailableError(
            f"The required native analysis module {NATIVE_FACT_MODULE_NAME!r} is not "
            "importable. Reinstall fensu to repair the installation."
        )
    module: ModuleType = import_module(NATIVE_FACT_MODULE_NAME)
    return str(module.backend_version())
