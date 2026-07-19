"""Inspect default repository-local generated skills during normal checks."""

from pathlib import Path

from strata.agentdocs.exceptions import SkillInstallError
from strata.agentdocs.main.build_generation_context import build_generation_context
from strata.agentdocs.main.build_install_plan import build_install_plan
from strata.agentdocs.main.check_install import check_skill_install
from strata.agentdocs.models import (
    SkillFreshnessResult,
    SkillGenerationContext,
    SkillInstallPlan,
)
from strata.config.models import LoadedConfig
from strata.rules.catalog.models import RuleSelection


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
