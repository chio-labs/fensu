"""Tests for pure config rendering and initialization decisions."""

from __future__ import annotations

import os
from io import StringIO
from pathlib import Path

import pytest

from strata.config.models import Config
from strata.reporting.classes.cli_style import CliStyle
from strata.scaffolding._helpers.execution import build_rendered_config, render_config
from strata.scaffolding._helpers.output import normalize_project_name
from strata.scaffolding._helpers.planning import (
    build_init_plan,
    count_runtime_python_files,
    interaction_decision,
    validate_option_applicability,
)
from strata.scaffolding.exceptions import InitError
from strata.scaffolding.main.detect_repository_layout import detect_repository_layout
from strata.scaffolding.main.find_local_config import find_local_config
from strata.scaffolding.models import InitOptions, InitPlan
from strata.scaffolding.types import InteractionDecision
from tests.unit.src.strata.scaffolding._test_types import (
    EffectiveCandidateTestCase,
    InteractionDecisionTestCase,
    InvalidNameTestCase,
    LocalConfigCaptureTestCase,
    MissingAnswerTestCase,
    NormalizeNameTestCase,
    OptionApplicabilityTestCase,
    RenderConfigTestCase,
    RuntimeCountTestCase,
)
from tests.unit.src.strata.scaffolding.helpers import (
    RacingDescriptorReader,
    applicability_options,
    build_repository,
    detected_layout,
    detected_nonempty_without_roots,
    init_options,
)


