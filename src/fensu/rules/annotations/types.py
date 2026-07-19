"""Annotation rule type declarations."""

from __future__ import annotations

from enum import StrEnum


class AnnotationCode(StrEnum):
    """Stable diagnostic codes for the annotations family."""

    PARAMETER_ANNOTATION = "FFA001"
    RETURN_ANNOTATION = "FFA002"
    MODULE_VARIABLE_ANNOTATION = "FFA101"
    CLASS_ATTRIBUTE_ANNOTATION = "FFA102"
    LOCAL_VARIABLE_ANNOTATION = "FFA103"


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
