"""Tests for canonical persistent cache fingerprints."""

from __future__ import annotations

from pathlib import Path

import pytest

from strata.cache.fingerprints.helpers.fingerprints import (
    canonical_fingerprint,
    config_fingerprint,
    global_fingerprint,
    implementation_fingerprint,
    ruleset_fingerprint,
    source_fingerprint,
)
from strata.cache.fingerprints.models import CacheFingerprint
from strata.config.core.models import Config
from strata.rules.authoring.models import RuleSpec
from strata.rules.catalog.main.build_ruleset import build_ruleset
from tests.unit.src.strata.cache.fingerprints._test_types import (
    CanonicalFingerprintTestCase,
    ConfigFingerprintTestCase,
    ConfigLayoutFingerprintTestCase,
    GlobalFingerprintTestCase,
    ImplementationFingerprintTestCase,
    RulesetFingerprintTestCase,
    SourceFingerprintTestCase,
)
from tests.unit.src.strata.cache.fingerprints.helpers import (
    config_with_statement_threshold,
    rule_with_message,
    write_custom_rule,
    write_implementation,
)


@pytest.mark.parametrize(
    "test_case",
    [
        CanonicalFingerprintTestCase(
            description="mapping insertion order does not change canonical identity",
            first={"alpha": 1, "beta": ["x", "y"]},
            second={"beta": ["x", "y"], "alpha": 1},
            expected_equal=True,
        ),
        CanonicalFingerprintTestCase(
            description="sequence order changes canonical identity",
            first={"values": ["x", "y"]},
            second={"values": ["y", "x"]},
            expected_equal=False,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_canonical_values_when_fingerprinting_then_preserves_semantic_order(
    test_case: CanonicalFingerprintTestCase,
) -> None:
    first: CacheFingerprint = canonical_fingerprint(test_case.first)
    second: CacheFingerprint = canonical_fingerprint(test_case.second)

    assert (first == second) is test_case.expected_equal
    assert len(first.value) == 64


@pytest.mark.parametrize(
    "test_case",
    [
        ConfigFingerprintTestCase(
            description="mapping order does not change config identity",
            first_threshold=20,
            second_threshold=20,
            reverse_mapping_order=True,
            expected_equal=True,
        ),
        ConfigFingerprintTestCase(
            description="threshold change invalidates config identity",
            first_threshold=20,
            second_threshold=21,
            reverse_mapping_order=False,
            expected_equal=False,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_validated_configs_when_fingerprinting_then_captures_policy_inputs(
    test_case: ConfigFingerprintTestCase,
) -> None:
    first_config: Config = config_with_statement_threshold(
        value=test_case.first_threshold,
        reverse_mapping_order=False,
    )
    second_config: Config = config_with_statement_threshold(
        value=test_case.second_threshold,
        reverse_mapping_order=test_case.reverse_mapping_order,
    )

    first: CacheFingerprint = config_fingerprint(first_config)
    second: CacheFingerprint = config_fingerprint(second_config)

    assert (first == second) is test_case.expected_equal


@pytest.mark.parametrize(
    "test_case",
    [
        ConfigLayoutFingerprintTestCase(
            description="runtime root change invalidates config identity",
            first_roots=("src/pkg",),
            second_roots=("python/pkg",),
            first_tests=("tests",),
            second_tests=("tests",),
            first_tooling=("scripts",),
            second_tooling=("scripts",),
            expected_equal=False,
        ),
        ConfigLayoutFingerprintTestCase(
            description="test root change invalidates config identity",
            first_roots=("src/pkg",),
            second_roots=("src/pkg",),
            first_tests=("tests",),
            second_tests=("qa",),
            first_tooling=("scripts",),
            second_tooling=("scripts",),
            expected_equal=False,
        ),
        ConfigLayoutFingerprintTestCase(
            description="tooling root change invalidates config identity",
            first_roots=("src/pkg",),
            second_roots=("src/pkg",),
            first_tests=("tests",),
            second_tests=("tests",),
            first_tooling=("scripts",),
            second_tooling=("dev/tools",),
            expected_equal=False,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_configured_layout_when_fingerprinting_then_captures_every_scope(
    test_case: ConfigLayoutFingerprintTestCase,
) -> None:
    first: CacheFingerprint = config_fingerprint(
        Config(
            roots=test_case.first_roots,
            tests=test_case.first_tests,
            tooling=test_case.first_tooling,
        )
    )
    second: CacheFingerprint = config_fingerprint(
        Config(
            roots=test_case.second_roots,
            tests=test_case.second_tests,
            tooling=test_case.second_tooling,
        )
    )

    assert (first == second) is test_case.expected_equal


@pytest.mark.parametrize(
    "test_case",
    [
        SourceFingerprintTestCase(
            description="identical complete bytes have identical source identity",
            first=b"value: int = 1\n",
            second=b"value: int = 1\n",
            expected_equal=True,
        ),
        SourceFingerprintTestCase(
            description="same-length content change invalidates source identity",
            first=b"value: int = 1\n",
            second=b"value: int = 2\n",
            expected_equal=False,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_source_bytes_when_fingerprinting_then_hashes_complete_content(
    test_case: SourceFingerprintTestCase,
) -> None:
    first: CacheFingerprint = source_fingerprint(test_case.first)
    second: CacheFingerprint = source_fingerprint(test_case.second)

    assert (first == second) is test_case.expected_equal


@pytest.mark.parametrize(
    "test_case",
    [
        ImplementationFingerprintTestCase(
            description="implementation source edit changes package identity",
            first="VALUE: int = 1\n",
            second="VALUE: int = 2\n",
            expected_equal=False,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_package_sources_when_fingerprinting_then_captures_editable_changes(
    tmp_path: Path,
    test_case: ImplementationFingerprintTestCase,
) -> None:
    package_root: Path = tmp_path / "strata"
    write_implementation(root=package_root, source=test_case.first)
    first: CacheFingerprint = implementation_fingerprint(package_root=package_root)
    write_implementation(root=package_root, source=test_case.second)
    second: CacheFingerprint = implementation_fingerprint(package_root=package_root)

    assert (first == second) is test_case.expected_equal
    assert not (tmp_path / ".strata").exists()


@pytest.mark.parametrize(
    "test_case",
    [
        RulesetFingerprintTestCase(
            description="rule metadata change invalidates ruleset identity",
            first_message="first message",
            second_message="second message",
            expected_equal=False,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_effective_rulesets_when_fingerprinting_then_captures_rule_metadata(
    test_case: RulesetFingerprintTestCase,
) -> None:
    first_rule: RuleSpec = rule_with_message(test_case.first_message)
    second_rule: RuleSpec = rule_with_message(test_case.second_message)

    first: CacheFingerprint = ruleset_fingerprint((first_rule,))
    second: CacheFingerprint = ruleset_fingerprint((second_rule,))

    assert (first == second) is test_case.expected_equal


@pytest.mark.parametrize(
    "test_case",
    [
        ImplementationFingerprintTestCase(
            description="custom rule implementation edit changes ruleset identity",
            first="no fault",
            second="fault",
            expected_equal=False,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_custom_rule_source_when_fingerprinting_then_captures_implementation_changes(
    tmp_path: Path,
    test_case: ImplementationFingerprintTestCase,
) -> None:
    rule_path: Path = tmp_path / "rules/custom.py"
    config: Config = Config(
        roots=("src/pkg",),
        tests=(),
        rule_paths=("rules/custom.py",),
        select=("XCF001",),
    )
    (tmp_path / "src/pkg").mkdir(parents=True)
    write_custom_rule(path=rule_path, returns_fault=False)
    first: CacheFingerprint = ruleset_fingerprint(build_ruleset(config, repo_root=tmp_path))
    write_custom_rule(path=rule_path, returns_fault=True)
    second: CacheFingerprint = ruleset_fingerprint(build_ruleset(config, repo_root=tmp_path))

    assert (first == second) is test_case.expected_equal


@pytest.mark.parametrize(
    "test_case",
    [
        GlobalFingerprintTestCase(
            description="Strata version change invalidates global identity",
            first_version="1.0.0",
            second_version="1.0.1",
            expected_equal=False,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_global_inputs_when_fingerprinting_then_captures_version_contract(
    test_case: GlobalFingerprintTestCase,
) -> None:
    common: CacheFingerprint = source_fingerprint(b"common")

    first: CacheFingerprint = global_fingerprint(
        implementation=common,
        config=common,
        ruleset=common,
        strata_version=test_case.first_version,
    )
    second: CacheFingerprint = global_fingerprint(
        implementation=common,
        config=common,
        ruleset=common,
        strata_version=test_case.second_version,
    )

    assert (first == second) is test_case.expected_equal
