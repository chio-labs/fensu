"""Build the complete global cache identity or conservatively disable caching."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError
from pathlib import Path

from strata.cache.fingerprints.helpers.fingerprints import (
    config_fingerprint,
    global_fingerprint,
    implementation_fingerprint,
    implementation_identity_is_complete,
    ruleset_fingerprint,
)
from strata.cache.fingerprints.models import GlobalFingerprintBuild
from strata.config.core.models import Config
from strata.rules.authoring.models import RuleSpec


def build_global_fingerprint(
    *,
    config: Config,
    ruleset: tuple[RuleSpec, ...],
) -> GlobalFingerprintBuild:
    """Return a complete installed/editable identity or the reason it is unavailable."""

    package_root: Path | None = _loaded_package_root()
    if package_root is None:
        return GlobalFingerprintBuild(
            fingerprint=None,
            disabled_reason="the loaded implementation location is unavailable",
        )
    try:
        if not (package_root / "__init__.py").is_file() or not implementation_identity_is_complete(
            package_root=package_root
        ):
            return GlobalFingerprintBuild(
                fingerprint=None,
                disabled_reason="the loaded implementation files are unavailable",
            )
        return GlobalFingerprintBuild(
            fingerprint=global_fingerprint(
                implementation=implementation_fingerprint(package_root=package_root),
                config=config_fingerprint(config),
                ruleset=ruleset_fingerprint(ruleset),
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
