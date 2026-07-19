"""Public API loading failures."""


class UnknownPublicAttributeError(AttributeError):
    """Raised when a name is not part of the public Fensu surface."""
