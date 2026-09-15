"""Errors raised while defining or registering a rule."""

from __future__ import annotations


class RuleDefinitionError(Exception):
    """A rule's metadata envelope or code namespace is invalid at definition time."""


class ProjectPathError(ValueError):
    """A public project path or glob is invalid."""


class ProjectPathTypeError(TypeError):
    """A project query received an unsupported path value."""


class ArchitectureGraphQueryError(ValueError):
    """An architecture graph query does not identify a discovered module."""


class ArchitectureGraphQueryTypeError(TypeError):
    """An architecture graph query received an unsupported subject value."""


class RustFactProtocolError(ValueError):
    """A native Rust fact payload does not match the supported public contract."""


class RustFactQueryTypeError(TypeError):
    """A Rust fact query received an unsupported subject value."""


class WebFactProtocolError(ValueError):
    """A native web fact payload does not match the supported public contract."""


class WebFactQueryTypeError(TypeError):
    """A web fact query received an unsupported subject value."""


class WebFactQueryError(ValueError):
    """A web fact query or text handle is invalid for the selected source."""


class PythonFactQueryTypeError(TypeError):
    """A Python target fact query received an unsupported subject value."""


class TargetFactsUnavailableError(RuntimeError):
    """A target handle was queried for facts owned by another analyzer."""


class TargetFactQueryTypeError(TypeError):
    """A repository target fact helper received an unsupported value."""
