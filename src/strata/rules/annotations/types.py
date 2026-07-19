"""Annotation rule type declarations."""

from __future__ import annotations

from enum import StrEnum


class AnnotationCode(StrEnum):
    """Stable diagnostic codes for the annotations family."""

    PARAMETER_ANNOTATION = "SFA001"
    RETURN_ANNOTATION = "SFA002"
    MODULE_VARIABLE_ANNOTATION = "SFA101"
    CLASS_ATTRIBUTE_ANNOTATION = "SFA102"
    LOCAL_VARIABLE_ANNOTATION = "SFA103"


class ParameterName(StrEnum):
    """Parameter names with annotation-policy semantics."""

    SELF = "self"
    CLS = "cls"
    DISCARD = "_"


class AnnotationSymbol(StrEnum):
    """Python symbols with annotation-policy semantics."""

    ALL = "__all__"
    MATCH_ARGS = "__match_args__"
    SLOTS = "__slots__"
    VERSION = "__version__"
    TEST = "__test__"
    ENUM = "Enum"
    STR_ENUM = "StrEnum"
