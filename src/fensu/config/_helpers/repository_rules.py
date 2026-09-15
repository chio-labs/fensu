"""Build repository-owned custom-rule policy independently of analyzer targets."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from pathlib import Path

from fensu.config._helpers.defaults import build_config
from fensu.config._helpers.rule_options import resolve_rule_options
from fensu.config._helpers.validate import validate_config
from fensu.config.constants import (
    REPOSITORY_RULE_CONFIG_KEYS,
    REPOSITORY_RULES_CONFIG_KEY,
    RULE_EXCEPTION_SYMBOLS_CONFIG_KEY,
    TARGETS_CONFIG_KEY,
)
from fensu.config.exceptions import ConfigValidationError
from fensu.config.models import Config, ConfigSource, LoadedConfig
from fensu.config.types import AnalyzerId
from fensu.rules.authoring.models import RuleSpec
from fensu.rules.authoring.types import RuleOptionValue, RuleSubjectKind
from fensu.rules.catalog.main.build_catalogue import build_catalogue


def build_repository_rule_config(
    *, source: ConfigSource, parsed: Mapping[str, object]
) -> LoadedConfig | None:
    """Return the isolated repository custom-rule policy from parsed configuration."""

    raw_policy: object = parsed.get(REPOSITORY_RULES_CONFIG_KEY)
    if raw_policy is None:
        return None
    policy: dict[str, object] = _repository_policy(parsed=parsed, raw=raw_policy)
    repository_root: Path = source.path.parent.resolve()
    bootstrap: Config = build_config(raw=policy, analyzer=AnalyzerId.PYTHON)
    catalogue: tuple[RuleSpec, ...] = tuple(
        rule
        for rule in build_catalogue(config=bootstrap, repo_root=repository_root)
        if rule.subject_kind is RuleSubjectKind.REPOSITORY
    )
    resolved_options: Mapping[str, Mapping[str, RuleOptionValue]] = resolve_rule_options(
        raw=policy.get("rule_options"), rules=catalogue
    )
    config: Config = replace(
        build_config(
            raw=policy,
            rule_options=resolved_options,
            analyzer=AnalyzerId.PYTHON,
        ),
        analyzer=AnalyzerId.PYTHON,
    )
    raw_options: object = policy.get("rule_options")
    configured_rule_option_codes: tuple[str, ...] = (
        tuple(sorted(str(code) for code in raw_options)) if isinstance(raw_options, Mapping) else ()
    )
    return LoadedConfig(
        config=config,
        source=source,
        catalogue=catalogue,
        configured_rule_option_codes=configured_rule_option_codes,
    )


def _repository_policy(*, parsed: Mapping[str, object], raw: object) -> dict[str, object]:
    if TARGETS_CONFIG_KEY not in parsed:
        raise ConfigValidationError("Repository rules require explicit named analyzer targets.")
    if not isinstance(raw, Mapping):
        raise ConfigValidationError("Config key repository_rules must be a table.")
    unknown: set[object] = set(raw) - REPOSITORY_RULE_CONFIG_KEYS
    if unknown:
        names: str = ", ".join(sorted(str(name) for name in unknown))
        raise ConfigValidationError(f"Unknown repository_rules config key(s): {names}.")
    policy: dict[str, object] = {"roots": ["."], "select": []}
    policy.update({str(key): value for key, value in raw.items()})
    exceptions: object = policy.get("rule_exceptions")
    if isinstance(exceptions, list) and any(
        isinstance(entry, Mapping) and RULE_EXCEPTION_SYMBOLS_CONFIG_KEY in entry
        for entry in exceptions
    ):
        raise ConfigValidationError(
            "Repository rule exceptions support file-level exceptions only; remove symbols."
        )
    validate_config(raw=policy, analyzer=None)
    return policy
