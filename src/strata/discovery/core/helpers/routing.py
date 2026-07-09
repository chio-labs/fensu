"""Route discovered scopes to the rule families that apply to them."""

from __future__ import annotations

from strata.discovery.core.constants import ROOT_FAMILIES, TEST_FAMILIES, TOOLING_FAMILIES
from strata.discovery.core.models import ScopedFile
from strata.rules.authoring.types import Family


def families_for_scope(scoped_file: ScopedFile) -> frozenset[Family]:
    """Return the rule families that apply to a discovered file's scope."""

    if scoped_file.scope == "root":
        return ROOT_FAMILIES
    if scoped_file.scope == "test":
        return TEST_FAMILIES
    return TOOLING_FAMILIES
