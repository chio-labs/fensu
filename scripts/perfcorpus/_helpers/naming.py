"""Deterministic domain and symbol naming for the generated corpus."""

from __future__ import annotations

from scripts.perfcorpus.constants import DOMAIN_FIRST_WORDS, DOMAIN_SECOND_WORDS


def build_domain_names(*, count: int) -> tuple[str, ...]:
    """Return the first deterministic snake_case domain names."""

    names: list[str] = []
    for second_word in DOMAIN_SECOND_WORDS:
        for first_word in DOMAIN_FIRST_WORDS:
            names.append(f"{first_word}{second_word}")
            if len(names) == count:
                return tuple(names)
    return tuple(names)


def class_prefix(*, domain: str) -> str:
    """Return the CamelCase symbol prefix for one domain."""

    parts: list[str] = domain.split("_")
    return "".join(part.capitalize() for part in parts)
