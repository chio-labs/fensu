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
