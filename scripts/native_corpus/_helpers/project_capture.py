"""Serialize whole-project native requests without manufacturing an anchor source."""

from pathlib import Path
from typing import Any

from fensu.analysis.types import PythonSymbolKind


def project_fixture(
    *, description: str, code: str, inputs: dict[str, Any], facts: Any, faults: Any
) -> dict[str, Any]:
    """Capture real selected source snapshots and policy inputs for Rust replay."""

    tree: Any = inputs["tree"]
    config: Any = inputs["config"]
    analysis: Any = inputs["analysis"]
    root: Path = tree.repo_root.path if tree.project_root is None else tree.project_root.path
    scopes: dict[Path, str] = {file.path: file.scope.value for file in tree.files}
    entries: Any = analysis.entrypoint_symbols(requester=inputs["requester"])
    return {
        "description": description,
        "source": "",
        "codes": [code],
        "context": {
            "scope": "root",
            "role": None,
            "is_main_module": False,
            "thresholds": {},
            "repository_path": "",
            "contracts": [],
            "relative_parts": [],
            "is_entry_module": False,
            "package_name": "",
            "tooling_packages": [],
            "scope_roots": [],
            "observations": {},
            "custom_registrations": [],
            "repo_root": "<repo-root>",
            "dead_code": {
                "enabled": config.dead_code.enabled,
                "roots": [
                    (list(value.modules), list(value.symbols)) for value in config.dead_code.roots
                ],
                "entrypoints": entries,
                "config_path": facts.configuration_path.relative_to(root, walk_up=True).as_posix(),
            },
        },
        "project_files": [
            {
                "path": symbol.location.path.relative_to(root).as_posix(),
                "scope": scopes[symbol.location.path],
                "module_parts": symbol.module.split("."),
                "source": analysis.native_source(
                    requester=inputs["requester"], path=symbol.location.path
                ),
            }
            for symbol in facts.symbols
            if symbol.kind is PythonSymbolKind.MODULE
        ],
        "filesystem": [],
        "entrypoint_modules": sorted({reference.partition(":")[0] for _, reference in entries}),
        "expected": [
            {
                "code": str(fault.code),
                "path": fault.path.relative_to(root, walk_up=True).as_posix(),
                "line": fault.line,
                "column": fault.column,
                "message": fault.message,
                "remediation": fault.remediation,
            }
            for fault in faults
        ],
    }
