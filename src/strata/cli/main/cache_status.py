"""Render optional persistent-cache status to the diagnostic stream."""

from typing import TextIO

from strata.cache.results.models import CacheStats


def write_cache_status(
    *,
    stderr: TextIO,
    stats: CacheStats | None,
    show_stats: bool,
) -> None:
    """Write cache degradation and opt-in operation details."""

    if stats is None:
        return
    if stats.storage_failed:
        stderr.write(
            "Warning: cache publication failed; existing cache data may have been reused. "
            "If this persists, check permissions or delete .strata/cache and rerun.\n"
        )
        stderr.flush()
    if show_stats:
        stderr.write(
            "Cache: "
            f"hits={stats.hits} "
            f"misses={stats.misses} "
            f"invalidations={stats.invalidations} "
            f"writes={stats.writes} "
            f"non_cacheable={stats.non_cacheable} "
            f"storage_failed={str(stats.storage_failed).lower()}\n"
        )
        stderr.flush()
