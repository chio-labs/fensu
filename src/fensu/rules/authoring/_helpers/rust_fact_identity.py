"""Canonical dependency identities for observed Rust fact queries."""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING

from fensu.analysis.models import SourceLocation

if TYPE_CHECKING:
    from fensu.rules.authoring.models import RustCrateFact, RustFileFacts


def rust_crate_identity(*, value: RustCrateFact) -> str:
    """Return one deterministic complete Cargo crate fact identity."""

    return json.dumps(
        {
            "dependencies": [
                {
                    "kinds": list(item.kinds),
                    "local_crate_identity": item.local_crate_identity,
                    "package_name": item.package_name,
                    "resolved": item.resolved,
                    "source_name": item.source_name,
                }
                for item in value.dependencies
            ],
            "directory": value.directory.value,
            "identity": value.identity,
            "library_name": value.library_name,
            "manifest_path": value.manifest_path.value,
            "name": value.name,
            "targets": [
                {
                    "entry_path": item.entry_path.value,
                    "identity": item.identity,
                    "kinds": list(item.kinds),
                    "name": item.name,
                    "source_root": item.source_root.value,
                    "test": item.test,
                }
                for item in value.targets
            ],
        },
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )


def rust_file_identity(*, value: RustFileFacts) -> str:
    """Return one deterministic complete Rust source fact identity."""

    return json.dumps(
        {
            "crate_identity": value.crate_identity,
            "crate_name": value.crate_name,
            "items": [
                {
                    "derives": list(item.derives),
                    "implemented_trait": item.implemented_trait,
                    "implementation_target": item.implementation_target,
                    "kind": item.kind.value,
                    "location": _location(value=item.location),
                    "module_parts": list(item.module_parts),
                    "name": item.name,
                    "visibility": item.visibility.value,
                    "visibility_path": item.visibility_path,
                }
                for item in value.items
            ],
            "module_parts": list(value.module_parts),
            "parse_error": value.parse_error,
            "path": value.file.path.value,
            "source_hash": hashlib.sha256(value.source.encode("utf-8")).hexdigest(),
            "source_root": value.source_root.value,
            "test": value.test,
            "uses": [
                {
                    "authored_parts": list(item.authored_parts),
                    "location": _location(value=item.location),
                    "resolution": item.resolution.value,
                    "source_module_parts": list(item.source_module_parts),
                    "target": None if item.target is None else item.target.path.value,
                    "target_crate_identity": item.target_crate_identity,
                    "target_module_parts": (
                        None if item.target_module_parts is None else list(item.target_module_parts)
                    ),
                }
                for item in value.uses
            ],
        },
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )


def _location(*, value: SourceLocation) -> dict[str, object]:
    return {"column": value.column, "line": value.line, "path": value.path.as_posix()}
