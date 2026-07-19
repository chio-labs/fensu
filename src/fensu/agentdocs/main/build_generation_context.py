"""Build immutable skill-generation inputs from resolved project policy."""

from __future__ import annotations

from pathlib import Path

from fensu.agentdocs._helpers.identity import (
    project_prefix,
    resolve_install_root,
    resolve_skill_name,
)
from fensu.agentdocs.models import SkillGenerationContext
from fensu.config.models import Config, ConfigSource
from fensu.rules.catalog.models import RuleSelection


def build_generation_context(
    *,
    config: Config,
    source: ConfigSource,
    project_root: Path,
    selection: RuleSelection,
    install_root: str | None = None,
    invocation_root: Path | None = None,
) -> SkillGenerationContext:
    """Build deterministic project identity and path-aware generation inputs."""

    resolved_root: Path = project_root.resolve()
    resolved_install_root: Path
    git_root: Path | None
    resolved_install_root, git_root = resolve_install_root(
        value=install_root,
        project_root=resolved_root,
        invocation_root=(invocation_root or resolved_root).resolve(),
    )
    return SkillGenerationContext(
        config_source=source,
        project_root=resolved_root,
        install_root=resolved_install_root,
        git_root=git_root,
        project_prefix=project_prefix(
            project_root=resolved_root,
            install_root=resolved_install_root,
        ),
        identity=resolve_skill_name(
            config=config,
            source=source,
            project_root=resolved_root,
            git_root=git_root,
        ),
        catalogue=selection.catalogue,
        blocking_rules=selection.blocking,
        warning_rules=selection.warnings,
        ignored_rules=selection.ignored,
        config=config,
    )
