"""Load configured custom rules and compose the selected ruleset."""

from __future__ import annotations

import ast
import hashlib
import importlib
import importlib.util
import sys
from dataclasses import replace
from importlib.machinery import ModuleSpec
from pathlib import Path
from types import ModuleType

from strata.analysis.models import SourceLocation
from strata.config.exceptions import ConfigError
from strata.config.models import Config
from strata.discovery.constants import INIT_MODULE_FILE_NAME
from strata.rules.authoring.main.inspect import rule_specs_in_module
from strata.rules.authoring.main.is_rule_code import is_rule_code
from strata.rules.authoring.main.matches_rule_selector import matches_rule_selector
from strata.rules.authoring.models import CustomRuleRegistration, RuleSpec
from strata.rules.authoring.types import Family, RuleKind
from strata.rules.catalog._helpers.hermeticity import validate_cacheable_rules
from strata.rules.catalog._helpers.module_use import check_uses_module
from strata.rules.catalog.constants import CORE_RULES
from strata.rules.catalog.models import RuleSelection


def build_ruleset_from_config(
    *, config: Config, repo_root: Path | None = None
) -> tuple[RuleSpec, ...]:
    """Load custom rules, merge with core rules, and apply select/ignore config."""

    selection: RuleSelection = build_rule_selection_from_config(config=config, repo_root=repo_root)
    validate_cacheable_rules(
        rules=selection.blocking,
        allowed_packages=frozenset(name.partition(".")[0] for name in config.rule_modules),
    )
    return selection.blocking


def build_rule_selection_from_config(
    *, config: Config, repo_root: Path | None = None
) -> RuleSelection:
    """Load one catalogue and resolve blocking, warning, and ignored rule sets."""

    catalogue: tuple[RuleSpec, ...] = build_catalogue_from_config(
        config=config, repo_root=repo_root
    )
    ignored: tuple[RuleSpec, ...] = _matching_rules(rules=catalogue, selectors=config.ignore)
    selected: tuple[RuleSpec, ...] = _selected_rules(rules=catalogue, selectors=config.select)
    ignored_codes: frozenset[str] = frozenset(rule.code for rule in ignored)
    blocking: tuple[RuleSpec, ...] = tuple(
        rule for rule in selected if rule.code not in ignored_codes
    )
    warnings: tuple[RuleSpec, ...] = _selected_rules(rules=catalogue, selectors=config.warn)
    _validate_tier_overlaps(blocking=blocking, warnings=warnings, ignored=ignored)
    return RuleSelection(
        catalogue=catalogue,
        blocking=blocking,
        warnings=warnings,
        ignored=ignored,
        custom_registrations=_custom_registrations(
            rules=catalogue,
            config=config,
            repo_root=(Path.cwd() if repo_root is None else repo_root).resolve(),
        ),
    )


def build_catalogue_from_config(
    *, config: Config, repo_root: Path | None = None
) -> tuple[RuleSpec, ...]:
    """Load the complete core and configured custom rule catalogue."""

    repository_root: Path = (Path.cwd() if repo_root is None else repo_root).resolve()
    custom_rules: tuple[RuleSpec, ...] = (
        *_load_rule_modules(module_names=config.rule_modules, repo_root=repository_root),
        *_load_rule_paths(rule_paths=config.rule_paths, repo_root=repository_root),
    )
    if config.cache.require_cacheable:
        custom_rules = tuple(replace(rule, cacheable=True) for rule in custom_rules)
    all_rules: tuple[RuleSpec, ...] = (*CORE_RULES, *custom_rules)
    _validate_rule_identities(rules=all_rules)
    _validate_unique_codes(rules=all_rules)
    _validate_exception_codes(config=config, rules=all_rules)
    return all_rules


def _load_rule_modules(*, module_names: tuple[str, ...], repo_root: Path) -> tuple[RuleSpec, ...]:
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
                    rules=rule_specs_in_module(module=module),
                    source=_repository_module_path(
                        module=module,
                        module_name=module_name,
                        repo_root=repo_root,
                    ).as_posix(),
                )
            )
    finally:
        _remove_repository_import_path(repository_path)
    return tuple(loaded)


