"""Load configured custom rules and compose the selected ruleset."""

from __future__ import annotations

import hashlib
import importlib
import importlib.util
import sys
from dataclasses import replace
from importlib.machinery import ModuleSpec
from pathlib import Path
from types import ModuleType

from strata.config.core.exceptions import ConfigError
from strata.config.core.models import Config
from strata.config.core.types import RuleSelector
from strata.rules.authoring.main.inspect import rule_specs_in_module
from strata.rules.authoring.models import RuleSpec
from strata.rules.authoring.types import Family, RuleKind
from strata.rules.catalog.constants import CORE_RULES
from strata.rules.catalog.helpers.hermeticity import validate_cacheable_rules

_minimum_core_rule_code_length: int = 3


def build_ruleset_from_config(
    config: Config, *, repo_root: Path | None = None
) -> tuple[RuleSpec, ...]:
    """Load custom rules, merge with core rules, and apply select/ignore config."""

    all_rules: tuple[RuleSpec, ...] = build_catalogue_from_config(config, repo_root=repo_root)
    selected: tuple[RuleSpec, ...] = _select_rules(
        rules=all_rules,
        select=config.select,
        ignore=config.ignore,
    )
    validate_cacheable_rules(
        rules=selected,
        allowed_packages=frozenset(name.partition(".")[0] for name in config.rule_modules),
    )
    return selected


def build_catalogue_from_config(
    config: Config, *, repo_root: Path | None = None
) -> tuple[RuleSpec, ...]:
    """Load the complete core and configured custom rule catalogue."""

    repository_root: Path = (Path.cwd() if repo_root is None else repo_root).resolve()
    custom_rules: tuple[RuleSpec, ...] = (
        *_load_rule_modules(config.rule_modules, repo_root=repository_root),
        *_load_rule_paths(config.rule_paths, repo_root=repository_root),
    )
    if config.cache.require_cacheable:
        custom_rules = tuple(replace(rule, cacheable=True) for rule in custom_rules)
    all_rules: tuple[RuleSpec, ...] = (*CORE_RULES, *custom_rules)
    _validate_unique_codes(rules=all_rules)
    _validate_exception_codes(config=config, rules=all_rules)
    return all_rules


def _load_rule_modules(module_names: tuple[str, ...], *, repo_root: Path) -> tuple[RuleSpec, ...]:
    loaded: list[RuleSpec] = []
    repository_path: str = _add_repository_import_path(repo_root)
    try:
        for module_name in module_names:
            try:
                module: ModuleType = importlib.import_module(module_name)
            except Exception as error:
                raise ConfigError(
                    f"Could not import custom rule module {module_name}: {error}"
                ) from error
            loaded.extend(
                _with_custom_source(
                    rules=rule_specs_in_module(module=module), source=f"module:{module_name}"
                )
            )
    finally:
        _remove_repository_import_path(repository_path)
    return tuple(loaded)


def _load_rule_paths(rule_paths: tuple[str, ...], *, repo_root: Path) -> tuple[RuleSpec, ...]:
    loaded: list[RuleSpec] = []
    for rule_path in rule_paths:
        configured_path: Path = Path(rule_path)
        path: Path = (
            configured_path.resolve()
            if configured_path.is_absolute()
            else (repo_root / configured_path).resolve()
        )
        if path.is_dir():
            for file_path in sorted(path.rglob("*.py")):
                loaded.extend(_load_rule_file(file_path, repo_root=repo_root))
        else:
            loaded.extend(_load_rule_file(path, repo_root=repo_root))
    return tuple(loaded)


def _load_rule_file(path: Path, *, repo_root: Path) -> tuple[RuleSpec, ...]:
    if not path.is_file():
        raise ConfigError(f"Custom rule path does not exist: {path}")
    module_name: str = _synthetic_module_name(path)
    spec: ModuleSpec | None = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ConfigError(f"Could not load custom rule file {path}")
    module: ModuleType = importlib.util.module_from_spec(spec)
    previous_module: ModuleType | None = sys.modules.get(module_name)
    repository_path: str = _add_repository_import_path(repo_root)
    previous_names: set[str] = set(sys.modules)
    displaced_modules: dict[str, ModuleType] = _displace_conflicting_modules(repo_root)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as error:
        raise ConfigError(f"Could not import custom rule file {path}: {error}") from error
    finally:
        if previous_module is None:
            _ = sys.modules.pop(module_name, None)
        else:
            sys.modules[module_name] = previous_module
        _remove_loaded_repository_modules(
            repo_root=repo_root,
            previous_names=previous_names,
        )
        sys.modules.update(displaced_modules)
        _remove_repository_import_path(repository_path)
    return _with_custom_source(rules=rule_specs_in_module(module=module), source=str(path))


def _synthetic_module_name(path: Path) -> str:
    digest: str = hashlib.sha256(str(path).encode("utf-8")).hexdigest()[:16]
    return f"strata._loaded_rules.{digest}"


