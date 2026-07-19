"""Render the deterministic effective project policy snapshot."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

from fensu.agentdocs.models import SkillGenerationContext
from fensu.config.models import Config, RuleExceptionEntry, ThresholdOverride
from fensu.config.types import ConfigSourceKind
from fensu.rules.authoring.models import RuleSpec
from fensu.rules.authoring.types import Threshold


def effective_config_lines(context: SkillGenerationContext) -> tuple[str, ...]:
    """Return configured declarations and separately resolved policy values."""

    config: Config = context.config
    lines: list[str] = [
        "## Effective Project Configuration",
        "",
        "This is the loaded effective configuration, not a template. Lists and mappings are "
        "rendered deterministically; path-threshold declarations retain declaration order because "
        "that order breaks equally specific matches.",
        "",
        f"- Configuration source: {_config_source(context)}",
        "- Project root from installation root: "
        f"{_relative_path(path=context.project_root, root=context.install_root)}",
        "- Installation root: "
        f"{_relative_path(path=context.install_root, root=context.install_root)}",
        f"- Current skill identity: {_json(context.identity)}",
        f"- Complete loaded catalogue size: {len(context.catalogue)}",
        "",
        "### Scopes",
        "",
        f"- Product roots: {_json(_project_paths(context=context, paths=config.roots))}",
        f"- Test roots: {_json(_project_paths(context=context, paths=config.tests))}",
        f"- Tooling roots: {_json(_project_paths(context=context, paths=config.tooling))}",
        "",
        "### Configured Rule Selectors",
        "",
        f"- Blocking selectors (`select`): {_json(sorted(config.select))}",
        f"- Warning selectors (`warn`): {_json(sorted(config.warn))}",
        f"- Ignore selectors (`ignore`): {_json(sorted(config.ignore))}",
        "",
        "### Resolved Rule Sets",
        "",
        f"- Blocking rule codes: {_rule_codes(context.blocking_rules)}",
        f"- Warning rule codes: {_rule_codes(context.warning_rules)}",
        f"- Ignored matched rule codes: {_rule_codes(context.ignored_rules)}",
        "",
        "Normal work must satisfy blocking policy. Warnings are review signals, not scope "
        "authorization. Run `fensu check --warn` after substantial changes when practical, and "
        "never delete code or change architecture solely because of an advisory warning without "
        "verifying the actual contract.",
        "",
        "### Custom Rule Sources",
        "",
        f"- `rule_paths`: {_json(_project_paths(context=context, paths=config.rule_paths))}",
        f"- `rule_modules`: {_json(sorted(config.rule_modules))}",
        "",
        "### Cache And Evaluation",
        "",
        f"- Cache enabled: `{str(config.cache.enabled).lower()}`",
        f"- Cache requires cacheable rules: `{str(config.cache.require_cacheable).lower()}`",
        "- Evaluation include boundaries: "
        f"{_json(_project_paths(context=context, paths=config.evaluation.include))}",
        "- Evaluation exclude boundaries: "
        f"{_json(_project_paths(context=context, paths=config.evaluation.exclude))}",
        "",
        "### Effective Global Thresholds",
        "",
    ]
    lines.extend(
        f"- `{threshold.value}` = {config.thresholds[threshold]}"
        for threshold in sorted(config.thresholds, key=lambda item: item.value)
    )
    lines.extend(("", "### Configured Role Threshold Overrides", ""))
    lines.extend(_role_threshold_lines(context=context))
    lines.extend(("", "### Configured Path Threshold Overrides", ""))
    lines.extend(_path_override_lines(context=context, overrides=config.threshold_overrides))
    lines.extend(("", "### Effective Naming Contracts", ""))
    lines.extend(
        f"- {_json(pattern)} = {_json(config.contracts[pattern])}"
        for pattern in sorted(config.contracts)
    )
    lines.extend(("", "### Configured Rule Exceptions", ""))
    lines.extend(_exception_lines(context=context, exceptions=config.rule_exceptions))
    lines.append("")
    return tuple(lines)


def warning_policy_lines(context: SkillGenerationContext) -> tuple[str, ...]:
    """Return additional operational guidance when warning rules are configured."""

    if not context.warning_rules:
        return ()
    return (
        "## Warning Policy",
        "",
        "`fensu check` evaluates blocking rules only. `fensu check --warn` additionally "
        "evaluates the configured warning tier; warning-only findings do not fail the command. "
        "Treat warnings as evidence to investigate, not proof that code is safe to remove or "
        "architecture should change.",
        "",
    )


def _config_source(context: SkillGenerationContext) -> str:
    display_root: Path = context.install_root if context.project_prefix else context.project_root
    path: str = _relative_path(path=context.config_source.path, root=display_root)
    if context.config_source.kind is ConfigSourceKind.PYPROJECT:
        return f"`[tool.fensu]` in {path}"
    return path


def _relative_path(*, path: Path, root: Path) -> str:
    resolved_path: Path = path.resolve()
    resolved_root: Path = root.resolve()
    try:
        relative: Path = resolved_path.relative_to(resolved_root)
    except ValueError:
        return _json_path(resolved_path)
    display: str = relative.as_posix() or "."
    return _json(display)


def _json_path(path: Path) -> str:
    return _json(path.resolve().as_posix())


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True)


def _rule_codes(rules: tuple[RuleSpec, ...]) -> str:
    return _json(sorted(rule.code for rule in rules))


def _project_paths(*, context: SkillGenerationContext, paths: tuple[str, ...]) -> list[str]:
    return sorted(
        f"{context.project_prefix}/{path}" if context.project_prefix else path for path in paths
    )


def _role_threshold_lines(context: SkillGenerationContext) -> tuple[str, ...]:
    config: Config = context.config
    lines: list[str] = []
    for role in sorted(config.role_thresholds):
        thresholds: Mapping[Threshold, int] = config.role_thresholds[role]
        for threshold in sorted(thresholds, key=lambda item: item.value):
            lines.append(f"- Role {_json(role)}: `{threshold.value}` = {thresholds[threshold]}")
    return tuple(lines) or ("- None.",)


def _path_override_lines(
    *, context: SkillGenerationContext, overrides: tuple[ThresholdOverride, ...]
) -> tuple[str, ...]:
    lines: list[str] = []
    for declaration_order, override in enumerate(overrides, start=1):
        thresholds: dict[str, int] = {
            threshold.value: override.thresholds[threshold]
            for threshold in sorted(override.thresholds, key=lambda item: item.value)
        }
        lines.append(
            f"- Declaration {declaration_order}: "
            f"paths={_json(_project_paths(context=context, paths=override.paths))}; "
            f"thresholds={_json(thresholds)}; reason={_json(override.reason)}"
        )
    return tuple(lines) or ("- None.",)


def _exception_lines(
    *, context: SkillGenerationContext, exceptions: tuple[RuleExceptionEntry, ...]
) -> tuple[str, ...]:
    sorted_exceptions: tuple[RuleExceptionEntry, ...] = tuple(
        sorted(exceptions, key=lambda item: (item.rule, item.path, item.symbols, item.reason))
    )
    if not sorted_exceptions:
        return ("- None.",)
    lines: list[str] = []
    for exception in sorted_exceptions:
        scope: str = _json(sorted(exception.symbols)) if exception.symbols else '"file-level"'
        lines.append(
            f"- Rule {_json(exception.rule)}; "
            f"path={_json(_project_paths(context=context, paths=(exception.path,))[0])}; "
            f"scope={scope}; "
            f"reason={_json(exception.reason)}"
        )
    return tuple(lines)
