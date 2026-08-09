"""Select direct evaluation targets while retaining complete project context."""

from importlib import import_module
from types import ModuleType

from fensu.analysis.constants import NATIVE_FACT_MODULE_NAME
from fensu.config.exceptions import ConfigError
from fensu.config.models import EvaluationConfig
from fensu.discovery.models import DiscoveredTree, RepoRoot, ScopedFile
from fensu.evaluation.models import EvaluationSelection


def select_evaluation_files(
    *, tree: DiscoveredTree, config: EvaluationConfig
) -> EvaluationSelection:
    """Return validated direct targets without changing the discovered tree."""

    discovered_count: int = len(tree.files)
    native: ModuleType = import_module(NATIVE_FACT_MODULE_NAME)
    if not config.include and not config.exclude:
        selected_indexes, excluded_count = native.select_native_execution_files([], [], [])
        return EvaluationSelection(
            files=tree.files if selected_indexes is None else (),
            discovered_count=discovered_count,
            excluded_count=excluded_count,
            filtered=False,
        )
    repository_paths: tuple[tuple[ScopedFile, str], ...] = tuple(
        (scoped_file, _project_path(tree=tree, scoped_file=scoped_file))
        for scoped_file in tree.files
    )
    try:
        selected_indexes, excluded_count = native.select_native_execution_files(
            [path for _, path in repository_paths],
            list(config.include),
            list(config.exclude),
        )
    except ValueError as error:
        raise ConfigError(str(error)) from error
    selected: tuple[ScopedFile, ...] = tuple(
        repository_paths[index][0] for index in selected_indexes or ()
    )
    return EvaluationSelection(
        files=selected,
        discovered_count=discovered_count,
        excluded_count=excluded_count,
        filtered=bool(config.include or config.exclude),
    )


def _project_path(*, tree: DiscoveredTree, scoped_file: ScopedFile) -> str:
    project_root: RepoRoot = tree.repo_root if tree.project_root is None else tree.project_root
    return scoped_file.path.relative_to(project_root.path).as_posix()
