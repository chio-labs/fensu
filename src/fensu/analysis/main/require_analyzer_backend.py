"""Enforce analyzer backend availability at command boundaries."""

from fensu.analysis.main.analyzer_capability import analyzer_capability
from fensu.analysis.models import AnalyzerCapability
from fensu.config.exceptions import ConfigError
from fensu.config.types import AnalyzerId


def require_analyzer_backend(analyzer: AnalyzerId) -> AnalyzerCapability:
    """Return an available capability or fail distinctly from unknown-ID parsing."""

    capability: AnalyzerCapability = analyzer_capability(analyzer)
    if not capability.available:
        raise ConfigError(f"Known analyzer backend unavailable: {analyzer.value}.")
    return capability