def _load_rule_paths(*, rule_paths: tuple[str, ...], repo_root: Path) -> tuple[RuleSpec, ...]:
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
                loaded.extend(_load_rule_file(path=file_path, repo_root=repo_root))
        else:
            loaded.extend(_load_rule_file(path=path, repo_root=repo_root))
    return tuple(loaded)


def _load_rule_file(*, path: Path, repo_root: Path) -> tuple[RuleSpec, ...]:
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
    return _with_custom_source(rules=rule_specs_in_module(module=module), source=path.as_posix())


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
            or _module_is_within(module=module, root=repo_root)
        ):
            continue
        displaced[name] = module
        _ = sys.modules.pop(name, None)
    return displaced


def _remove_loaded_repository_modules(*, repo_root: Path, previous_names: set[str]) -> None:
    for name in set(sys.modules) - previous_names:
        if _module_is_within(module=sys.modules.get(name), root=repo_root):
            _ = sys.modules.pop(name, None)


def _module_is_within(*, module: ModuleType | None, root: Path) -> bool:
    module_file: object = getattr(module, "__file__", None)
    if not isinstance(module_file, str):
        return False
    return Path(module_file).resolve().is_relative_to(root)


def _with_custom_source(*, rules: tuple[RuleSpec, ...], source: str) -> tuple[RuleSpec, ...]:
    result: list[RuleSpec] = []
    for rule in rules:
        if not is_rule_code(rule.code):
            raise ConfigError(
                f"Custom rule {rule.code} from {source} must use one exact X* rule code."
            )
        if not rule.code.startswith("X") or rule.kind is not RuleKind.CUSTOM:
            raise ConfigError(f"Custom rule {rule.code} from {source} must use the X* namespace.")
        result.append(
            replace(
                rule,
                source=source if rule.source is None else rule.source,
                uses_module=check_uses_module(check=rule.check),
            )
        )
    return tuple(result)


def _repository_module_path(*, module: ModuleType, module_name: str, repo_root: Path) -> Path:
    module_file: object = getattr(module, "__file__", None)
    if not isinstance(module_file, str):
        raise ConfigError(
            f"Custom rule module {module_name} has no repository-owned Python source. "
            "Move the rule into this repository and configure that module or a rule_path."
        )
    path: Path = Path(module_file).resolve()
    if not path.is_file() or not path.is_relative_to(repo_root):
        raise ConfigError(
            f"Custom rule module {module_name} resolves outside the repository at {path}. "
            "Move the rule into this repository and configure that module or a rule_path so "
            "SFR707 diagnostics and cache entries can be owned by its source."
        )
    return path


def _custom_registrations(
    *, rules: tuple[RuleSpec, ...], config: Config, repo_root: Path
) -> tuple[CustomRuleRegistration, ...]:
    registrations: list[CustomRuleRegistration] = []
    for rule in rules:
        if rule.kind is not RuleKind.CUSTOM or rule.source is None:
            continue
        source_path: Path = Path(rule.source).resolve()
        if not source_path.is_file() or not source_path.is_relative_to(repo_root):
            raise ConfigError(
                f"Custom rule {rule.code} source {source_path} is not a repository-owned file; "
                "SFR707 requires repository-owned rule sources for diagnostic and cache identity."
            )
        module_name: str = _configured_module_name(
            rule=rule, source_path=source_path, config=config, repo_root=repo_root
        )
        function_value: object = getattr(rule.check, "__name__", None)
        if not isinstance(function_value, str):
            raise ConfigError(f"Could not resolve custom rule function name for {rule.code}.")
        function_name: str = function_value
        declaration: SourceLocation = _declaration_location(
            path=source_path, function_name=function_name
        )
        registrations.append(
            CustomRuleRegistration(
                rule=rule,
                source_path=source_path,
                module_name=module_name,
                function_name=function_name,
                declaration_line=declaration.line,
                declaration_column=declaration.column,
                owner_key=source_path.relative_to(repo_root).as_posix(),
            )
        )
    return tuple(
        sorted(
            registrations,
            key=lambda item: (item.owner_key, item.declaration_line, item.rule.code),
        )
    )


