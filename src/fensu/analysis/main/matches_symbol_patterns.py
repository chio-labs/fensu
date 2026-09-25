"""Match the documented dotted-symbol glob grammar independently of reachability."""

import fensu._native as native


def matches_symbol_patterns(*, value: str, patterns: tuple[str, ...]) -> bool:
    """Match any pattern using the same strict grammar accepted by configured roots."""

    return native.symbol_pattern_matches(value, list(patterns))
