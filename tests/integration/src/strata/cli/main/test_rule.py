"""Tests for `strata rule` metadata inspection."""

from __future__ import annotations

from pathlib import Path

import pytest

from strata.cli.main.rule import run_rule
from tests.integration.src.strata.cli.main._test_types import (
    MetadataCommandTestCase,
    RulePresentationTestCase,
)
from tests.integration.src.strata.cli.main.helpers import (
    CaptureOutput,
    configure_no_color,
    write_cli_exception_project,
    write_cli_fixture_project,
)


@pytest.mark.parametrize(
    "test_case",
    [
        MetadataCommandTestCase(
            description="configured custom rule renders complete metadata",
            argv=("XCK001",),
            expected_exit_code=0,
            expected_output_fragments=(
                "XCK001 always",
                "Family: custom",
                "Kind: custom",
                "Message: custom fault",
                "Remediation: apply the custom remediation",
                "Source:",
            ),
        ),
        MetadataCommandTestCase(
            description="ignored core rule remains inspectable",
            argv=("SFS131",),
            expected_exit_code=0,
            expected_output_fragments=(
                "SFS131 no-complex-comprehensions",
                "Family: shape",
                "Kind: core",
                "Source: core",
            ),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_known_custom_rule_when_inspecting_then_renders_single_sourced_metadata(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: MetadataCommandTestCase,
) -> None:
    write_cli_fixture_project(root=tmp_path, rule_code="XCK001")
    monkeypatch.chdir(tmp_path)
    stdout: CaptureOutput = CaptureOutput()
    stderr: CaptureOutput = CaptureOutput()

    exit_code: int = run_rule(argv=test_case.argv, stdout=stdout, stderr=stderr)

    assert exit_code == test_case.expected_exit_code
    assert all(fragment in stdout.getvalue() for fragment in test_case.expected_output_fragments)


@pytest.mark.parametrize(
    "test_case",
    [
        MetadataCommandTestCase(
            description="unknown rule returns clear command error",
            argv=("UNKNOWN",),
            expected_exit_code=2,
            expected_output_fragments=("Unknown rule code: UNKNOWN",),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_unknown_rule_when_inspecting_then_returns_clear_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: MetadataCommandTestCase,
) -> None:
    write_cli_fixture_project(root=tmp_path, rule_code="XCK001")
    monkeypatch.chdir(tmp_path)
    stdout: CaptureOutput = CaptureOutput()
    stderr: CaptureOutput = CaptureOutput()

    exit_code: int = run_rule(argv=test_case.argv, stdout=stdout, stderr=stderr)

    assert exit_code == test_case.expected_exit_code
    assert all(fragment in stderr.getvalue() for fragment in test_case.expected_output_fragments)


@pytest.mark.parametrize(
    "test_case",
    [
        MetadataCommandTestCase(
            description="rule inspection shows active exact exceptions and reasons",
            argv=("SFS120",),
            expected_exit_code=0,
            expected_output_fragments=(
                "Active exceptions:",
                "src/pkg/external.py: callback",
                "Reason: The external API invokes this callback positionally.",
            ),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_active_exception_when_inspecting_rule_then_renders_path_symbol_and_reason(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: MetadataCommandTestCase,
) -> None:
    write_cli_exception_project(tmp_path)
    monkeypatch.chdir(tmp_path)
    stdout: CaptureOutput = CaptureOutput()

    exit_code: int = run_rule(argv=test_case.argv, stdout=stdout)

    assert exit_code == test_case.expected_exit_code
    assert all(fragment in stdout.getvalue() for fragment in test_case.expected_output_fragments)


@pytest.mark.parametrize(
    "test_case",
    [
        RulePresentationTestCase(
            description="terminal output uses restrained code and label color",
            argv=("SFR401",),
            is_terminal=True,
            no_color=False,
            expected_output_fragments=(
                "\x1b[1;36mSFR401\x1b[0m entry-module-shape",
                "\x1b[2mFamily:\x1b[0m roles",
                "\x1b[2mRemediation:\x1b[0m",
            ),
            expected_absent_fragments=(),
        ),
        RulePresentationTestCase(
            description="NO_COLOR keeps explicitly requested output plain",
            argv=("SFR401", "--color", "always"),
            is_terminal=True,
            no_color=True,
            expected_output_fragments=("SFR401 entry-module-shape", "Family: roles"),
            expected_absent_fragments=("\x1b[",),
        ),
        RulePresentationTestCase(
            description="long remediation wraps beneath its label",
            argv=("SFR401", "--color", "never"),
            is_terminal=False,
            no_color=False,
            expected_output_fragments=(
                "Remediation: Keep only imports, one public entry function, and at most two "
                "small private glue",
                "             functions; move phase logic to helpers/.",
            ),
            expected_absent_fragments=("\x1b[",),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_terminal_options_when_inspecting_rule_then_styles_and_wraps_metadata(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: RulePresentationTestCase,
) -> None:
    write_cli_fixture_project(root=tmp_path, rule_code="XCK001")
    monkeypatch.chdir(tmp_path)
    configure_no_color(monkeypatch=monkeypatch, enabled=test_case.no_color)
    stdout: CaptureOutput = CaptureOutput(is_terminal=test_case.is_terminal)
    stderr: CaptureOutput = CaptureOutput()

    exit_code: int = run_rule(argv=test_case.argv, stdout=stdout, stderr=stderr)
    output: str = stdout.getvalue()

    assert exit_code == 0
    assert all(fragment in output for fragment in test_case.expected_output_fragments)
    assert all(fragment not in output for fragment in test_case.expected_absent_fragments)
