"""Target-qualified runtime dependency observations for repository rules."""

from __future__ import annotations

from fensu.evaluation.constants import REPOSITORY_RULE_REQUESTER
from fensu.rules.authoring.models import ProjectPath


class RepositoryDependencyObserver:
    """Record one target's tree, graph, or analyzer-fact query answers."""

    def __init__(self, *, target: str, observations: list[dict[str, str]]) -> None:
        self._target = target
        self._observations = observations

    def __call__(
        self,
        kind: str,
        query: ProjectPath | str,
        answer: str | tuple[ProjectPath, ...],
        pattern: str | None = None,
    ) -> None:
        """Record one canonical target-qualified query answer."""

        query_text: str = query.value if isinstance(query, ProjectPath) else query
        answer_text: str = (
            answer if isinstance(answer, str) else "\n".join(item.value for item in answer)
        )
        if pattern is not None:
            answer_text = f"{pattern}\0{answer_text}"
        self._observations.append(
            {
                "requester": REPOSITORY_RULE_REQUESTER,
                "target": self._target,
                "kind": kind,
                "query": query_text,
                "answer": answer_text,
            }
        )
