"""Load configured custom rules and compose the selected ruleset."""

from __future__ import annotations

import hashlib
import importlib
import importlib.util
import sys
from importlib.machinery import ModuleSpec
from pathlib import Path
from types import ModuleType

from strata.config.core.exceptions import ConfigError
from strata.config.core.models import Config
from strata.rules.authoring.main.inspect import rule_specs_in_module
from strata.rules.authoring.models import RuleSpec
from strata.rules.authoring.types import Family, RuleKind
from strata.rules.catalog.constants import CORE_RULES


def build_ruleset_from_config(config: Config) -> tuple[RuleSpec, ...]:
    """Load custom rules, merge with core rules, and apply select/ignore config."""

    all_rules: tuple[RuleSpec, ...] = build_catalogue_from_config(config)
    return _select_rules(rules=all_rules, select=config.select, ignore=config.ignore)


def build_catalogue_from_config(config: Config) -> tuple[RuleSpec, ...]:
    """Load the complete core and configured custom rule catalogue."""

    custom_rules: tuple[RuleSpec, ...] = (
        *_load_rule_modules(config.rule_modules),
        *_load_rule_paths(config.rule_paths),
    )
    all_rules: tuple[RuleSpec, ...] = (*CORE_RULES, *custom_rules)
    _validate_unique_codes(rules=all_rules)
    return all_rules


def _load_rule_modules(module_names: tuple[str, ...]) -> tuple[RuleSpec, ...]:
    loaded: list[RuleSpec] = []
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
    return tuple(loaded)


def _load_rule_paths(rule_paths: tuple[str, ...]) -> tuple[RuleSpec, ...]:
    loaded: list[RuleSpec] = []
    for rule_path in rule_paths:
        path: Path = Path(rule_path).resolve()
        if path.is_dir():
            for file_path in sorted(path.rglob("*.py")):
                loaded.extend(_load_rule_file(file_path))
        else:
            loaded.extend(_load_rule_file(path))
    return tuple(loaded)


def _load_rule_file(path: Path) -> tuple[RuleSpec, ...]:
    if not path.is_file():
        raise ConfigError(f"Custom rule path does not exist: {path}")
    module_name: str = _synthetic_module_name(path)
    spec: ModuleSpec | None = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ConfigError(f"Could not load custom rule file {path}")
    module: ModuleType = importlib.util.module_from_spec(spec)
    previous_module: ModuleType | None = sys.modules.get(module_name)
    repository_path: str = str(Path.cwd().resolve())
    added_repository_path: bool = repository_path not in sys.path
    if added_repository_path:
        sys.path.insert(0, repository_path)
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
        if added_repository_path:
            sys.path.remove(repository_path)
    return _with_custom_source(rules=rule_specs_in_module(module=module), source=str(path))


def _synthetic_module_name(path: Path) -> str:
    digest: str = hashlib.sha256(str(path).encode("utf-8")).hexdigest()[:16]
    return f"strata._loaded_rules.{digest}"


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
                )
            )
        else:
            result.append(rule)
    return tuple(result)


def _select_rules(
    *, rules: tuple[RuleSpec, ...], select: tuple[str, ...], ignore: tuple[str, ...]
) -> tuple[RuleSpec, ...]:
    selected: list[RuleSpec] = []
    ignore_set: set[str] = set(ignore)
    explicit_code_selects: set[str] = {item for item in select if _is_code_selector(item)}
    for rule in rules:
        if rule.code in ignore_set:
            continue
        if rule.enabled_by_default and _rule_matches_select(rule=rule, select=select):
            selected.append(rule)
            continue
        if rule.code in explicit_code_selects:
            selected.append(rule)
    return tuple(selected)


def _rule_matches_select(*, rule: RuleSpec, select: tuple[str, ...]) -> bool:
    for selector in select:
        if selector == "SF" and rule.code.startswith("SF"):
            return True
        if selector == rule.code:
            return True
        if selector == _family_selector(rule.family):
            return True
    return False


def _family_selector(family: Family) -> str:
    family_selectors: dict[Family, str] = {
        Family.LAYERS: "SFL",
        Family.ROLES: "SFR",
        Family.SHAPE: "SFS",
        Family.NAMING: "SFN",
        Family.HYGIENE: "SFX",
        Family.TESTS: "SFT",
        Family.ANNOTATIONS: "SFA",
        Family.CUSTOM: "X",
    }
    return family_selectors[family]


def _is_code_selector(selector: str) -> bool:
    return (selector.startswith("SF") and len(selector) > 3) or selector.startswith("X")


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
