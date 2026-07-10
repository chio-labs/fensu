"""Source-analysis exceptions."""


class AnalysisLookupError(LookupError):
    """Raised when a query uses a handle outside its analysis context."""
