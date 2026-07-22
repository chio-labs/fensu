"""Apply additive selector-and-path finding suppression."""

from __future__ import annotations

from pathlib import Path

from fensu.config.main.matches_path_pattern import matches_path_pattern
from fensu.config.models import Config, RuleIgnoreEntry
from fensu.rules.authoring.main.matches_rule_selector import matches_rule_selector
from fensu.rules.authoring.models import Fault


def visible_faults(*, faults: list[Fault], config: Config, repo_root: Path) -> list[Fault]:
    """Return findings not matched by one complete path-scoped ignore declaration."""

    return [
        fault
        for fault in faults
        if not _ignored(fault=fault, entries=config.rule_ignores, repo_root=repo_root)
    ]


def _ignored(*, fault: Fault, entries: tuple[RuleIgnoreEntry, ...], repo_root: Path) -> bool:
    try:
        repository_path: str = fault.path.relative_to(repo_root).as_posix()
    except ValueError:
        return False
    return any(
        _entry_ignores(fault=fault, entry=entry, repository_path=repository_path)
        for entry in entries
    )


def _entry_ignores(*, fault: Fault, entry: RuleIgnoreEntry, repository_path: str) -> bool:
    selector_matches: bool = any(
        matches_rule_selector(code=fault.code, selector=selector) for selector in entry.rules
    )
    return selector_matches and matches_path_pattern(patterns=entry.paths, path=repository_path)
