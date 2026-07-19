"""Render optional persistent-cache status to the diagnostic stream."""

from typing import TextIO

from fensu.cache.results.models import CacheStats


def write_cache_status(
    *,
    stderr: TextIO,
    stats: CacheStats | None,
    show_stats: bool,
    disabled_reason: str | None = None,
) -> None:
    """Write cache degradation, unavailability, and opt-in operation details."""

    if stats is None:
        if show_stats and disabled_reason is not None:
            stderr.write(f"Cache: disabled ({disabled_reason})\n")
            stderr.flush()
        return
    if stats.internal_error:
        stderr.write(
            "Warning: an internal cache error prevented some results from being cached. "
            "Diagnostics are complete and computed fresh. This is a Fensu bug; "
            "please report it.\n"
        )
        stderr.flush()
    elif stats.storage_failed:
        stderr.write(
            "Warning: cache publication failed; existing cache data may have been reused. "
            "If this persists, check permissions or delete .fensu/cache and rerun.\n"
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
