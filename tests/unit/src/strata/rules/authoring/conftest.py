"""Fixtures for rule authoring tests."""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from strata.rules.authoring.main.collect import collect_registered


@pytest.fixture(autouse=True)
def clear_registry() -> Iterator[None]:
    collect_registered()
    yield
    collect_registered()
