"""Resolve detected, explicit, and prompted initialization choices."""

from __future__ import annotations

from pathlib import Path
from typing import TextIO

from strata.config.main.find_config import find_config_source
from strata.config.models import ConfigSource
from strata.reporting.classes.cli_style import CliStyle
from strata.scaffolding.constants import (
    CONFIG_FILE_NAME,
    CURRENT_PATH_TEXT,
    DEFAULT_TEST_PATH,
    PARENT_PATH_PART,
)
from strata.scaffolding.exceptions import InitError, InitRefusalError
from strata.scaffolding.helpers.output import (
    normalize_project_name,
    prompt_accept_layout,
    prompt_paths,
    prompt_project_name,
    prompt_root_selection,
    prompt_yes_no,
    write_detected_layout,
    write_header,
)
from strata.scaffolding.models import (
    DetectedRepositoryLayout,
    InitOptions,
    InitPlan,
    PathCandidate,
)
from strata.scaffolding.types import (
    AdoptionMode,
    CandidateProvenance,
    InteractionDecision,
)


def preflight_existing_config(*, repository: Path) -> None:
    """Refuse initialization when this directory inherits any Strata config."""

    local_path: Path = repository / CONFIG_FILE_NAME
    if local_path.is_symlink():
        raise InitRefusalError(f"Strata configuration path is a symlink: {local_path}")
    source: ConfigSource | None = find_config_source(repository)
    if source is not None:
        raise InitRefusalError(f"Strata configuration already exists: {source.path}")


def validate_option_applicability(
    *, options: InitOptions, detected: DetectedRepositoryLayout
) -> None:
    """Reject options that cannot apply to the detected repository state."""

    if detected.python.is_empty:
        explicit_scopes: bool = any(
            value is not None for value in (options.roots, options.tests, options.tooling)
        )
        if explicit_scopes:
            raise InitError(
                "Explicit --root, --tests, and --tooling options do not apply to an empty "
                "scaffold; use --name to choose its package."
            )
        return
    if options.name is not None:
        raise InitError("--name only applies when no Python package is detected.")
    if options.roots is not None:
        _ = _validate_paths(values=options.roots, field="roots")
    if options.tests is not None:
        _ = _validate_paths(values=options.tests, field="tests")
    if options.tooling is not None:
        _ = _validate_paths(values=options.tooling, field="tooling", allow_empty=True)


def interaction_decision(
    *, options: InitOptions, detected: DetectedRepositoryLayout
) -> InteractionDecision:
    """Decide whether unresolved choices require a terminal before output starts."""

    if options.yes:
        return InteractionDecision.NON_INTERACTIVE
    if detected.python.is_empty:
        unresolved: bool = options.name is None or options.skills is None
        return _decision(unresolved=unresolved)
    unresolved_layout: bool = options.roots is None or options.tests is None
    unresolved_tooling: bool = bool(detected.tooling) and options.tooling is None
    unresolved_final: bool = options.skills is None
    return _decision(unresolved=unresolved_layout or unresolved_tooling or unresolved_final)


def build_init_plan(
    *,
    repository: Path,
    detected: DetectedRepositoryLayout,
    options: InitOptions,
    stdin: TextIO,
    stdout: TextIO,
    style: CliStyle,
) -> InitPlan:
    """Build complete choices without leaving any question partially answered."""

    if detected.python.is_empty:
        return _empty_plan(
            repository=repository,
            options=options,
            stdin=stdin,
            stdout=stdout,
            style=style,
        )
    displayed_roots: tuple[PathCandidate, ...] = _effective_candidates(
        repository=repository, configured=options.roots, detected=detected.roots
    )
    displayed_tests: tuple[PathCandidate, ...] = _effective_candidates(
        repository=repository, configured=options.tests, detected=detected.tests
    )
    displayed_tooling: tuple[PathCandidate, ...] = _effective_candidates(
        repository=repository, configured=options.tooling, detected=detected.tooling
    )
    write_detected_layout(
        stdout=stdout,
        style=style,
        roots=displayed_roots,
        tests=displayed_tests,
        tooling=displayed_tooling,
    )
    roots: tuple[str, ...] = _runtime_roots(
        detected=detected, options=options, stdin=stdin, stdout=stdout, style=style
    )
    tests: tuple[str, ...] = _configured_or_detected(
        configured=options.tests,
        detected=tuple(candidate.path for candidate in detected.tests),
        fallback=(DEFAULT_TEST_PATH,),
        field="tests",
    )
    roots, tests = _confirm_layout(
        roots=roots,
        tests=tests,
        options=options,
        stdin=stdin,
        stdout=stdout,
        style=style,
    )
    tooling: tuple[str, ...] = _tooling_scope(
        detected=detected, options=options, stdin=stdin, stdout=stdout, style=style
    )
    count: int = count_runtime_python_files(repository=repository, roots=roots)
    adoption: AdoptionMode = options.adoption or (
        AdoptionMode.GRADUAL if count else AdoptionMode.FULL
    )
    return InitPlan(roots=roots, tests=tests, tooling=tooling, adoption=adoption)


