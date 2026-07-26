"""Fixed numeric limits for role rules."""

from __future__ import annotations

from fensu.rules.authoring.models import RuleLimit
from fensu.rules.roles.types import RoleCode


def get_role_rule_limits(code: RoleCode) -> tuple[RuleLimit, ...]:
    """Return fixed numeric cardinalities owned by one role rule."""

    limits: dict[RoleCode, tuple[RuleLimit, ...]] = {
        RoleCode.ENTRY_MODULE_SHAPE: (
            RuleLimit(
                name="required_public_functions",
                description="Required public entry functions",
                value=1,
            ),
            RuleLimit(
                name="maximum_private_functions",
                description="Maximum private glue functions",
                value=2,
            ),
        ),
        RoleCode.TOOLING_ENTRYPOINT_SHAPE: (
            RuleLimit(
                name="required_main_functions",
                description="Required public main functions",
                value=1,
            ),
        ),
    }
    return limits.get(code, ())