def _add_repository_import_path(repo_root: Path) -> str:
    repository_path: str = str(repo_root)
    if repository_path not in sys.path:
        sys.path.insert(0, repository_path)
        return repository_path
    return ""


def _remove_repository_import_path(repository_path: str) -> None:
    if repository_path:
        sys.path.remove(repository_path)


def _displace_conflicting_modules(repo_root: Path) -> dict[str, ModuleType]:
    package_names: frozenset[str] = frozenset(
        path.name for path in repo_root.iterdir() if (path / "__init__.py").is_file()
    )
    displaced: dict[str, ModuleType] = {}
    for name, module in tuple(sys.modules.items()):
        if (
            module is None
            or name.partition(".")[0] not in package_names
            or _module_is_within(module, root=repo_root)
        ):
            continue
        displaced[name] = module
        _ = sys.modules.pop(name, None)
    return displaced


def _remove_loaded_repository_modules(*, repo_root: Path, previous_names: set[str]) -> None:
    for name in set(sys.modules) - previous_names:
        if _module_is_within(sys.modules.get(name), root=repo_root):
            _ = sys.modules.pop(name, None)


def _module_is_within(module: ModuleType | None, *, root: Path) -> bool:
    module_file: object = getattr(module, "__file__", None)
    if not isinstance(module_file, str):
        return False
    return Path(module_file).resolve().is_relative_to(root)


def _with_custom_source(*, rules: tuple[RuleSpec, ...], source: str) -> tuple[RuleSpec, ...]:
    result: list[RuleSpec] = []
    for rule in rules:
        if rule.code.startswith("SF"):
            raise ConfigError(f"Custom rule {rule.code} from {source} must use the X* namespace.")
        if rule.kind is RuleKind.CUSTOM and rule.source is None:
            result.append(
                RuleSpec(
                    code=rule.code,
                    family=rule.family,
                    slug=rule.slug,
                    message=rule.message,
                    check=rule.check,
                    remediation=rule.remediation,
                    severity=rule.severity,
                    kind=rule.kind,
                    source=source,
                    enabled_by_default=rule.enabled_by_default,
                    cacheable=rule.cacheable,
                )
            )
        else:
            result.append(rule)
    return tuple(result)


def _select_rules(
    *, rules: tuple[RuleSpec, ...], select: tuple[str, ...], ignore: tuple[str, ...]
) -> tuple[RuleSpec, ...]:
    selected: list[RuleSpec] = []
    explicit_code_selects: set[str] = {item for item in select if _is_code_selector(item)}
    for rule in rules:
        if _rule_matches_select(rule=rule, select=ignore):
            continue
        if rule.enabled_by_default and _rule_matches_select(rule=rule, select=select):
            selected.append(rule)
            continue
        if rule.code in explicit_code_selects:
            selected.append(rule)
    return tuple(selected)


def _rule_matches_select(*, rule: RuleSpec, select: tuple[str, ...]) -> bool:
    for selector in select:
        if selector == RuleSelector.ALL and rule.code.startswith(RuleSelector.ALL):
            return True
        if selector == rule.code:
            return True
        if selector == _family_selector(rule.family):
            return True
    return False


def _family_selector(family: Family) -> RuleSelector:
    family_selectors: dict[Family, RuleSelector] = {
        Family.LAYERS: RuleSelector.LAYERS,
        Family.ROLES: RuleSelector.ROLES,
        Family.SHAPE: RuleSelector.SHAPE,
        Family.NAMING: RuleSelector.NAMING,
        Family.HYGIENE: RuleSelector.HYGIENE,
        Family.TESTS: RuleSelector.TESTS,
        Family.ANNOTATIONS: RuleSelector.ANNOTATIONS,
        Family.CUSTOM: RuleSelector.CUSTOM,
    }
    return family_selectors[family]


def _is_code_selector(selector: str) -> bool:
    return (
        selector.startswith(RuleSelector.ALL) and len(selector) > _minimum_core_rule_code_length
    ) or selector.startswith(RuleSelector.CUSTOM)


def _validate_unique_codes(*, rules: tuple[RuleSpec, ...]) -> None:
    rules_by_code: dict[str, RuleSpec] = {}
    for rule in rules:
        previous: RuleSpec | None = rules_by_code.get(rule.code)
        if previous is not None:
            previous_source: str = previous.source or "core"
            current_source: str = rule.source or "core"
            raise ConfigError(
                f"Duplicate rule code {rule.code}: {previous_source} and {current_source}"
            )
        rules_by_code[rule.code] = rule


def _validate_exception_codes(*, config: Config, rules: tuple[RuleSpec, ...]) -> None:
    known_codes: frozenset[str] = frozenset(rule.code for rule in rules)
    for exception in config.rule_exceptions:
        if exception.rule not in known_codes:
            raise ConfigError(f"Unknown rule exception code: {exception.rule}.")
