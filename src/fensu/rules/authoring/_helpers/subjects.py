"""Infer the callback subject declared by an authored rule signature."""

from __future__ import annotations

import inspect
from typing import get_type_hints

from fensu.rules.authoring.exceptions import RuleDefinitionError
from fensu.rules.authoring.subjects import File, Project
from fensu.rules.authoring.types import RuleCheck, RuleContext, RuleSubjectKind


def infer_rule_subject(
    *, check: RuleCheck
) -> tuple[RuleSubjectKind, str | None, str | None]:
    """Return the supported callback shape inferred from parameter annotations."""

    parameters: tuple[inspect.Parameter, ...] = tuple(inspect.signature(check).parameters.values())
    if tuple(parameter.name for parameter in parameters) == ("module", "ctx"):
        return RuleSubjectKind.LEGACY, None, None
    if len(parameters) != 2 or any(
        parameter.kind is not inspect.Parameter.KEYWORD_ONLY for parameter in parameters
    ):
        raise RuleDefinitionError(
            "rule checks must declare either (module, ctx) or two keyword-only parameters "
            "annotated as File/Project and RuleContext"
        )
    try:
        annotations: dict[str, object] = get_type_hints(check)
    except (NameError, TypeError):
        annotations = {parameter.name: parameter.annotation for parameter in parameters}
    subject_parameter = next(
        (
            parameter
            for parameter in parameters
            if annotations.get(parameter.name) in {File, Project}
        ),
        None,
    )
    context_parameter = next(
        (
            parameter
            for parameter in parameters
            if annotations.get(parameter.name) is RuleContext
        ),
        None,
    )
    if subject_parameter is not None and context_parameter is not None:
        annotation = annotations[subject_parameter.name]
        kind = RuleSubjectKind.FILE if annotation is File else RuleSubjectKind.PROJECT
        return kind, subject_parameter.name, context_parameter.name
    raise RuleDefinitionError(
        "typed rule parameters must contain exactly one fensu.File or fensu.Project subject and "
        "one fensu.RuleContext"
    )
