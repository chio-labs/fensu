"""Python semantic-fact analysis implementation."""

from __future__ import annotations

import ast
from collections.abc import Mapping
from pathlib import Path

from strata.analysis.core.helpers.locations import line_offsets, source_range
from strata.analysis.core.helpers.outer_state import outer_state_mutation_nodes
from strata.analysis.core.models import OuterStateMutationFact


class PythonFactAnalysis:
    """Lazy semantic facts backed by shared Python AST indexes."""

    def __init__(
        self,
        *,
        path: Path,
        source: str,
        module: ast.Module,
        node_index: Mapping[type[ast.AST], tuple[ast.AST, ...]],
        parent_by_node: Mapping[ast.AST, ast.AST],
    ) -> None:
        """Bind shared syntax indexes without computing semantic facts."""

        self._path: Path = path
        self._source: str = source
        self._module: ast.Module = module
        self._node_index: Mapping[type[ast.AST], tuple[ast.AST, ...]] = node_index
        self._parent_by_node: Mapping[ast.AST, ast.AST] = parent_by_node
        self._outer_state_mutations: tuple[OuterStateMutationFact, ...] | None = None

    def outer_state_mutations(self) -> tuple[OuterStateMutationFact, ...]:
        """Return direct mutations resolving to state owned by an outer scope."""

        if self._outer_state_mutations is None:
            mutation_nodes: tuple[ast.AST, ...] = outer_state_mutation_nodes(
                module=self._module,
                node_index=self._node_index,
                parent_by_node=self._parent_by_node,
            )
            if not mutation_nodes:
                self._outer_state_mutations = ()
                return self._outer_state_mutations
            offsets: tuple[int, ...] = line_offsets(self._source)
            self._outer_state_mutations = tuple(
                OuterStateMutationFact(
                    location=source_range(
                        path=self._path,
                        source=self._source,
                        line_offsets=offsets,
                        node=node,
                    )
                )
                for node in mutation_nodes
            )
        return self._outer_state_mutations