@pytest.mark.parametrize(
    "test_case",
    [
        RenderConfigTestCase(
            description="minimal full config",
            roots=("src/pkg",),
            tests=("tests",),
            tooling=(),
            expected_text='roots = ["src/pkg"]\ntests = ["tests"]\nselect = ["SF"]\n',
            expected_select=("SF",),
        ),
        RenderConfigTestCase(
            description="full config with optional tooling",
            roots=("pkg",),
            tests=("test",),
            tooling=("scripts", "tasks"),
            expected_text='roots = ["pkg"]\ntests = ["test"]\ntooling = ["scripts", "tasks"]\nselect = ["SF"]\n',
            expected_select=("SF",),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_init_plan_when_rendering_then_emits_exact_minimal_roundtrippable_config(
    test_case: RenderConfigTestCase,
) -> None:
    plan: InitPlan = InitPlan(
        roots=test_case.roots,
        tests=test_case.tests,
        tooling=test_case.tooling,
    )

    text: str = render_config(plan=plan)
    config: Config = build_rendered_config(text=text)

    assert text == test_case.expected_text
    assert config.roots == test_case.roots
    assert config.tests == test_case.tests
    assert config.tooling == test_case.tooling
    assert config.select == test_case.expected_select


@pytest.mark.parametrize(
    "test_case",
    [
        InteractionDecisionTestCase(
            description="yes answers every repository non-interactively",
            is_empty=False,
            has_tooling=True,
            yes=True,
            roots=None,
            tests=None,
            tooling=None,
            skills=None,
            name=None,
            expected_decision=InteractionDecision.NON_INTERACTIVE,
        ),
        InteractionDecisionTestCase(
            description="existing repository needs missing layout answer",
            is_empty=False,
            has_tooling=False,
            yes=False,
            roots=("src/pkg",),
            tests=None,
            tooling=(),
            skills=False,
            name=None,
            expected_decision=InteractionDecision.TTY_REQUIRED,
        ),
        InteractionDecisionTestCase(
            description="tooling candidate needs an explicit answer",
            is_empty=False,
            has_tooling=True,
            yes=False,
            roots=("src/pkg",),
            tests=("tests",),
            tooling=None,
            skills=False,
            name=None,
            expected_decision=InteractionDecision.TTY_REQUIRED,
        ),
        InteractionDecisionTestCase(
            description="all existing repository answers avoid terminal",
            is_empty=False,
            has_tooling=True,
            yes=False,
            roots=("src/pkg",),
            tests=("tests",),
            tooling=(),
            skills=False,
            name=None,
            expected_decision=InteractionDecision.NON_INTERACTIVE,
        ),
        InteractionDecisionTestCase(
            description="empty repository needs project name",
            is_empty=True,
            has_tooling=False,
            yes=False,
            roots=None,
            tests=None,
            tooling=None,
            skills=False,
            name=None,
            expected_decision=InteractionDecision.TTY_REQUIRED,
        ),
        InteractionDecisionTestCase(
            description="empty repository explicit name and skills avoid terminal",
            is_empty=True,
            has_tooling=False,
            yes=False,
            roots=None,
            tests=None,
            tooling=None,
            skills=False,
            name="pkg",
            expected_decision=InteractionDecision.NON_INTERACTIVE,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_detected_state_and_answers_when_deciding_interaction_then_returns_expected_decision(
    test_case: InteractionDecisionTestCase,
) -> None:
    options: InitOptions = init_options(test_case=test_case)

    decision: InteractionDecision = interaction_decision(
        options=options,
        detected=detected_layout(is_empty=test_case.is_empty, has_tooling=test_case.has_tooling),
    )

    assert decision is test_case.expected_decision


@pytest.mark.parametrize(
    "test_case",
    [
        NormalizeNameTestCase(
            description="distribution punctuation normalizes to underscores",
            value="  My.Cool-Pkg  ",
            expected_name="my_cool_pkg",
        ),
        NormalizeNameTestCase(
            description="leading digit gains identifier prefix",
            value="2026-app",
            expected_name="_2026_app",
        ),
        NormalizeNameTestCase(
            description="Python keyword gains suffix", value="class", expected_name="class_"
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_valid_project_name_when_normalizing_then_returns_identifier(
    test_case: NormalizeNameTestCase,
) -> None:
    result: str = normalize_project_name(value=test_case.value)

    assert result == test_case.expected_name


@pytest.mark.parametrize(
    "test_case",
    [
        InvalidNameTestCase(
            description="punctuation-only project name is invalid",
            value="---",
            expected_error_type=InitError,
            expected_error_fragment="cannot be normalized",
        ),
        InvalidNameTestCase(
            description="empty project name is invalid",
            value="  ",
            expected_error_type=InitError,
            expected_error_fragment="cannot be normalized",
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_invalid_project_name_when_normalizing_then_raises_init_error(
    test_case: InvalidNameTestCase,
) -> None:
    with pytest.raises(test_case.expected_error_type) as error:
        normalize_project_name(value=test_case.value)

    assert test_case.expected_error_fragment in str(error.value)


@pytest.mark.parametrize(
    "test_case",
    [
        RuntimeCountTestCase(
            description="only Python files under chosen roots are counted",
            files=(
                "src/a/__init__.py",
                "src/a/mod.py",
                "src/b/other.py",
                "tests/test_mod.py",
                "scripts/run.py",
            ),
            roots=("src/a",),
            expected_count=2,
        ),
        RuntimeCountTestCase(
            description="overlapping duplicate file resolution counts once",
            files=("src/a/__init__.py", "src/a/mod.py"),
            roots=("src", "src/a"),
            expected_count=2,
        ),
        RuntimeCountTestCase(
            description="missing chosen root contributes no files",
            files=("app.py",),
            roots=("src/pkg",),
            expected_count=0,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_repository_files_when_counting_runtime_then_uses_only_chosen_roots(
    test_case: RuntimeCountTestCase, tmp_path: Path
) -> None:
    build_repository(root=tmp_path, files=tuple((path, "") for path in test_case.files))

    count: int = count_runtime_python_files(repository=tmp_path, roots=test_case.roots)

    assert count == test_case.expected_count


@pytest.mark.parametrize(
    "test_case",
    [
        MissingAnswerTestCase(
            description="yes mode cannot proceed when loose Python has no detected root",
            expected_error_type=InitError,
            expected_error_fragment="No runtime roots detected",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_nonempty_repository_without_root_when_building_yes_plan_then_reports_missing_answer(
    test_case: MissingAnswerTestCase, tmp_path: Path
) -> None:
    with pytest.raises(test_case.expected_error_type) as error:
        build_init_plan(
            repository=tmp_path,
            detected=detected_nonempty_without_roots(),
            options=InitOptions(yes=True),
            stdin=StringIO(),
            stdout=StringIO(),
            style=CliStyle(use_color=False),
        )

    assert test_case.expected_error_fragment in str(error.value)


@pytest.mark.parametrize(
    "test_case",
    [
        OptionApplicabilityTestCase(
            description="explicit roots do not apply to empty scaffold",
            is_empty=True,
            roots=("src/pkg",),
            tests=None,
            tooling=None,
            name=None,
            expected_error_type=InitError,
            expected_error_fragment="do not apply to an empty scaffold",
        ),
        OptionApplicabilityTestCase(
            description="explicit tests do not apply to empty scaffold",
            is_empty=True,
            roots=None,
            tests=("tests",),
            tooling=None,
            name=None,
            expected_error_type=InitError,
            expected_error_fragment="do not apply to an empty scaffold",
        ),
        OptionApplicabilityTestCase(
            description="explicit tooling does not apply to empty scaffold",
            is_empty=True,
            roots=None,
            tests=None,
            tooling=("scripts",),
            name=None,
            expected_error_type=InitError,
            expected_error_fragment="do not apply to an empty scaffold",
        ),
        OptionApplicabilityTestCase(
            description="project name does not apply when package is detected",
            is_empty=False,
            roots=None,
            tests=None,
            tooling=None,
            name="other",
            expected_error_type=InitError,
            expected_error_fragment="--name only applies when no Python package is detected",
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_state_inapplicable_options_when_validating_then_raises_init_error(
    test_case: OptionApplicabilityTestCase,
) -> None:
    options: InitOptions = applicability_options(test_case=test_case)

    with pytest.raises(test_case.expected_error_type) as error:
        validate_option_applicability(
            options=options,
            detected=detected_layout(is_empty=test_case.is_empty, has_tooling=False),
        )

    assert test_case.expected_error_fragment in str(error.value)


@pytest.mark.parametrize(
    "test_case",
    [
        EffectiveCandidateTestCase(
            description="explicit roots replace only root candidates with command-line provenance",
            explicit_roots=("src/explicit",),
            expected_plan_roots=("src/explicit",),
            expected_transcript_fragments=(
                "src/explicit",
                "command line",
                "tests/",
                "directory scan",
                "scripts/",
            ),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_partial_explicit_scopes_when_building_plan_then_displays_effective_provenance(
    test_case: EffectiveCandidateTestCase, tmp_path: Path
) -> None:
    build_repository(
        root=tmp_path,
        files=(
            ("src/detected/__init__.py", ""),
            ("src/explicit/__init__.py", ""),
            ("scripts/run.py", "value: int = 1\n"),
        ),
        directories=("tests",),
    )
    stdout: StringIO = StringIO()

    plan: InitPlan = build_init_plan(
        repository=tmp_path,
        detected=detect_repository_layout(repository=tmp_path),
        options=InitOptions(yes=True, roots=test_case.explicit_roots),
        stdin=StringIO(),
        stdout=stdout,
        style=CliStyle(use_color=False),
    )
    transcript: str = stdout.getvalue()

    assert plan.roots == test_case.expected_plan_roots
    assert all(fragment in transcript for fragment in test_case.expected_transcript_fragments)


@pytest.mark.parametrize(
    "test_case",
    [
        LocalConfigCaptureTestCase(
            description="captured tool strata survives concurrent pathname replacement",
            initial=b'[tool.strata]\nroots = ["src/pkg"]\n',
            replacement=b'[project]\nname = "user-replacement"\n',
            expected_found=True,
        ),
        LocalConfigCaptureTestCase(
            description="captured plain pyproject ignores concurrent tool strata replacement",
            initial=b'[project]\nname = "original"\n',
            replacement=b'[tool.strata]\nroots = ["src/pkg"]\n',
            expected_found=False,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_racing_pyproject_path_when_finding_local_config_then_parses_captured_descriptor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    test_case: LocalConfigCaptureTestCase,
) -> None:
    path: Path = tmp_path / "pyproject.toml"
    path.write_bytes(test_case.initial)
    reader: RacingDescriptorReader = RacingDescriptorReader(
        path=path, replacement=test_case.replacement, read=os.read
    )
    monkeypatch.setattr(os, "read", reader)

    found: Path | None = find_local_config(repository=tmp_path)

    assert (found is not None) is test_case.expected_found
    assert path.read_bytes() == test_case.replacement
