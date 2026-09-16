"""Analyzer-neutral coverage policy for configured Python-authored rules."""

from __future__ import annotations

from pathlib import Path

from fensu.analysis.exceptions import PythonSourceParseError
from fensu.analysis.main.associate_rule_tests import associate_rule_tests
from fensu.analysis.main.build import build_analysis
from fensu.analysis.main.parse_source import parse_python_source
from fensu.analysis.models import EvaluateRuleCallFact, RuleTestAssociationFact
from fensu.analysis.types import Analysis, PythonSourceArtifact
from fensu.config.main.resolve_threshold import resolve_threshold
from fensu.config.models import Config
from fensu.discovery.constants import INIT_MODULE_NAME
from fensu.discovery.main.position import position_facts
from fensu.discovery.models import ScopedFile
from fensu.discovery.types import ScopeName
from fensu.rules.authoring.models import CustomRuleRegistration, RuleSpec
from fensu.rules.authoring.types import Threshold


class CustomRuleCoverageEvaluator:
    """Evaluate public-harness coverage for every configured custom-rule declaration."""

    @staticmethod
    def evaluate(
        *,
        root: Path,
        config: Config,
        registrations: tuple[CustomRuleRegistration, ...],
        rule: RuleSpec,
        warning: bool,
    ) -> list[dict[str, object]]:
        """Return declaration-owned findings for statically unproven harness coverage."""

        if not registrations:
            return []
        modules: dict[str, Analysis] = {}
        calls: list[EvaluateRuleCallFact] = []
        for configured_root in sorted(config.tests):
            test_root: Path = root / configured_root
            if not test_root.is_dir():
                continue
            for test_path in sorted(test_root.rglob("*.py")):
                if test_path.is_symlink() or not test_path.resolve().is_relative_to(root):
                    continue
                analysis: Analysis | None = CustomRuleCoverageEvaluator._analysis(path=test_path)
                if analysis is None:
                    continue
                modules[
                    CustomRuleCoverageEvaluator._module_name(
                        path=test_path, import_root=test_root.parent
                    )
                ] = analysis
                calls.extend(analysis.facts.evaluate_rule_calls())
        for registration in registrations:
            analysis = CustomRuleCoverageEvaluator._analysis(path=registration.source_path)
            if analysis is not None:
                modules[registration.module_name] = analysis
        associations: tuple[RuleTestAssociationFact, ...] = associate_rule_tests(
            calls=tuple(calls), modules=modules
        )
        findings: list[dict[str, object]] = []
        for registration in registrations:
            repository_path: str = registration.source_path.relative_to(root).as_posix()
            minimum: int = resolve_threshold(
                config=config,
                name=Threshold.MIN_CUSTOM_RULE_TEST_CASES,
                path=repository_path,
                role=CustomRuleCoverageEvaluator._registration_role(
                    root=root, config=config, path=registration.source_path
                ),
            ).effective_value
            if minimum == 0:
                continue
            matching: tuple[RuleTestAssociationFact, ...] = tuple(
                item
                for item in associations
                if item.rule_reference.module_name == registration.module_name
                and item.rule_reference.symbol_name == registration.function_name
            )
            count: int = sum(item.provable_case_count for item in matching)
            dynamic: bool = any(item.unknown_case_count for item in matching)
            if count >= minimum:
                continue
            message: str = (
                f"custom rule {registration.rule.code} has associated tests with dynamically "
                f"determined case counts; the configured minimum of {minimum} cannot be "
                "statically proven"
                if dynamic
                else f"custom rule {registration.rule.code} has {count} statically declared test "
                f"cases; at least {minimum} is required"
            )
            findings.append(
                {
                    "code": rule.code,
                    "path": repository_path,
                    "line": registration.declaration_line,
                    "column": registration.declaration_column,
                    "symbol": None,
                    "message": message,
                    "remediation": rule.remediation,
                    "severity": "warning" if warning else "blocking",
                }
            )
        return findings

    @staticmethod
    def _analysis(*, path: Path) -> Analysis | None:
        try:
            artifact: PythonSourceArtifact = parse_python_source(
                path=path, content=path.read_bytes()
            )
        except (OSError, PythonSourceParseError):
            return None
        return build_analysis(path=path, source=artifact.source, module=artifact.module)

    @staticmethod
    def _registration_role(*, root: Path, config: Config, path: Path) -> str | None:
        configured: list[tuple[ScopeName, Path]] = [
            *((ScopeName.ROOT, root / value) for value in config.roots),
            *((ScopeName.TEST, root / value) for value in config.tests),
            *((ScopeName.TOOLING, root / value) for value in config.tooling),
        ]
        configured.sort(key=lambda item: len(item[1].parts), reverse=True)
        matching: tuple[ScopeName, Path] | None = next(
            (
                (scope, scope_root)
                for scope, scope_root in configured
                if path.is_relative_to(scope_root)
            ),
            None,
        )
        scope, scope_root = matching or (ScopeName.TOOLING, root)
        return position_facts(
            ScopedFile(
                path=path,
                root=scope_root,
                scope=scope,
                relative_parts=path.relative_to(scope_root).parts,
            )
        ).role

    @staticmethod
    def _module_name(*, path: Path, import_root: Path) -> str:
        parts: tuple[str, ...] = path.relative_to(import_root).with_suffix("").parts
        if parts and parts[-1] == INIT_MODULE_NAME:
            parts = parts[:-1]
        return ".".join(parts)
