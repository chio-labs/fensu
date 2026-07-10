"""Build backend-neutral analysis from Python source syntax."""

from __future__ import annotations

import ast
from pathlib import Path

from strata.analysis.core.helpers.building import build_python_analysis
from strata.analysis.core.types import AnalysisBuild


def build_analysis(*, path: Path, source: str, module: ast.Module) -> AnalysisBuild:
    """Build private analysis and compatibility indexes in one AST traversal."""

    return build_python_analysis(path=path, source=source, module=module)
