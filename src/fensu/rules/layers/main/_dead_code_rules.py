"""Opt-in Python reachability diagnostic identities."""

from functools import partial

from fensu.rules.authoring.models import RuleSpec
from fensu.rules.authoring.types import ExecutionOwner, Family, RuleSubjectKind
from fensu.rules.layers._helpers.dead_code import check_dead_code
from fensu.rules.layers.types import LayerCode


def dead_code_rules() -> tuple[RuleSpec, ...]:
    """Describe enforced reachability diagnostics, disabled without explicit opt-in."""

    return tuple(
        RuleSpec(
            code=code,
            family=Family.LAYERS,
            slug=slug,
            message=message,
            remediation=(
                "Investigate the production entry mechanism before deleting code. "
                "Preserve deliberate public exports and use reasoned roots for dynamic dispatch."
            ),
            execution_owner=ExecutionOwner.PROJECT,
            subject_kind=RuleSubjectKind.PROJECT,
            subject_parameter="project",
            context_parameter="ctx",
            check=partial(check_dead_code, code=code),
            uses_module=False,
            configuration_inputs=("dead_code", "roots", "tests", "evaluation"),
            enabled_by_default=False,
        )
        for code, slug, message in (
            (
                LayerCode.UNREACHABLE_DEFINITION,
                "unreachable-definition",
                "definition is unreachable from production roots",
            ),
            (
                LayerCode.STALE_DEAD_CODE_ROOT,
                "stale-dead-code-root",
                "configured root matches no existing production declaration",
            ),
            (
                LayerCode.UNREACHABLE_MODULE,
                "unreachable-module",
                "module is unreachable from production roots",
            ),
        )
    )
