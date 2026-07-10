"""Source comment fact extraction."""

from __future__ import annotations

import io
import tokenize
from pathlib import Path

from strata.analysis.core.models import CommentFact


def comment_facts(*, path: Path, source: str) -> tuple[CommentFact, ...]:
    """Return source comments in token order, or no facts for incomplete tokens."""

    comments: list[CommentFact] = []
    try:
        for token in tokenize.generate_tokens(io.StringIO(source).readline):
            if token.type == tokenize.COMMENT:
                comments.append(
                    CommentFact(
                        path=path,
                        line=token.start[0],
                        column=token.start[1],
                        text=token.string.strip(),
                    )
                )
    except tokenize.TokenError:
        return ()
    return tuple(comments)