def count_runtime_python_files(*, repository: Path, roots: tuple[str, ...]) -> int:
    """Count Python files under chosen runtime roots only."""

    files: set[Path] = set()
    resolved_repository: Path = repository.resolve()
    for value in roots:
        root: Path = repository / value
        resolved_root: Path = root.resolve()
        try:
            resolved_root.relative_to(resolved_repository)
        except ValueError:
            continue
        if not root.is_dir():
            continue
        for path in root.rglob("*.py"):
            resolved_path: Path = path.resolve()
            try:
                resolved_path.relative_to(resolved_repository)
            except ValueError:
                continue
            if path.is_file() and not path.is_symlink():
                files.add(resolved_path)
    return len(files)


def _empty_plan(
    *,
    repository: Path,
    options: InitOptions,
    stdin: TextIO,
    stdout: TextIO,
    style: CliStyle,
) -> InitPlan:
    write_header(stdout=stdout, style=style, text="Empty repository")
    stdout.write("\n")
    if options.name is not None:
        project_name: str = normalize_project_name(value=options.name)
    elif options.yes:
        project_name = normalize_project_name(value=repository.name)
    else:
        project_name = prompt_project_name(
            stdin=stdin,
            stdout=stdout,
            style=style,
            repository_name=repository.name,
        )
    return InitPlan(
        roots=(f"src/{project_name}",),
        tests=(DEFAULT_TEST_PATH,),
        tooling=(),
        adoption=options.adoption or AdoptionMode.FULL,
        project_name=project_name,
    )


def _runtime_roots(
    *,
    detected: DetectedRepositoryLayout,
    options: InitOptions,
    stdin: TextIO,
    stdout: TextIO,
    style: CliStyle,
) -> tuple[str, ...]:
    if options.roots is not None:
        return _validate_paths(values=options.roots, field="roots")
    candidates: tuple[str, ...] = tuple(candidate.path for candidate in detected.roots)
    if options.yes:
        if not candidates:
            raise InitError("No runtime roots detected; pass --root with a package path.")
        return candidates
    if len(detected.roots) > 1:
        return prompt_root_selection(
            stdin=stdin, stdout=stdout, style=style, candidates=detected.roots
        )
    if candidates:
        return candidates
    return prompt_paths(stdin=stdin, stdout=stdout, style=style, field="roots", default=())


def _confirm_layout(
    *,
    roots: tuple[str, ...],
    tests: tuple[str, ...],
    options: InitOptions,
    stdin: TextIO,
    stdout: TextIO,
    style: CliStyle,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    if options.yes or (options.roots is not None and options.tests is not None):
        return roots, tests
    if prompt_accept_layout(stdin=stdin, stdout=stdout, style=style):
        stdout.write("\n")
        return roots, tests
    edited_roots: tuple[str, ...] = prompt_paths(
        stdin=stdin, stdout=stdout, style=style, field="roots", default=roots
    )
    edited_tests: tuple[str, ...] = prompt_paths(
        stdin=stdin, stdout=stdout, style=style, field="tests", default=tests
    )
    stdout.write("\n")
    return edited_roots, edited_tests


def _tooling_scope(
    *,
    detected: DetectedRepositoryLayout,
    options: InitOptions,
    stdin: TextIO,
    stdout: TextIO,
    style: CliStyle,
) -> tuple[str, ...]:
    if options.tooling is not None:
        return _validate_paths(values=options.tooling, field="tooling", allow_empty=True)
    candidates: tuple[str, ...] = tuple(candidate.path for candidate in detected.tooling)
    if not candidates or options.yes:
        return candidates
    write_header(stdout=stdout, style=style, text="Tooling scope")
    stdout.write("\n")
    paths: str = ", ".join(style.path(f"{path}/") for path in candidates)
    accepted: bool = prompt_yes_no(
        stdin=stdin,
        stdout=stdout,
        style=style,
        prompt=f"    Found {paths} with Python files. Use it?",
    )
    stdout.write("\n")
    return candidates if accepted else ()


def _configured_or_detected(
    *,
    configured: tuple[str, ...] | None,
    detected: tuple[str, ...],
    fallback: tuple[str, ...],
    field: str,
) -> tuple[str, ...]:
    if configured is None:
        return detected or fallback
    return _validate_paths(values=configured, field=field)


def _effective_candidates(
    *,
    repository: Path,
    configured: tuple[str, ...] | None,
    detected: tuple[PathCandidate, ...],
) -> tuple[PathCandidate, ...]:
    if configured is None:
        return detected
    return tuple(
        PathCandidate(
            path=value,
            provenance=CandidateProvenance.COMMAND_LINE,
            present=(repository / value).is_dir(),
        )
        for value in configured
    )


def _validate_paths(
    *, values: tuple[str, ...], field: str, allow_empty: bool = False
) -> tuple[str, ...]:
    if not values and allow_empty:
        return ()
    paths: tuple[Path, ...] = tuple(Path(value) for value in values)
    if not paths or any(
        path.is_absolute() or PARENT_PATH_PART in path.parts or path.as_posix() == CURRENT_PATH_TEXT
        for path in paths
    ):
        raise InitError(f"Invalid repository-relative {field}: {values!r}.")
    normalized: tuple[str, ...] = tuple(path.as_posix() for path in paths)
    if len(set(normalized)) != len(normalized):
        raise InitError(f"Duplicate {field} paths are not allowed: {values!r}.")
    return normalized


def _decision(*, unresolved: bool) -> InteractionDecision:
    return InteractionDecision.TTY_REQUIRED if unresolved else InteractionDecision.NON_INTERACTIVE
