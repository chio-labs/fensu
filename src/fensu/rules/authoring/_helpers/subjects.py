"""Infer the callback subject declared by an authored rule signature."""

from __future__ import annotations

from types import CodeType, FunctionType
from typing import get_type_hints

from fensu.rules.authoring.constants import (
    LEGACY_RULE_PARAMETER_COUNT,
    LEGACY_RULE_PARAMETER_NAMES,
    TYPED_RULE_KEYWORD_PARAMETER_COUNT,
    VAR_KEYWORD_FLAG,
    VAR_POSITIONAL_FLAG,
)
from fensu.rules.authoring.exceptions import RuleDefinitionError
from fensu.rules.authoring.models import File, Project, Repository
from fensu.rules.authoring.types import RuleCheck, RuleContext, RuleSubjectKind


def infer_rule_subject(*, check: RuleCheck) -> tuple[RuleSubjectKind, str | None, str | None]:
    """Return the supported callback shape inferred from parameter annotations."""

    if not isinstance(check, FunctionType):
        raise RuleDefinitionError("rule checks must be Python functions")
    code: CodeType = check.__code__
    has_variadic_parameters: bool = bool(code.co_flags & (VAR_POSITIONAL_FLAG | VAR_KEYWORD_FLAG))
    parameter_count: int = code.co_argcount + code.co_kwonlyargcount
    parameter_names: tuple[str, ...] = code.co_varnames[:parameter_count]
    if (
        parameter_count == LEGACY_RULE_PARAMETER_COUNT
        and not has_variadic_parameters
        and parameter_names == LEGACY_RULE_PARAMETER_NAMES
    ):
        return RuleSubjectKind.LEGACY, None, None
    if (
        code.co_argcount != 0
        or code.co_kwonlyargcount != TYPED_RULE_KEYWORD_PARAMETER_COUNT
        or has_variadic_parameters
    ):
        raise RuleDefinitionError(
            "rule checks must declare either (module, ctx) or two keyword-only parameters "
            "annotated as File/Project/Repository and RuleContext"
        )
    try:
        annotations: dict[str, object] = get_type_hints(check)
    except (NameError, TypeError):
        annotations = dict(check.__annotations__)
    subject_parameter: str | None = next(
        (
            parameter
            for parameter in parameter_names
            if annotations.get(parameter) in {File, Project, Repository}
        ),
        None,
    )
    context_parameter: str | None = next(
        (parameter for parameter in parameter_names if annotations.get(parameter) is RuleContext),
        None,
    )
    if subject_parameter is not None and context_parameter is not None:
        annotation: object = annotations[subject_parameter]
        kind: RuleSubjectKind = (
            RuleSubjectKind.FILE
            if annotation is File
            else RuleSubjectKind.PROJECT
            if annotation is Project
            else RuleSubjectKind.REPOSITORY
        )
        return kind, subject_parameter, context_parameter
    raise RuleDefinitionError(
        "typed rule parameters must contain exactly one fensu.File, fensu.Project, or "
        "fensu.Repository subject and one fensu.RuleContext"
    )
