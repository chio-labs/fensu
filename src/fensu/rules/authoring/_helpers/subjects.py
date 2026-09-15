"""Infer the callback subject declared by an authored rule signature."""

from __future__ import annotations

from types import FunctionType
from typing import get_type_hints

from fensu.rules.authoring.exceptions import RuleDefinitionError
from fensu.rules.authoring.subjects import File, Project
from fensu.rules.authoring.types import RuleCheck, RuleContext, RuleSubjectKind

_VAR_POSITIONAL_FLAG = 0x04
_VAR_KEYWORD_FLAG = 0x08


def infer_rule_subject(*, check: RuleCheck) -> tuple[RuleSubjectKind, str | None, str | None]:
    """Return the supported callback shape inferred from parameter annotations."""

    if not isinstance(check, FunctionType):
        raise RuleDefinitionError("rule checks must be Python functions")
    code = check.__code__
    has_variadic_parameters = bool(code.co_flags & (_VAR_POSITIONAL_FLAG | _VAR_KEYWORD_FLAG))
    parameter_count = code.co_argcount + code.co_kwonlyargcount
    parameter_names = code.co_varnames[:parameter_count]
    if (
        parameter_count == 2
        and not has_variadic_parameters
        and parameter_names == ("module", "ctx")
    ):
        return RuleSubjectKind.LEGACY, None, None
    if code.co_argcount != 0 or code.co_kwonlyargcount != 2 or has_variadic_parameters:
        raise RuleDefinitionError(
            "rule checks must declare either (module, ctx) or two keyword-only parameters "
            "annotated as File/Project and RuleContext"
        )
    try:
        annotations: dict[str, object] = get_type_hints(check)
    except (NameError, TypeError):
        annotations = dict(check.__annotations__)
    subject_parameter = next(
        (
            parameter
            for parameter in parameter_names
            if annotations.get(parameter) in {File, Project}
        ),
        None,
    )
    context_parameter = next(
        (parameter for parameter in parameter_names if annotations.get(parameter) is RuleContext),
        None,
    )
    if subject_parameter is not None and context_parameter is not None:
        annotation = annotations[subject_parameter]
        kind = RuleSubjectKind.FILE if annotation is File else RuleSubjectKind.PROJECT
        return kind, subject_parameter, context_parameter
    raise RuleDefinitionError(
        "typed rule parameters must contain exactly one fensu.File or fensu.Project subject and "
        "one fensu.RuleContext"
    )
