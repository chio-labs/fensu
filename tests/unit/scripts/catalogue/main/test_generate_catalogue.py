"""Tests for deterministic native catalogue asset generation."""

import json
from importlib import import_module
from pathlib import Path
from types import ModuleType

import pytest

from fensu.analysis.constants import NATIVE_FACT_MODULE_NAME
from fensu.cli._helpers.rule_metadata import serialized_rule_catalogue
from fensu.config.types import AnalyzerId
from fensu.rules.catalog.constants import CORE_RULES, SHIPPED_RULES
from fensu.rules.dagster.constants import FPDG_NATIVE_CODES
from fensu.rules.exemplars.constants import NATIVE_CUSTOM_RULE_EQUIVALENTS
from scripts.catalogue._helpers.rust_policy import serialized_cli_defaults, serialized_native_policy
from scripts.catalogue.constants import CATALOGUE_ASSET_PATH
from scripts.catalogue.main.generate_catalogue import generate_catalogue
from tests.unit.scripts.catalogue.main._test_types import (
    GenerateCatalogueTestCase,
    RuleSurfaceParityTestCase,
)


@pytest.mark.parametrize(
    "test_case",
    [
        GenerateCatalogueTestCase(
            description="check accepts the canonical committed projection",
            arguments=("--check",),
            initial_catalogue=serialized_rule_catalogue(rules=SHIPPED_RULES),
            initial_native_policy=serialized_native_policy(rules=CORE_RULES),
            initial_cli_defaults=serialized_cli_defaults(),
            expected_exit_code=0,
            expected_current=True,
        ),
        GenerateCatalogueTestCase(
            description="check rejects stale catalogue bytes without replacing them",
            arguments=("--check",),
            initial_catalogue=b"[]\n",
            initial_native_policy=serialized_native_policy(rules=CORE_RULES),
            initial_cli_defaults=serialized_cli_defaults(),
            expected_exit_code=1,
            expected_current=False,
        ),
        GenerateCatalogueTestCase(
            description="check rejects stale native policy without replacing it",
            arguments=("--check",),
            initial_catalogue=serialized_rule_catalogue(rules=SHIPPED_RULES),
            initial_native_policy=b"",
            initial_cli_defaults=serialized_cli_defaults(),
            expected_exit_code=1,
            expected_current=False,
        ),
        GenerateCatalogueTestCase(
            description="check rejects stale CLI defaults without replacing them",
            arguments=("--check",),
            initial_catalogue=serialized_rule_catalogue(rules=SHIPPED_RULES),
            initial_native_policy=serialized_native_policy(rules=CORE_RULES),
            initial_cli_defaults=b"",
            expected_exit_code=1,
            expected_current=False,
        ),
        GenerateCatalogueTestCase(
            description="write replaces stale bytes with the canonical projection",
            arguments=("--write",),
            initial_catalogue=b"[]\n",
            initial_native_policy=b"",
            initial_cli_defaults=b"",
            expected_exit_code=0,
            expected_current=True,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_catalogue_asset_when_generating_then_returns_expected_state(
    test_case: GenerateCatalogueTestCase,
    tmp_path: Path,
) -> None:
    catalogue_target: Path = tmp_path / "catalogue.json"
    native_policy_target: Path = tmp_path / "generated_policy.rs"
    cli_defaults_target: Path = tmp_path / "generated_defaults.rs"
    catalogue_target.write_bytes(test_case.initial_catalogue)
    native_policy_target.write_bytes(test_case.initial_native_policy)
    cli_defaults_target.write_bytes(test_case.initial_cli_defaults)

    exit_code: int = generate_catalogue(
        arguments=test_case.arguments,
        catalogue_target=catalogue_target,
        native_policy_target=native_policy_target,
        cli_defaults_target=cli_defaults_target,
    )
    expected_catalogue: bytes = serialized_rule_catalogue(rules=SHIPPED_RULES)
    expected_native_policy: bytes = serialized_native_policy(rules=CORE_RULES)
    expected_cli_defaults: bytes = serialized_cli_defaults()

    assert exit_code == test_case.expected_exit_code
    assert (
        catalogue_target.read_bytes() == expected_catalogue
        and native_policy_target.read_bytes() == expected_native_policy
        and cli_defaults_target.read_bytes() == expected_cli_defaults
    ) is test_case.expected_current


@pytest.mark.parametrize(
    "test_case",
    [
        RuleSurfaceParityTestCase(
            description="all canonical core registries and generated owners agree",
            expected_mismatches=(),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_core_rule_surfaces_when_comparing_registries_then_no_codes_drift(
    test_case: RuleSurfaceParityTestCase,
) -> None:
    native: ModuleType = import_module(NATIVE_FACT_MODULE_NAME)
    core_codes: set[str] = {rule.code for rule in CORE_RULES}
    embedded_rows: list[dict[str, object]] = json.loads(CATALOGUE_ASSET_PATH.read_text())
    embedded_codes: set[str] = set(
        str(row["code"]) for row in filter(lambda row: row.get("pack") is None, embedded_rows)
    )
    python_codes: set[str] = {
        rule.code for rule in filter(lambda item: AnalyzerId.PYTHON in item.analyzers, CORE_RULES)
    }
    native_codes: set[str] = {code for code, _ in native.native_rule_fact_families()}.difference(
        FPDG_NATIVE_CODES
    )
    expected_policy_owners: set[str] = set(
        rule.code
        for rule in filter(
            lambda rule: (
                AnalyzerId.PYTHON in rule.analyzers and bool(rule.constraints or rule.limits)
            ),
            CORE_RULES,
        )
    )
    generated_policy_owners: set[str] = set(native.native_generated_policy_owners())
    exemplar_codes: set[str] = set(NATIVE_CUSTOM_RULE_EQUIVALENTS)
    surfaces: tuple[tuple[str, set[str], set[str]], ...] = (
        ("embedded", core_codes, embedded_codes),
        ("native", python_codes, native_codes),
        ("generated-policy", expected_policy_owners, generated_policy_owners),
        ("exemplar", python_codes, exemplar_codes),
    )
    mismatch_rows: list[str] = []
    for surface, expected, actual in surfaces:
        mismatch_rows.extend(
            f"{surface}:{code}" for code in sorted(expected.symmetric_difference(actual))
        )
    mismatches: tuple[str, ...] = tuple(mismatch_rows)

    assert mismatches == test_case.expected_mismatches