def _configured_module_name(
    *, rule: RuleSpec, source_path: Path, config: Config, repo_root: Path
) -> str:
    if not rule.check.__module__.startswith("strata._loaded_rules."):
        return rule.check.__module__
    configured_roots: tuple[str, ...] = (*config.roots, *config.tests, *config.tooling)
    owners: list[Path] = []
    for value in configured_roots:
        root: Path = (repo_root / value).resolve()
        if source_path.is_relative_to(root):
            owners.append(root)
    relative: Path = (
        source_path.relative_to(max(owners, key=lambda path: len(path.parts)).parent)
        if owners
        else source_path.relative_to(repo_root)
    )
    parts: tuple[str, ...] = relative.with_suffix("").parts
    if parts and parts[-1] == Path(INIT_MODULE_FILE_NAME).stem:
        parts = parts[:-1]
    return ".".join(parts)


def _declaration_location(*, path: Path, function_name: str) -> SourceLocation:
    try:
        module: ast.Module = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, SyntaxError, UnicodeError) as error:
        raise ConfigError(
            f"Could not resolve custom rule declaration in {path}: {error}"
        ) from error
    matches: tuple[ast.FunctionDef | ast.AsyncFunctionDef, ...] = tuple(
        statement
        for statement in module.body
        if isinstance(statement, ast.FunctionDef | ast.AsyncFunctionDef)
        and statement.name == function_name
    )
    if len(matches) != 1:
        raise ConfigError(
            f"Could not resolve one declaration for custom rule function {function_name} in {path}."
        )
    node: ast.FunctionDef | ast.AsyncFunctionDef = matches[0]
    return SourceLocation(path=path, line=node.lineno, column=node.col_offset)


def _selected_rules(
    *, rules: tuple[RuleSpec, ...], selectors: tuple[str, ...]
) -> tuple[RuleSpec, ...]:
    selected: list[RuleSpec] = []
    explicit_code_selects: set[str] = {item for item in selectors if is_rule_code(item)}
    for rule in rules:
        if rule.enabled_by_default and _rule_matches_select(rule=rule, select=selectors):
            selected.append(rule)
            continue
        if rule.code in explicit_code_selects:
            selected.append(rule)
    return tuple(selected)


def _matching_rules(
    *, rules: tuple[RuleSpec, ...], selectors: tuple[str, ...]
) -> tuple[RuleSpec, ...]:
    return tuple(rule for rule in rules if _rule_matches_select(rule=rule, select=selectors))


def _validate_tier_overlaps(
    *,
    blocking: tuple[RuleSpec, ...],
    warnings: tuple[RuleSpec, ...],
    ignored: tuple[RuleSpec, ...],
) -> None:
    blocking_codes: frozenset[str] = frozenset(rule.code for rule in blocking)
    warning_codes: frozenset[str] = frozenset(rule.code for rule in warnings)
    ignored_codes: frozenset[str] = frozenset(rule.code for rule in ignored)
    blocking_warning_overlap: list[str] = sorted(blocking_codes & warning_codes)
    if blocking_warning_overlap:
        raise ConfigError(
            f"Rule {blocking_warning_overlap[0]} cannot be configured as both blocking and warning."
        )
    warning_ignore_overlap: list[str] = sorted(warning_codes & ignored_codes)
    if warning_ignore_overlap:
        raise ConfigError(
            f"Rule {warning_ignore_overlap[0]} cannot be configured as both warning and ignored."
        )


def _rule_matches_select(*, rule: RuleSpec, select: tuple[str, ...]) -> bool:
    return any(matches_rule_selector(code=rule.code, selector=selector) for selector in select)


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


def _validate_rule_identities(*, rules: tuple[RuleSpec, ...]) -> None:
    for rule in rules:
        if not is_rule_code(rule.code):
            raise ConfigError(f"Catalogue rule {rule.code} must use one exact rule code.")
        if not isinstance(rule.family, Family):
            raise ConfigError(f"Catalogue rule {rule.code} must use one valid Family member.")
        expected_kind: RuleKind = RuleKind.CORE if rule.code.startswith("SF") else RuleKind.CUSTOM
        if rule.kind is not expected_kind:
            raise ConfigError(f"Catalogue rule {rule.code} must use kind {expected_kind.value}.")


def _validate_exception_codes(*, config: Config, rules: tuple[RuleSpec, ...]) -> None:
    known_codes: frozenset[str] = frozenset(rule.code for rule in rules)
    for exception in config.rule_exceptions:
        if exception.rule not in known_codes:
            raise ConfigError(f"Unknown rule exception code: {exception.rule}.")
