"""Comparison helpers for native and public custom-rule diagnostics."""

from fensu import Fault
from fensu.rules.annotations.constants import FFA_RULES
from fensu.rules.authoring.models import RuleSpec
from fensu.rules.hygiene.constants import FFH_RULES
from fensu.rules.layers.constants import FFL_RULES
from fensu.rules.naming.constants import FFN_RULES
from fensu.rules.roles.constants import FFR_RULES
from fensu.rules.shape.constants import FFS_RULES
from fensu.rules.tests.constants import FFT_RULES

_NATIVE_RULES_BY_CODE: dict[str, RuleSpec] = {
    rule.code: rule
    for rule in (*FFA_RULES, *FFH_RULES, *FFL_RULES, *FFN_RULES, *FFR_RULES, *FFS_RULES, *FFT_RULES)
}


def native_rule(code: str) -> RuleSpec:
    """Return one core rule spec by code."""

    return _NATIVE_RULES_BY_CODE[code]


def normalized_faults(
    faults: tuple[Fault, ...],
) -> tuple[tuple[int | None, int | None, str, str | None], ...]:
    """Remove the intentionally different rule code from parity output."""

    return tuple((fault.line, fault.column, fault.message, fault.remediation) for fault in faults)
