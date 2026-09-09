"""Resolve registered analyzer backend capability metadata."""

from fensu.analysis.models import AnalyzerCapability
from fensu.config.types import AnalyzerId


def analyzer_capability(analyzer: AnalyzerId) -> AnalyzerCapability:
    """Return the registered capability contract for a known analyzer."""

    return {
        AnalyzerId.PYTHON: AnalyzerCapability(
            analyzer=AnalyzerId.PYTHON,
            available=True,
            cache_contract="python-ruff-py312-v1",
        ),
        AnalyzerId.RUST: AnalyzerCapability(
            analyzer=AnalyzerId.RUST,
            available=True,
            cache_contract="rust-structure-policy-v1",
        ),
        AnalyzerId.TYPESCRIPT: AnalyzerCapability(
            analyzer=AnalyzerId.TYPESCRIPT,
            available=True,
            cache_contract="typescript-policy-v4",
        ),
        AnalyzerId.SVELTE: AnalyzerCapability(
            analyzer=AnalyzerId.SVELTE,
            available=True,
            cache_contract="svelte-policy-v4",
        ),
    }[analyzer]
