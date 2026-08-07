"""Rule metadata transport test cases."""

from dataclasses import dataclass


@dataclass(frozen=True)
class RuleMetadataCacheabilityTestCase:
    """One authored cacheability state and expected transport value."""

    description: str
    cacheable: bool | None
    expected_cacheable: bool | None
