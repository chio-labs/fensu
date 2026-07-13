"""Build the effective rule selection for one check invocation."""

from __future__ import annotations

from pathlib import Path

from strata.config.models import Config
from strata.rules.authoring.models import RuleSpec
from strata.rules.catalog._helpers.hermeticity import validate_cacheable_rules
from strata.rules.catalog._helpers.loading import build_rule_selection_from_config
from strata.rules.catalog.models import RuleSelection


def build_check_rule_selection(
    *, config: Config, repo_root: Path, include_warnings: bool
) -> RuleSelection:
    """Resolve tiers and validate cacheability only for rules this check evaluates."""

    selection: RuleSelection = build_rule_selection_from_config(
        config=config,
        repo_root=repo_root,
    )
    evaluated_warning_rules: tuple[RuleSpec, ...] = selection.warnings if include_warnings else ()
    validate_cacheable_rules(
        rules=(*selection.blocking, *evaluated_warning_rules),
        allowed_packages=frozenset(name.partition(".")[0] for name in config.rule_modules),
    )
    return RuleSelection(
        catalogue=selection.catalogue,
        blocking=selection.blocking,
        warnings=selection.warnings,
        ignored=selection.ignored,
        custom_registrations=selection.custom_registrations,
    )
