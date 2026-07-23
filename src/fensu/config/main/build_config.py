"""Preserve option-free in-memory configuration construction."""

from __future__ import annotations

from collections.abc import Mapping

from fensu.config.main._build_config import build_config as _build
from fensu.config.models import Config


def build_config(raw: Mapping[str, object]) -> Config:
    """Validate and build option-free configuration from a raw mapping."""

    return _build(raw)
