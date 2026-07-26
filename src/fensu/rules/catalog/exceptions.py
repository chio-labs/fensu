"""Rule catalogue lookup exceptions."""


class RuleConstraintNotFoundError(LookupError):
    """Raised when canonical rule metadata lacks a requested constraint."""
