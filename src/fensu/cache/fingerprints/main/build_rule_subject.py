"""Build one hosted custom-rule subject cache identity."""

from __future__ import annotations

import hashlib
import json

from fensu.cache.fingerprints._helpers.fingerprints import (
    config_fingerprint,
    ruleset_fingerprint,
)
from fensu.config.models import Config
from fensu.rules.authoring.models import RuleSpec


def build_rule_subject_fingerprint(
    *,
    config: Config,
    custom_rules_identity: str,
    fact_schema: str,
    parser_contract: str,
    runtime_version: str,
    rule: RuleSpec,
    subject_kind: str,
    subject_identity: str,
) -> str:
    """Return a canonical implementation, option, config, and subject identity."""

    framed: str = json.dumps(
        [
            ruleset_fingerprint((rule,)).value,
            custom_rules_identity,
            fact_schema,
            parser_contract,
            runtime_version,
            config_fingerprint(config).value,
            subject_kind,
            subject_identity,
        ],
        ensure_ascii=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(framed.encode("utf-8")).hexdigest()
