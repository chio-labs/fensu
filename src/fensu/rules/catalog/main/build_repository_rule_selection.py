"""Build repository-subject custom-rule selection for one target registry."""

from pathlib import Path

from fensu.config.exceptions import ConfigError
from fensu.config.models import LoadedConfig
from fensu.config.types import AnalyzerId
from fensu.rules.catalog._helpers.loading import (
    build_repository_rule_selection_from_catalogue,
)
from fensu.rules.catalog.models import RuleSelection


def build_repository_rule_selection(
    *, loaded: LoadedConfig, target_analyzers: frozenset[AnalyzerId], repo_root: Path
) -> RuleSelection:
    """Return selected repository rules whose analyzer capabilities are configured."""

    selection: RuleSelection = build_repository_rule_selection_from_catalogue(
        config=loaded.config,
        catalogue=loaded.catalogue,
        target_analyzers=target_analyzers,
        repo_root=repo_root,
    )
    selected_codes: frozenset[str] = frozenset(
        rule.code for rule in (*selection.blocking, *selection.warnings)
    )
    unselected_options: tuple[str, ...] = tuple(
        sorted(
            code
            for code in loaded.configured_rule_option_codes
            if code.startswith("X") and code not in selected_codes
        )
    )
    if unselected_options:
        raise ConfigError(
            "Repository custom rule options require a selected custom rule: "
            f"{', '.join(unselected_options)}."
        )
    return selection
