"""Build backend-neutral analysis from Python source syntax."""

from __future__ import annotations

import ast
from pathlib import Path

from strata.analysis.classes.file_analysis import PythonFileAnalysis
from strata.analysis.classes.lazy_syntax_artifacts import LazySyntaxArtifacts
from strata.analysis.types import Analysis


def build_analysis(*, path: Path, source: str, module: ast.Module) -> Analysis:
    """Build one private analysis facade around an already-parsed module."""

    artifacts: LazySyntaxArtifacts = LazySyntaxArtifacts(path=path, source=source, module=module)
    return PythonFileAnalysis(path=path, source=source, artifacts=artifacts)
