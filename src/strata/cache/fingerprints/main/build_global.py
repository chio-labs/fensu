"""Build the complete global cache identity or conservatively disable caching."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError
from pathlib import Path

from strata.analysis.main.select_fact_backend import select_fact_backend
from strata.analysis.models import FactBackendSelection
from strata.cache.fingerprints._helpers.fingerprints import (
    collect_implementation_paths,
    config_fingerprint,
    custom_rules_fingerprint,
    global_fingerprint,
    implementation_fingerprint,
    ruleset_fingerprint,
)
from strata.cache.fingerprints.models import CacheFingerprint, GlobalFingerprintBuild
from strata.config.models import Config
from strata.rules.authoring.models import RuleSpec
from strata.rules.authoring.types import RuleKind


def build_global_fingerprint(
    *,
    config: Config,
    ruleset: tuple[RuleSpec, ...],
    repo_root: Path,
    warnings_enabled: bool = False,
) -> GlobalFingerprintBuild:
    """Return a complete installed/editable identity or the reason it is unavailable."""

    if ruleset and all(rule.kind is RuleKind.CUSTOM and not rule.cacheable for rule in ruleset):
        return GlobalFingerprintBuild(
            fingerprint=None,
            disabled_reason="no cacheable rules are selected",
        )
    package_root: Path | None = _loaded_package_root()
    if package_root is None:
        return GlobalFingerprintBuild(
            fingerprint=None,
            disabled_reason="the loaded implementation location is unavailable",
        )
    try:
        if not (package_root / "__init__.py").is_file():
            return GlobalFingerprintBuild(
                fingerprint=None,
                disabled_reason="the loaded implementation files are unavailable",
            )
        implementation_paths: tuple[Path, ...] = collect_implementation_paths(
            package_root=package_root
        )
        if not implementation_paths:
            return GlobalFingerprintBuild(
                fingerprint=None,
                disabled_reason="the loaded implementation files are unavailable",
            )
        custom_rules: CacheFingerprint | None = custom_rules_fingerprint(
            config=config,
            repo_root=repo_root,
        )
        if custom_rules is None:
            return GlobalFingerprintBuild(
                fingerprint=None,
                disabled_reason="the custom rule implementation identity is unavailable",
            )
        selection: FactBackendSelection = select_fact_backend()
        return GlobalFingerprintBuild(
            fingerprint=global_fingerprint(
                implementation=implementation_fingerprint(
                    package_root=package_root,
                    paths=implementation_paths,
                ),
                config=config_fingerprint(config),
                ruleset=ruleset_fingerprint(ruleset),
                custom_rules=custom_rules,
                fact_backend=selection.backend.value,
                fact_backend_version=selection.native_version or "",
                warnings_enabled=warnings_enabled,
            )
        )
    except (OSError, PackageNotFoundError, TypeError, ValueError):
        return GlobalFingerprintBuild(
            fingerprint=None,
            disabled_reason="the implementation identity could not be fingerprinted",
        )


def _loaded_package_root() -> Path | None:
    module_file: object = globals().get("__file__")
    if not isinstance(module_file, str):
        return None
    try:
        package_root: Path = Path(module_file).resolve().parents[3]
    except (IndexError, OSError, RuntimeError):
        return None
    return package_root if package_root.is_dir() else None
