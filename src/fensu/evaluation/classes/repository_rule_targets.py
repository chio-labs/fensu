"""Deterministic name-indexed target collection for repository rules."""

from fensu.evaluation.classes.repository_rule_target import RepositoryRuleTargetView
from fensu.rules.authoring.exceptions import TargetFactQueryTypeError


class RepositoryRuleTargets:
    """Name-indexed target handles for one repository-rule invocation."""

    def __init__(self, *, values: tuple[RepositoryRuleTargetView, ...]) -> None:
        self._values = tuple(sorted(values, key=lambda item: item.identity.name))
        self._by_name = {item.identity.name: item for item in self._values}

    def all(self) -> tuple[RepositoryRuleTargetView, ...]:
        """Return all configured targets in deterministic name order."""

        return self._values

    def named(self, name: str) -> RepositoryRuleTargetView | None:
        """Return one configured target by exact name."""

        if not isinstance(name, str):
            raise TargetFactQueryTypeError("target names must be strings")
        return self._by_name.get(name)
