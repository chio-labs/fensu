"""Build configured custom-rule source identities."""

from __future__ import annotations

from pathlib import Path

from fensu.cache.fingerprints._helpers.fingerprints import custom_rules_fingerprint
from fensu.cache.fingerprints.models import CacheFingerprint
from fensu.config.models import Config


def build_custom_rules_fingerprint(*, config: Config, repo_root: Path) -> CacheFingerprint | None:
    """Return a complete configured custom-rule source identity when available."""

    return custom_rules_fingerprint(config=config, repo_root=repo_root)
