"""Load one top-level public attribute from its owning module."""

from __future__ import annotations

from functools import cache
from importlib import import_module
from types import ModuleType

from strata.public_api.constants import PUBLIC_ATTRIBUTES
from strata.public_api.exceptions import UnknownPublicAttributeError


@cache
def load_public_attribute(name: str) -> object:
    """Return one lazily imported top-level public attribute."""

    owner: tuple[str, str] | None = PUBLIC_ATTRIBUTES.get(name)
    if owner is None:
        raise UnknownPublicAttributeError(f"module 'strata' has no attribute {name!r}")
    module_name, attribute_name = owner
    module: ModuleType = import_module(module_name)
    return getattr(module, attribute_name)
