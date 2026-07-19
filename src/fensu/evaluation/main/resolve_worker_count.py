"""Resolve automatic evaluation worker counts."""

from fensu.evaluation._helpers.parallel_evaluation import default_worker_count


def resolve_worker_count(*, target_count: int) -> int:
    """Return the measured-breakeven worker count for a target population."""

    return default_worker_count(target_count=target_count)
