"""Readable Python harness examples for every native Dagster policy."""

from __future__ import annotations

import pytest

from fensu import RuleCase, RuleFile, RuleResult, evaluate_rule
from fensu.rules.authoring.models import RuleSpec
from fensu.rules.dagster.constants import FPDG_RULES
from tests.unit.src.fensu.rules.dagster._test_types import NativeDagsterRuleTestCase

RULES_BY_CODE: dict[str, RuleSpec] = {rule.code: rule for rule in FPDG_RULES}


@pytest.mark.parametrize(
    "test_case",
    (
        NativeDagsterRuleTestCase(
            description="legacy pipeline asset module faults",
            code="FPDG001",
            source="assets: tuple[object, ...] = ()\n",
            path="pkg/defs/assets/example/pipeline_assets.py",
            expected_fault_count=1,
        ),
        NativeDagsterRuleTestCase(
            description="retained core alias evaluates under its pack identity",
            code="FPDGA001",
            source="def missing(value):\n    return value\n",
            path="pkg/example.py",
            expected_fault_count=1,
        ),
        NativeDagsterRuleTestCase(
            description="private helper in assets module faults",
            code="FPDG002",
            source="import dagster as dg\n\n@dg.asset\ndef example(context):\n    return None\n\ndef _helper():\n    return None\n",
            path="pkg/defs/assets/example/assets.py",
            expected_fault_count=1,
        ),
        NativeDagsterRuleTestCase(
            description="asset callback without direct main delegation faults",
            code="FPDG003",
            source="import dagster as dg\n\n@dg.asset\ndef example(context):\n    return None\n",
            path="pkg/defs/assets/example/assets.py",
            expected_fault_count=2,
        ),
        NativeDagsterRuleTestCase(
            description="asset main with broad return contract faults",
            code="FPDG004",
            source="def main() -> object:\n    return object()\n",
            path="pkg/defs/assets/example/main.py",
            expected_fault_count=1,
            files=(
                RuleFile(
                    path="pkg/defs/assets/example/assets.py",
                    source="assets: tuple[object, ...] = ()\n",
                ),
            ),
        ),
        NativeDagsterRuleTestCase(
            description="asset callback without positional context faults",
            code="FPDG007",
            source="import dagster as dg\n\n@dg.asset\ndef example(resource):\n    return None\n",
            path="pkg/defs/assets/example/assets.py",
            expected_fault_count=1,
        ),
        NativeDagsterRuleTestCase(
            description="cross asset implementation import faults",
            code="FPDG008",
            source="from pkg.defs.assets.other.main import run\n",
            path="pkg/defs/assets/example/main.py",
            expected_fault_count=1,
            files=(
                RuleFile(
                    path="pkg/defs/assets/example/assets.py",
                    source="assets: tuple[object, ...] = ()\n",
                ),
            ),
        ),
        NativeDagsterRuleTestCase(
            description="public undecorated job helper faults",
            code="FPDG009",
            source="def helper() -> None:\n    return None\n",
            path="pkg/defs/jobs/racing/example.py",
            expected_fault_count=1,
        ),
        NativeDagsterRuleTestCase(
            description="generic job main module faults",
            code="FPDG010",
            source="def build() -> None:\n    return None\n",
            path="pkg/defs/jobs/racing/main.py",
            expected_fault_count=1,
        ),
        NativeDagsterRuleTestCase(
            description="private automation support imported outside owner faults",
            code="FPDG011",
            source="from pkg.defs.jobs.racing._models import Plan\n",
            path="pkg/defs/assets/example/main.py",
            expected_fault_count=1,
        ),
        NativeDagsterRuleTestCase(
            description="unsupported operational resource module faults",
            code="FPDG012",
            source="def build() -> None:\n    return None\n",
            path="pkg/defs/resources/database/main.py",
            expected_fault_count=1,
        ),
        NativeDagsterRuleTestCase(
            description="cast definitions provider faults",
            code="FPDG013",
            source="from typing import cast\nimport dagster as dg\n\nvalue = cast(dg.JobDefinition, dg.definitions())\n",
            path="pkg/defs/jobs/racing/example.py",
            expected_fault_count=1,
        ),
        NativeDagsterRuleTestCase(
            description="asset config without config and provider faults",
            code="FPDG014",
            source="VALUE: int = 1\n",
            path="pkg/defs/resources/asset_configs/racing/example.py",
            expected_fault_count=1,
        ),
        NativeDagsterRuleTestCase(
            description="dynamic project import faults once",
            code="FPDG015",
            source="from importlib import import_module\n\nmodule = import_module('pkg.defs.jobs.racing')\n",
            path="pkg/defs/jobs/racing/example.py",
            expected_fault_count=1,
        ),
        NativeDagsterRuleTestCase(
            description="model outside Dagster model role faults",
            code="FPDG016",
            source="from dataclasses import dataclass\n\n@dataclass\nclass Plan:\n    name: str\n",
            path="pkg/defs/assets/example/main.py",
            expected_fault_count=1,
        ),
        NativeDagsterRuleTestCase(
            description="exception outside Dagster exception role faults",
            code="FPDG017",
            source="class DiscoveryError(Exception):\n    pass\n",
            path="pkg/defs/jobs/racing/example.py",
            expected_fault_count=1,
        ),
        NativeDagsterRuleTestCase(
            description="private helper imported outside owner faults",
            code="FPDG018",
            source="from pkg.defs.assets.other._helpers.loading import load\n",
            path="pkg/defs/assets/example/main.py",
            expected_fault_count=1,
        ),
        NativeDagsterRuleTestCase(
            description="public class in private classes role faults",
            code="FPDG019",
            source="class Loader:\n    pass\n",
            path="pkg/defs/resources/database/_classes/loader.py",
            expected_fault_count=1,
        ),
        NativeDagsterRuleTestCase(
            description="unsupported source-root directory faults",
            code="FPDG020",
            source="",
            path="pkg/defs/__init__.py",
            expected_fault_count=1,
            files=(
                RuleFile(
                    path="pkg/services/example.py",
                    source="VALUE: int = 1\n",
                ),
            ),
        ),
        NativeDagsterRuleTestCase(
            description="runtime import from tooling faults",
            code="FPDG021",
            source="from scripts.deploy import run\n",
            path="pkg/defs/assets/example/main.py",
            expected_fault_count=1,
            files=(
                RuleFile(
                    path="scripts/deploy.py",
                    source="def run() -> None:\n    return None\n",
                ),
            ),
        ),
        NativeDagsterRuleTestCase(
            description="nested generic runtime package faults",
            code="FPDG022",
            source="VALUE: int = 1\n",
            path="pkg/defs/assets/example/common/value.py",
            expected_fault_count=1,
        ),
        NativeDagsterRuleTestCase(
            description="unsupported test-root scope faults",
            code="FPDG023",
            source="",
            path="pkg/defs/__init__.py",
            expected_fault_count=1,
            files=(
                RuleFile(
                    path="tests/resources/test_database.py",
                    source="def test_database() -> None:\n    return None\n",
                ),
            ),
        ),
        NativeDagsterRuleTestCase(
            description="module-level subprocess during autoload faults",
            code="FPDG024",
            source="import subprocess\n\nresult = subprocess.run(['discover'])\n",
            path="pkg/defs/jobs/racing/example.py",
            expected_fault_count=1,
        ),
        NativeDagsterRuleTestCase(
            description="exact approved loader encapsulates autoload discovery",
            code="FPDG024",
            source="import dagster as dg\nfrom pkg.defs.resources.example.loader import load_metadata\n\n@dg.definitions\ndef example() -> dg.Definitions:\n    load_metadata()\n    return dg.Definitions()\n",
            path="pkg/defs/resources/example/resource.py",
            expected_fault_count=0,
            files=(
                RuleFile(
                    path="pkg/defs/resources/example/loader.py",
                    source="import paramiko\n\ndef load_metadata() -> None:\n    paramiko.SSHClient()\n",
                ),
            ),
            rule_options={
                "approved_loader_boundaries": ("pkg.defs.resources.example.loader.load_metadata",)
            },
        ),
        NativeDagsterRuleTestCase(
            description="ordinary runtime function is not an autoload root",
            code="FPDG024",
            source="import boto3\n\ndef execute_asset() -> None:\n    boto3.client('s3')\n",
            path="pkg/defs/assets/example/main.py",
            expected_fault_count=0,
        ),
        NativeDagsterRuleTestCase(
            description="type declaration outside Dagster type role faults",
            code="FPDG025",
            source="from enum import Enum\n\nclass State(Enum):\n    READY = 'ready'\n",
            path="pkg/defs/jobs/racing/example.py",
            expected_fault_count=1,
        ),
    ),
    ids=lambda case: case.description,
)
def test_given_dagster_policy_example_when_evaluating_native_rule_then_returns_expected_faults(
    test_case: NativeDagsterRuleTestCase,
) -> None:
    rule: RuleSpec = RULES_BY_CODE[test_case.code]
    result: RuleResult = evaluate_rule(
        rule=rule,
        test_case=RuleCase(
            description=test_case.description,
            source=test_case.source,
            path=test_case.path,
            files=test_case.files,
            expected_fault_count=test_case.expected_fault_count,
        ),
        rule_options=test_case.rule_options,
    )

    assert result.fault_count == test_case.expected_fault_count
