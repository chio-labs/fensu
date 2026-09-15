"""Requester-bound observation recorder for serialized Rust fact queries."""

from __future__ import annotations

from fensu.rules.authoring.models import ProjectPath


class RustDependencyObserver:
    """Record tree and Rust fact query answers in one canonical shape."""

    def __init__(self, *, requester: str, observations: list[dict[str, str]]) -> None:
        self._requester: str = requester
        self._observations: list[dict[str, str]] = observations

    def __call__(
        self,
        kind: str,
        query: ProjectPath | str,
        answer: str | tuple[ProjectPath, ...],
        pattern: str | None = None,
    ) -> None:
        """Record one stable answer for native cache dependency transport."""

        query_text: str = query.value if isinstance(query, ProjectPath) else query
        answer_text: str = (
            answer if isinstance(answer, str) else "\n".join(item.value for item in answer)
        )
        if pattern is not None:
            answer_text = f"{pattern}\0{answer_text}"
        self._observations.append(
            {
                "requester": self._requester,
                "kind": kind,
                "query": query_text,
                "answer": answer_text,
            }
        )
