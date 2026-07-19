"""Inspect default repository-local generated skills during normal checks."""

from pathlib import Path

from fensu.agentdocs.exceptions import SkillInstallError
from fensu.agentdocs.main.build_generation_context import build_generation_context
from fensu.agentdocs.main.build_install_plan import build_install_plan
from fensu.agentdocs.main.check_install import check_skill_install
from fensu.agentdocs.models import (
    SkillFreshnessResult,
    SkillGenerationContext,
    SkillInstallPlan,
)
from fensu.config.models import LoadedConfig
from fensu.rules.catalog.models import RuleSelection


def installed_skill_is_stale(
    *,
    loaded: LoadedConfig,
    selection: RuleSelection,
    project_root: Path,
    invocation_root: Path,
) -> bool:
    """Return staleness for owned existing defaults, degrading safely on inspection errors."""

    try:
        context: SkillGenerationContext = build_generation_context(
            config=loaded.config,
            source=loaded.source,
            project_root=project_root,
            selection=selection,
            invocation_root=invocation_root,
        )
        plan: SkillInstallPlan = build_install_plan(context=context)
        result: SkillFreshnessResult = check_skill_install(plan=plan, authoritative=False)
    except (OSError, SkillInstallError):
        return False
    return bool(result.issues)
