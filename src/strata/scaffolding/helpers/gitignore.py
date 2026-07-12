"""Match root comments, negation, anchors, directories, and ordinary globs conservatively."""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from strata.scaffolding.constants import (
    GITIGNORE_FILE_NAME,
    GLOBSTAR_PATTERN,
    POSIX_PATH_SEPARATOR,
)
from strata.scaffolding.types import GitIgnorePredicate


@dataclass(frozen=True, slots=True)
class _IgnoreRule:
    pattern: str
    negated: bool
    anchored: bool
    directory_only: bool


def is_gitignored(*, repository: Path, path: Path, is_directory: bool) -> bool:
    """Apply a documented stdlib subset of root .gitignore rules in declaration order."""

    predicate: GitIgnorePredicate = build_gitignore_predicate(repository=repository)
    return predicate(path=path, is_directory=is_directory)


def build_gitignore_predicate(*, repository: Path) -> GitIgnorePredicate:
    """Parse root rules once and return an immutable detection-pass predicate."""

    rules: tuple[_IgnoreRule, ...] = _load_rules(repository=repository)

    def is_ignored(*, path: Path, is_directory: bool) -> bool:
        try:
            relative: PurePosixPath = PurePosixPath(path.relative_to(repository).as_posix())
        except ValueError:
            return True
        ignored: bool = False
        for rule in rules:
            if _matches(rule=rule, relative=relative, is_directory=is_directory):
                ignored = not rule.negated
        return ignored

    return is_ignored


def _load_rules(*, repository: Path) -> tuple[_IgnoreRule, ...]:
    path: Path = repository / GITIGNORE_FILE_NAME
    if path.is_symlink() or not path.is_file():
        return ()
    rules: list[_IgnoreRule] = []
    for source_line in path.read_text(encoding="utf-8").splitlines():
        rule: _IgnoreRule | None = _parse_rule(source_line=source_line)
        if rule is not None:
            rules.append(rule)
    return tuple(rules)


def _parse_rule(*, source_line: str) -> _IgnoreRule | None:
    line: str = source_line.strip()
    if not line or line.startswith("#"):
        return None
    if line.startswith(r"\#") or line.startswith(r"\!"):
        line = line[1:]
    negated: bool = line.startswith("!")
    if negated:
        line = line[1:]
    anchored: bool = line.startswith("/")
    if anchored:
        line = line[1:]
    directory_only: bool = line.endswith("/")
    pattern: str = line.rstrip("/")
    if not pattern:
        return None
    return _IgnoreRule(
        pattern=pattern,
        negated=negated,
        anchored=anchored,
        directory_only=directory_only,
    )


def _matches(*, rule: _IgnoreRule, relative: PurePosixPath, is_directory: bool) -> bool:
    candidates: tuple[str, ...] = _match_candidates(
        relative=relative,
        include_self=is_directory or not rule.directory_only,
    )
    if rule.anchored or POSIX_PATH_SEPARATOR in rule.pattern:
        return any(
            _path_pattern_matches(candidate=candidate, pattern=rule.pattern)
            for candidate in candidates
        )
    return any(
        fnmatch.fnmatchcase(PurePosixPath(candidate).name, rule.pattern) for candidate in candidates
    )


def _match_candidates(*, relative: PurePosixPath, include_self: bool) -> tuple[str, ...]:
    parts: tuple[str, ...] = relative.parts
    limit: int = len(parts) if include_self else len(parts) - 1
    return tuple(PurePosixPath(*parts[:index]).as_posix() for index in range(1, limit + 1))


def _path_pattern_matches(*, candidate: str, pattern: str) -> bool:
    path_parts: tuple[str, ...] = PurePosixPath(candidate).parts
    pattern_parts: tuple[str, ...] = PurePosixPath(pattern).parts
    return _segment_pattern_matches(path_parts=path_parts, pattern_parts=pattern_parts)


def _segment_pattern_matches(
    *, path_parts: tuple[str, ...], pattern_parts: tuple[str, ...]
) -> bool:
    if not pattern_parts:
        return not path_parts
    pattern_head: str = pattern_parts[0]
    if pattern_head == GLOBSTAR_PATTERN:
        remaining_pattern: tuple[str, ...] = pattern_parts[1:]
        if _segment_pattern_matches(path_parts=path_parts, pattern_parts=remaining_pattern):
            return True
        return bool(path_parts) and _segment_pattern_matches(
            path_parts=path_parts[1:], pattern_parts=pattern_parts
        )
    if not path_parts or not fnmatch.fnmatchcase(path_parts[0], pattern_head):
        return False
    return _segment_pattern_matches(path_parts=path_parts[1:], pattern_parts=pattern_parts[1:])
