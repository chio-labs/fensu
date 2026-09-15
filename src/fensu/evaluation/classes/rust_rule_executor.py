"""Per-rule and per-subject execution for serialized Rust custom facts."""

from __future__ import annotations

from pathlib import Path
from typing import cast

from fensu.config.models import Config
from fensu.evaluation.classes.rust_rule_context import RustRuleContext
from fensu.evaluation.classes.rust_rule_result_cache import RustRuleResultCache
from fensu.evaluation.exceptions import RustCustomRuleError
from fensu.rules.authoring.models import (
    Fault,
    Project,
    ProjectPath,
    ProjectTree,
    RuleSpec,
    RustFileFacts,
    RustWorkspaceFacts,
)
from fensu.rules.authoring.types import RuleSubjectKind


class RustRuleExecutor:
    """Evaluate typed Rust rules at their declared subject granularity."""

    @staticmethod
    def execute(
        *,
        root: Path,
        tree: ProjectTree,
        workspace: RustWorkspaceFacts,
        config: Config,
        rule: RuleSpec,
        warning: bool,
        cache: RustRuleResultCache,
    ) -> tuple[list[dict[str, object]], list[dict[str, str]]]:
        """Evaluate one selected rule at its declared subject granularity."""

        if rule.subject_kind is RuleSubjectKind.FILE:
            return RustRuleExecutor._execute_file_subjects(
                root=root,
                tree=tree,
                workspace=workspace,
                config=config,
                rule=rule,
                warning=warning,
                cache=cache,
            )
        if rule.subject_kind is RuleSubjectKind.PROJECT:
            return RustRuleExecutor._execute_project_subject(
                root=root,
                tree=tree,
                workspace=workspace,
                config=config,
                rule=rule,
                warning=warning,
                cache=cache,
            )
        raise RustCustomRuleError(f"Rust custom rule {rule.code} must use File or Project")

    @staticmethod
    def _execute_file_subjects(
        *,
        root: Path,
        tree: ProjectTree,
        workspace: RustWorkspaceFacts,
        config: Config,
        rule: RuleSpec,
        warning: bool,
        cache: RustRuleResultCache,
    ) -> tuple[list[dict[str, object]], list[dict[str, str]]]:
        findings: list[dict[str, object]] = []
        observations: list[dict[str, str]] = []
        files_by_path: dict[ProjectPath, RustFileFacts] = {
            file.file.path: file for file in workspace._file_values
        }
        for file in tree.files:
            facts: RustFileFacts | None = files_by_path.get(file.path)
            if facts is None:
                continue
            cached: tuple[list[dict[str, object]], list[dict[str, str]]] | None = cache.read(
                rule=rule,
                subject_kind="file",
                subject_identity=file.path.value,
                tree=tree,
                workspace=workspace,
            )
            if cached is not None:
                cached_findings, cached_dependencies = cached
                findings.extend(cached_findings)
                observations.extend(cached_dependencies)
                continue
            invocation_observations: list[dict[str, str]] = []
            context: RustRuleContext = RustRuleContext(
                root=root,
                tree=tree,
                workspace=workspace,
                config=config,
                rule=rule,
                file_facts=facts,
                observations=invocation_observations,
            )
            current_findings: list[dict[str, object]] = RustRuleExecutor._serialize_findings(
                root=root,
                rule=rule,
                faults=rule.check(
                    **{
                        rule.subject_parameter or "file": file,
                        rule.context_parameter or "ctx": context,
                    }
                )
                if rule.check is not None
                else [],
                warning=warning,
            )
            findings.extend(current_findings)
            observations.extend(invocation_observations)
            cache.write(
                rule=rule,
                subject_kind="file",
                subject_identity=file.path.value,
                findings=current_findings,
                dependencies=invocation_observations,
            )
        return findings, observations

    @staticmethod
    def _execute_project_subject(
        *,
        root: Path,
        tree: ProjectTree,
        workspace: RustWorkspaceFacts,
        config: Config,
        rule: RuleSpec,
        warning: bool,
        cache: RustRuleResultCache,
    ) -> tuple[list[dict[str, object]], list[dict[str, str]]]:
        cached: tuple[list[dict[str, object]], list[dict[str, str]]] | None = cache.read(
            rule=rule,
            subject_kind="project",
            subject_identity=".",
            tree=tree,
            workspace=workspace,
        )
        if cached is not None:
            return cached
        observations: list[dict[str, str]] = []
        context: RustRuleContext = RustRuleContext(
            root=root,
            tree=tree,
            workspace=workspace,
            config=config,
            rule=rule,
            file_facts=None,
            observations=observations,
        )
        findings: list[dict[str, object]] = RustRuleExecutor._serialize_findings(
            root=root,
            rule=rule,
            faults=rule.check(
                **{
                    rule.subject_parameter or "project": Project(),
                    rule.context_parameter or "ctx": context,
                }
            )
            if rule.check is not None
            else [],
            warning=warning,
        )
        cache.write(
            rule=rule,
            subject_kind="project",
            subject_identity=".",
            findings=findings,
            dependencies=observations,
        )
        return findings, observations

    @staticmethod
    def _serialize_findings(
        *, root: Path, rule: RuleSpec, faults: object, warning: bool
    ) -> list[dict[str, object]]:
        if not isinstance(faults, list) or any(not isinstance(fault, Fault) for fault in faults):
            raise RustCustomRuleError(f"Rust custom rule {rule.code} must return list[Fault]")
        fault_values: list[Fault] = cast("list[Fault]", faults)
        values: list[dict[str, object]] = []
        for fault in fault_values:
            if fault.code != rule.code:
                raise RustCustomRuleError(
                    f"Rust custom rule {rule.code} returned a fault for different code {fault.code}"
                )
            path: Path = fault.path.resolve()
            if not path.is_relative_to(root):
                raise RustCustomRuleError(
                    f"Rust custom rule {rule.code} returned a path outside the project"
                )
            values.append(
                {
                    "code": fault.code,
                    "path": path.relative_to(root).as_posix(),
                    "line": fault.line,
                    "column": fault.column,
                    "symbol": None,
                    "message": fault.message,
                    "remediation": fault.remediation,
                    "severity": "warning" if warning else "blocking",
                }
            )
        return values
