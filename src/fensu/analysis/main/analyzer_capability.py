"""Resolve registered analyzer backend capability metadata."""

from fensu.analysis.models import AnalyzerCapability
from fensu.config.types import AnalyzerId


def analyzer_capability(analyzer: AnalyzerId) -> AnalyzerCapability:
    """Return the registered capability contract for a known analyzer."""

    return {
        AnalyzerId.PYTHON: AnalyzerCapability(
            analyzer=AnalyzerId.PYTHON,
            available=True,
            cache_contract="python-ruff-py312-v2",
        ),
        AnalyzerId.RUST: AnalyzerCapability(
            analyzer=AnalyzerId.RUST,
            available=True,
            cache_contract="rust-rules-v3",
        ),
        AnalyzerId.TYPESCRIPT: AnalyzerCapability(
            analyzer=AnalyzerId.TYPESCRIPT,
            available=True,
            cache_contract="typescript-policy-v5",
        ),
        AnalyzerId.SVELTE: AnalyzerCapability(
            analyzer=AnalyzerId.SVELTE,
            available=True,
            cache_contract="svelte-policy-v5",
        ),
    }[analyzer]
