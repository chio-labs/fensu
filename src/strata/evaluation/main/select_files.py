"""Select direct evaluation targets while retaining complete project context."""

from strata.config.exceptions import ConfigError
from strata.config.main.path_matches import path_matches
from strata.config.models import EvaluationConfig
from strata.discovery.constants import SNAPSHOT_TABLE
from strata.discovery.models import DiscoveredTree, ScopedFile
from strata.evaluation.models import EvaluationSelection


def select_evaluation_files(
    *, tree: DiscoveredTree, config: EvaluationConfig
) -> EvaluationSelection:
    """Return validated direct targets without changing the discovered tree."""

    discovered_count: int = len(tree.files)
    if not config.include and not config.exclude:
        return EvaluationSelection(
            files=tree.files,
            discovered_count=discovered_count,
            excluded_count=0,
            filtered=False,
        )
    repository_paths: tuple[tuple[ScopedFile, str], ...] = tuple(
        (scoped_file, _repository_path(tree=tree, scoped_file=scoped_file))
        for scoped_file in tree.files
    )
    for pattern in config.include:
        if not any(path_matches(patterns=(pattern,), path=path) for _, path in repository_paths):
            raise ConfigError(
                f"Evaluation include pattern matched no discovered Python files: {pattern}."
            )
    selected: tuple[ScopedFile, ...] = tuple(
        scoped_file
        for scoped_file, path in repository_paths
        if (not config.include or path_matches(patterns=config.include, path=path))
        and not path_matches(patterns=config.exclude, path=path)
    )
    if not selected:
        raise ConfigError(
            "Evaluation configuration selects zero Python files; exclusions removed all targets."
        )
    return EvaluationSelection(
        files=selected,
        discovered_count=discovered_count,
        excluded_count=discovered_count - len(selected),
        filtered=bool(config.include or config.exclude),
    )


def _repository_path(*, tree: DiscoveredTree, scoped_file: ScopedFile) -> str:
    snapshot_path: str | None = SNAPSHOT_TABLE.relative_path(
        path=scoped_file.path,
        repo_root=tree.repo_root.path,
    )
    if snapshot_path is not None:
        return snapshot_path
    return scoped_file.path.relative_to(tree.repo_root.path).as_posix()
