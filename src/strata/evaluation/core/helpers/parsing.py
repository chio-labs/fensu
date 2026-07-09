"""Parse discovered files into evaluation models."""

from __future__ import annotations

import ast

from strata.discovery.core.main.position import position_facts
from strata.discovery.core.models import ScopedFile
from strata.evaluation.core.exceptions import ParseError
from strata.evaluation.core.helpers.ast_access import build_ast_indexes
from strata.evaluation.core.models import ParsedModule


def parse_scoped_file(scoped_file: ScopedFile) -> ParsedModule:
    """Read and parse one discovered Python file."""

    source: str = scoped_file.path.read_text(encoding="utf-8")
    try:
        module: ast.Module = ast.parse(source, filename=str(scoped_file.path))
    except SyntaxError as error:
        message: str = (
            f"Could not parse {scoped_file.path}: syntax is not valid for the Python "
            "interpreter running strata. Run strata under the target project's Python "
            "version or newer."
        )
        raise ParseError(
            path=scoped_file.path, message=message, line=error.lineno, column=error.offset
        ) from error
    node_index, parent_by_node = build_ast_indexes(module)
    return ParsedModule(
        scoped_file=scoped_file,
        module=module,
        source=source,
        node_index=node_index,
        parent_by_node=parent_by_node,
        position=position_facts(scoped_file),
    )
