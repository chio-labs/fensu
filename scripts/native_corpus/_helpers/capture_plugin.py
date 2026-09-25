"""Pytest plugin that captures deterministic native core-rule requests."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import fensu._native as native
import fensu.evaluation.classes.rule_project as rule_project
import fensu.rules.layers._helpers.dead_code as dead_code
from scripts.native_corpus._helpers.project_capture import project_fixture

_REPOSITORY_PLACEHOLDER: str = "<repo-root>"
_EXCLUDED_FILESYSTEM_PARTS: frozenset[str] = frozenset({".fensu", ".git", "__pycache__"})


class _CaptureState:
    def __init__(self) -> None:
        self.fixtures: list[dict[str, Any]] = []
        self.plans: dict[int, tuple[list[Any], list[Any], list[str]]] = {}
        self.current_nodeid: str = "unknown"
        self.original_plan: Any = native.plan_native_execution_batch
        self.original_evaluate: Any = native.evaluate_native_execution_batch
        self.original_project_check: Any = dead_code._check_dead_code
        self.original_project_facts: Any = rule_project.build_reachability_facts
        self.project_snapshot: tuple[dict[str, Any], Any] | None = None
        self.project_fixtures: list[dict[str, Any]] = []

    def project_facts(self, **arguments: Any) -> Any:
        facts: Any = self.original_project_facts(**arguments)
        self.project_snapshot = (arguments, facts)
        return facts

    def project_check(self, **arguments: Any) -> Any:
        self.project_snapshot = None
        faults: Any = self.original_project_check(**arguments)
        if self.project_snapshot is not None:
            inputs, facts = self.project_snapshot
            self.project_fixtures.append(
                project_fixture(
                    description=f"{self.current_nodeid} project {arguments['code']}",
                    code=str(arguments["code"]),
                    inputs=inputs,
                    facts=facts,
                    faults=faults,
                )
            )
        return faults

    def plan(self, *arguments: Any) -> Any:
        requests: list[Any] = arguments[0]
        project_files: list[Any] = arguments[1]
        entrypoint_modules: list[str] = arguments[2]
        major: int = arguments[3]
        minor: int = arguments[4]
        result: Any = self.original_plan(requests, project_files, entrypoint_modules, major, minor)
        self.plans[id(result[0])] = (requests, project_files, entrypoint_modules)
        return result

    def evaluate(self, *arguments: Any) -> Any:
        batch: Any = arguments[0]
        observations: list[dict[str, list[str]]] = arguments[1]
        result: Any = self.original_evaluate(batch, observations)
        requests, project_files, entrypoint_modules = self.plans.pop(id(batch))
        for index, (request, answers, expected) in enumerate(
            zip(requests, observations, result, strict=True)
        ):
            core_codes: list[str] = [code for code in request[1] if code.startswith("FF")]
            if not core_codes:
                continue
            self.fixtures.append(
                _fixture(
                    description=f"{self.current_nodeid} request {index}",
                    request=request,
                    answers=answers,
                    expected=[row for row in expected if row[0].startswith("FF")],
                    codes=core_codes,
                    project_files=project_files,
                    entrypoint_modules=entrypoint_modules,
                )
            )
        return result

    def set_current_nodeid(self, *, nodeid: str) -> None:
        self.current_nodeid = nodeid

    def merge_worker_output(self, *, output: dict[str, Any]) -> None:
        self.fixtures.extend(json.loads(output.get("fensu_core_fixtures", "[]")))
        self.project_fixtures.extend(json.loads(output.get("fensu_project_fixtures", "[]")))

    def populate_worker_output(self, *, output: dict[str, Any]) -> dict[str, Any]:
        output["fensu_core_fixtures"] = json.dumps(self.fixtures)
        output["fensu_project_fixtures"] = json.dumps(self.project_fixtures)
        return output


_CAPTURE: _CaptureState = _CaptureState()


def pytest_configure() -> None:
    _ = setattr(native, "plan_native_execution_batch", _CAPTURE.plan)
    _ = setattr(native, "evaluate_native_execution_batch", _CAPTURE.evaluate)
    _ = setattr(rule_project, "build_reachability_facts", _CAPTURE.project_facts)
    _ = setattr(dead_code, "_check_dead_code", _CAPTURE.project_check)


def pytest_runtest_setup(item: Any) -> None:
    _CAPTURE.set_current_nodeid(nodeid=item.nodeid)


def pytest_testnodedown(node: Any) -> None:
    """Collect worker-owned records before the controller writes each corpus once."""

    output: dict[str, Any] = getattr(node, "workeroutput", {})
    _CAPTURE.merge_worker_output(output=output)


def pytest_sessionfinish(session: Any) -> None:
    if hasattr(session.config, "workeroutput"):
        _ = _CAPTURE.populate_worker_output(output=session.config.workeroutput)
        return
    if session.exitstatus:
        return
    for variable, fixtures in (
        ("FENSU_CORE_FIXTURE_OUTPUT", _CAPTURE.fixtures),
        ("FENSU_CORE_PROJECT_FIXTURE_OUTPUT", _CAPTURE.project_fixtures),
    ):
        output: str | None = os.environ.get(variable)
        if output is not None:
            _write_fixtures(output=Path(output), fixtures=fixtures)


def _write_fixtures(*, output: Path, fixtures: list[dict[str, Any]]) -> None:
    ordered: list[dict[str, Any]] = sorted(
        fixtures,
        key=lambda fixture: (
            fixture["description"],
            fixture["context"]["repository_path"],
            fixture["codes"],
        ),
    )
    output.write_text(
        "\n".join(json.dumps(fixture, sort_keys=True, separators=(",", ":")) for fixture in ordered)
        + "\n",
        encoding="utf-8",
    )


def _fixture(
    *,
    description: str,
    request: Any,
    answers: dict[str, list[str]],
    expected: list[Any],
    codes: list[str],
    project_files: list[Any],
    entrypoint_modules: list[str],
) -> dict[str, Any]:
    project_context: Any = request[11]
    repo_root: str = project_context[4]
    return {
        "description": description,
        "source": request[0],
        "codes": codes,
        "context": {
            "scope": request[2],
            "role": request[3],
            "is_main_module": request[4],
            "thresholds": request[5],
            "repository_path": request[6],
            "contracts": request[7],
            "relative_parts": request[8],
            "is_entry_module": request[9],
            "package_name": request[10],
            "tooling_packages": project_context[0],
            "scope_roots": project_context[1],
            "test_scopes": project_context[6],
            "observations": _normalize(value=answers, repo_root=repo_root),
            "custom_registrations": _normalize(value=project_context[3], repo_root=repo_root),
            "repo_root": _REPOSITORY_PLACEHOLDER,
        },
        "project_files": [
            {
                "path": project_file[0],
                "scope": project_file[1],
                "module_parts": project_file[2],
                "source": project_file[3],
            }
            for project_file in project_files
        ],
        "filesystem": _filesystem(repo_root=repo_root),
        "entrypoint_modules": entrypoint_modules,
        "expected": [
            {
                "code": row[0],
                "path": row[1],
                "line": row[2],
                "column": row[3],
                "message": row[4],
                "remediation": row[5],
            }
            for row in expected
        ],
    }


def _normalize(*, value: Any, repo_root: str) -> Any:
    if isinstance(value, str):
        return value.replace(repo_root, _REPOSITORY_PLACEHOLDER)
    if isinstance(value, list | tuple):
        return [_normalize(value=item, repo_root=repo_root) for item in value]
    if isinstance(value, dict):
        return {
            _normalize(value=key, repo_root=repo_root): _normalize(value=item, repo_root=repo_root)
            for key, item in value.items()
        }
    return value


def _filesystem(*, repo_root: str) -> list[dict[str, Any]]:
    root: Path = Path(repo_root)
    entries: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        relative: Path = path.relative_to(root)
        if any(part in _EXCLUDED_FILESYSTEM_PARTS for part in relative.parts):
            continue
        entries.append(
            {
                "path": relative.as_posix(),
                "content": path.read_text(encoding="utf-8") if path.is_file() else None,
            }
        )
    return entries
