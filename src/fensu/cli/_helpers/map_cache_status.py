"""Render mapping-cache status to the diagnostic stream."""

from typing import TextIO

from fensu.cache.mapping.models import MapCacheStats


def write_map_cache_status(
    *, stderr: TextIO, stats: MapCacheStats | None, show_stats: bool
) -> None:
    """Write cache degradation and opt-in operation details."""

    if stats is None:
        return
    if stats.internal_error:
        stderr.write("Warning: an internal map cache error forced fresh mapping.\n")
    elif stats.storage_failed:
        stderr.write("Warning: map cache publication failed; mapping output is complete.\n")
    if show_stats:
        status: str = "hit" if stats.manifest_hit else "miss"
        stderr.write(
            f"Map cache: manifest={status} parsed_files={stats.parsed_files} "
            f"reused_file_records={stats.reused_file_records} writes={stats.writes} "
            f"storage_failed={str(stats.storage_failed).lower()} "
            f"internal_error={str(stats.internal_error).lower()}\n"
        )
    stderr.flush()
