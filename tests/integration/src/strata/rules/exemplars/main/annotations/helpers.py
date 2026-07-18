"""Comparison helpers for native and public custom-rule diagnostics."""

from strata import Fault
from strata.rules.annotations.constants import SFA_RULES
from strata.rules.authoring.models import RuleSpec
from strata.rules.hygiene.constants import SFH_RULES
from strata.rules.naming.constants import SFN_RULES
from strata.rules.shape.constants import SFS_RULES

_NATIVE_RULES_BY_CODE: dict[str, RuleSpec] = {
    rule.code: rule for rule in (*SFA_RULES, *SFH_RULES, *SFN_RULES, *SFS_RULES)
}


def native_rule(code: str) -> RuleSpec:
    """Return one core rule spec by code."""

    return _NATIVE_RULES_BY_CODE[code]


def normalized_faults(
    faults: tuple[Fault, ...],
) -> tuple[tuple[int | None, int | None, str, str | None], ...]:
    """Remove the intentionally different rule code from parity output."""

    return tuple((fault.line, fault.column, fault.message, fault.remediation) for fault in faults)
