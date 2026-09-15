"""Canonical dependency identities for observed web fact queries."""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING

from fensu.analysis.models import SourceLocation

if TYPE_CHECKING:
    from fensu.rules.authoring.models import WebFileFacts, WebImportBindingFact


def web_file_identity(*, value: WebFileFacts) -> str:
    """Return one deterministic complete web source fact identity."""

    return json.dumps(
        {
            "analyzer": value.analyzer.value,
            "bindings": [
                {
                    "initializer_call": item.initializer_call,
                    "location": _location(value=item.location),
                    "name": item.name,
                }
                for item in value.bindings
            ],
            "calls": [
                {
                    "ancestor_calls": list(item.ancestor_calls),
                    "function_argument": item.function_argument,
                    "function_name": item.function_name,
                    "location": _location(value=item.location),
                    "name": item.name,
                    "returned_cleanup": item.returned_cleanup,
                }
                for item in value.calls
            ],
            "classes": [
                {
                    "error_class": item.error_class,
                    "exported": item.exported,
                    "location": _location(value=item.location),
                    "name": item.name,
                }
                for item in value.classes
            ],
            "functions": [
                {
                    "distinct_call_count": item.distinct_call_count,
                    "export_owner": item.export_owner,
                    "exported": item.exported,
                    "local_count": item.local_count,
                    "location": _location(value=item.location),
                    "name": item.name,
                    "parameter_count": item.parameter_count,
                    "parameters_annotated": item.parameters_annotated,
                    "qualified_name": item.qualified_name,
                    "return_type": item.return_type,
                    "statement_count": item.statement_count,
                }
                for item in value.functions
            ],
            "imports": [
                {
                    "bindings": _bindings(value=item.bindings),
                    "location": _location(value=item.location),
                    "namespace": item.namespace,
                    "specifier": item.specifier,
                    "target": None if item.target is None else item.target.path.value,
                    "type_only": item.type_only,
                }
                for item in value.imports
            ],
            "models": [
                {
                    "exported": item.exported,
                    "kind": item.kind.value,
                    "location": _location(value=item.location),
                    "name": item.name,
                    "property_names": list(item.property_names),
                    "readonly_properties": item.readonly_properties,
                    "readonly_shape": item.readonly_shape,
                }
                for item in value.models
            ],
            "module": value.module,
            "parse_error": value.parse_error,
            "path": value.file.path.value,
            "purpose": value.purpose.value,
            "public_export_count": value.public_export_count,
            "re_exports": [_location(value=item) for item in value.re_exports],
            "resources": [
                {
                    "ancestor_calls": list(item.ancestor_calls),
                    "binding_name": item.binding_name,
                    "family": item.family,
                    "location": _location(value=item.location),
                }
                for item in value.resources
            ],
            "scope": value.scope.value,
            "source_hash": hashlib.sha256(value.source.encode("utf-8")).hexdigest(),
            "source_kind": value.source_kind.value,
            "source_root": value.source_root.value,
            "runtime_declaration_count": value.runtime_declaration_count,
            "svelte": (
                None
                if value.svelte is None
                else {
                    "has_component_markup": value.svelte.has_component_markup,
                    "module_runes": [
                        {"location": _location(value=item.location), "name": item.name}
                        for item in value.svelte.module_runes
                    ],
                    "route": value.svelte.route,
                    "scripts": [
                        {
                            "context": item.context.value,
                            "location": _location(value=item.location),
                        }
                        for item in value.svelte.scripts
                    ],
                    "state_module": value.svelte.state_module,
                }
            ),
            "syntax_handles": [
                {
                    "end": item.end,
                    "kind": item.kind.value,
                    "location": _location(value=item.location),
                    "name": item.name,
                    "start": item.start,
                }
                for item in value.syntax_handles
            ],
        },
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )


def _location(*, value: SourceLocation) -> dict[str, object]:
    return {"column": value.column, "line": value.line, "path": value.path.as_posix()}


def _bindings(*, value: tuple[WebImportBindingFact, ...]) -> list[dict[str, str]]:
    return [{"imported_name": item.imported_name, "local_name": item.local_name} for item in value]
