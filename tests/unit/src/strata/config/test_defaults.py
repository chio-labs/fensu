"""Tests for config defaults and normalization."""

from __future__ import annotations

from pathlib import Path

import pytest

from strata.config.main.load_config import load_config
from strata.config.main.resolve_threshold import resolve_threshold
from strata.config.models import (
    Config,
    RuleExceptionEntry,
    ThresholdOverride,
    ThresholdResolution,
)
from strata.rules.authoring.types import Threshold
from tests.unit.src.strata.config._test_types import (
    CacheConfigTestCase,
    ConfigContractTestCase,
    ConfigDefaultsTestCase,
    ConfigListFieldTestCase,
    ConfigThresholdTestCase,
    EvaluationConfigTestCase,
    MemoryConfigTestCase,
    RuleExceptionConfigTestCase,
    SkillsConfigTestCase,
    ThresholdOverrideConfigTestCase,
    ThresholdResolutionTestCase,
)
from tests.unit.src.strata.config.helpers import write_strata_toml


@pytest.mark.parametrize(
    "test_case",
    [
        MemoryConfigTestCase(
            description="omitted experimental table disables memory with retention defaults",
            config_text='roots = ["src/pkg"]\n',
            expected_enabled=False,
            expected_archive_after_days=7,
        ),
        MemoryConfigTestCase(
            description="experimental gate enables memory and settings override task retention",
            config_text=(
                'roots = ["src/pkg"]\n[experimental]\nmemory = true\n'
                "[memory.tasks]\narchive_after_days = 30\n"
            ),
            expected_enabled=True,
            expected_archive_after_days=30,
        ),
        MemoryConfigTestCase(
            description="zero archive age disables automatic task age eligibility",
            config_text=('roots = ["src/pkg"]\n[memory.tasks]\narchive_after_days = 0\n'),
            expected_enabled=False,
            expected_archive_after_days=0,
        ),
        MemoryConfigTestCase(
            description="archive age has no arbitrary upper bound",
            config_text=(
                'roots = ["src/pkg"]\n[memory.tasks]\narchive_after_days = 9223372036854775807\n'
            ),
            expected_enabled=False,
            expected_archive_after_days=9223372036854775807,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_memory_preferences_when_loading_then_applies_nested_defaults_and_overrides(
    tmp_path: Path, test_case: MemoryConfigTestCase
) -> None:
    write_strata_toml(root=tmp_path, contents=test_case.config_text)

    config: Config = load_config(tmp_path)

    assert config.experimental.memory is test_case.expected_enabled
    assert config.memory.tasks.archive_after_days == test_case.expected_archive_after_days


@pytest.mark.parametrize(
    "test_case",
    [
        SkillsConfigTestCase(
            description="omitted skills table leaves identity discovery enabled",
            config_text='roots = ["src/pkg"]\n',
            expected_name=None,
        ),
        SkillsConfigTestCase(
            description="configured skill name is persisted without early normalization",
            config_text='roots = ["src/pkg"]\n[skills]\nname = "RaceHealth API"\n',
            expected_name="RaceHealth API",
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_skills_identity_when_loading_then_preserves_persistent_name(
    tmp_path: Path, test_case: SkillsConfigTestCase
) -> None:
    write_strata_toml(root=tmp_path, contents=test_case.config_text)

    config: Config = load_config(tmp_path)

    assert config.skills.name == test_case.expected_name


@pytest.mark.parametrize(
    "test_case",
    [
        EvaluationConfigTestCase(
            description="omitted evaluation table selects all paths by default",
            config_text='roots = ["src/pkg"]\n',
            expected_include=(),
            expected_exclude=(),
        ),
        EvaluationConfigTestCase(
            description="include-only evaluation table preserves patterns",
            config_text='roots = ["src/pkg"]\n[evaluation]\ninclude = ["src/pkg/**"]\n',
            expected_include=("src/pkg/**",),
            expected_exclude=(),
        ),
        EvaluationConfigTestCase(
            description="exclude-only evaluation table preserves patterns",
            config_text='roots = ["src/pkg"]\n[evaluation]\nexclude = ["**/generated/**"]\n',
            expected_include=(),
            expected_exclude=("**/generated/**",),
        ),
        EvaluationConfigTestCase(
            description="combined evaluation table preserves both pattern lists",
            config_text=(
                'roots = ["src/pkg"]\n[evaluation]\ninclude = ["src/**", "tests/**"]\n'
                'exclude = ["**/legacy/**"]\n'
            ),
            expected_include=("src/**", "tests/**"),
            expected_exclude=("**/legacy/**",),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_evaluation_paths_when_loading_then_applies_optional_semantics(
    tmp_path: Path, test_case: EvaluationConfigTestCase
) -> None:
    write_strata_toml(root=tmp_path, contents=test_case.config_text)

    config: Config = load_config(tmp_path)

    assert config.evaluation.include == test_case.expected_include
    assert config.evaluation.exclude == test_case.expected_exclude


@pytest.mark.parametrize(
    "test_case",
    [
        CacheConfigTestCase(
            description="cache is enabled by the shipped default",
            config_text='roots = ["src/pkg"]\n',
            expected_enabled=True,
        ),
        CacheConfigTestCase(
            description="cache table disables persistent evaluation",
            config_text='roots = ["src/pkg"]\n[cache]\nenabled = false\n',
            expected_enabled=False,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_cache_preference_when_loading_then_applies_default_or_override(
    tmp_path: Path,
    test_case: CacheConfigTestCase,
) -> None:
    write_strata_toml(root=tmp_path, contents=test_case.config_text)

    config: Config = load_config(tmp_path)

    assert config.cache.enabled is test_case.expected_enabled


@pytest.mark.parametrize(
    "test_case",
    [
        RuleExceptionConfigTestCase(
            description="symbol scoped rule exception is normalized",
            config_text=(
                'roots = ["src/pkg"]\n'
                "[[rule_exceptions]]\n"
                'rule = "SFS120"\n'
                'path = "src/pkg/progress.py"\n'
                'symbols = ["Collector.update", "outer.nested"]\n'
                'reason = "External callbacks invoke these positionally."\n'
            ),
            expected_rule="SFS120",
            expected_path="src/pkg/progress.py",
            expected_symbols=("Collector.update", "outer.nested"),
            expected_reason="External callbacks invoke these positionally.",
        ),
        RuleExceptionConfigTestCase(
            description="file level rule exception omits symbols",
            config_text=(
                'roots = ["src/pkg"]\n'
                "[[rule_exceptions]]\n"
                'rule = "SFR307"\n'
                'path = "src/pkg/special.py"\n'
                'reason = "The file is an intentional adapter."\n'
            ),
            expected_rule="SFR307",
            expected_path="src/pkg/special.py",
            expected_symbols=(),
            expected_reason="The file is an intentional adapter.",
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_rule_exception_when_loading_then_normalizes_exact_fields(
    tmp_path: Path,
    test_case: RuleExceptionConfigTestCase,
) -> None:
    write_strata_toml(root=tmp_path, contents=test_case.config_text)

    config: Config = load_config(tmp_path)
    exception: RuleExceptionEntry = config.rule_exceptions[0]

    assert exception.rule == test_case.expected_rule
    assert exception.path == test_case.expected_path
    assert exception.symbols == test_case.expected_symbols
    assert exception.reason == test_case.expected_reason


@pytest.mark.parametrize(
    "test_case",
    [
        ConfigDefaultsTestCase(
            description="no optional fields applies shipped defaults",
            config_text='roots = ["src/pkg"]\n',
            expected_roots=("src/pkg",),
            expected_tests=("tests",),
            expected_tooling=(),
            expected_threshold_name="max_statements",
            expected_threshold_value=40,
            expected_role_name=None,
            expected_role_threshold_name=None,
            expected_role_threshold_value=None,
        ),
        ConfigDefaultsTestCase(
            description="multiple independent roots are kept",
            config_text='roots = ["src/pkg_a", "src/pkg_b"]\ntests = ["test_suite"]\n',
            expected_roots=("src/pkg_a", "src/pkg_b"),
            expected_tests=("test_suite",),
            expected_tooling=(),
            expected_threshold_name="max_file_lines",
            expected_threshold_value=2000,
            expected_role_name=None,
            expected_role_threshold_name=None,
            expected_role_threshold_value=None,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_valid_config_when_loading_then_applies_defaults(
    tmp_path: Path,
    test_case: ConfigDefaultsTestCase,
) -> None:
    write_strata_toml(root=tmp_path, contents=test_case.config_text)

    config: Config = load_config(tmp_path)
    threshold: Threshold = Threshold(test_case.expected_threshold_name)

    assert config.roots == test_case.expected_roots
    assert config.tests == test_case.expected_tests
    assert config.tooling == test_case.expected_tooling
    assert config.thresholds[threshold] == test_case.expected_threshold_value


@pytest.mark.parametrize(
    "test_case",
    [
        ConfigListFieldTestCase(
            description="tests override is normalized",
            config_text='roots = ["src/pkg"]\ntests = ["test_suite"]\n',
            expected_field_name="tests",
            expected_value=("test_suite",),
        ),
        ConfigListFieldTestCase(
            description="tooling override is normalized",
            config_text='roots = ["src/pkg"]\ntooling = ["scripts", "tools"]\n',
            expected_field_name="tooling",
            expected_value=("scripts", "tools"),
        ),
        ConfigListFieldTestCase(
            description="select override is normalized",
            config_text='roots = ["src/pkg"]\nselect = ["SFL", "XWH001"]\n',
            expected_field_name="select",
            expected_value=("SFL", "XWH001"),
        ),
        ConfigListFieldTestCase(
            description="custom family selector is accepted",
            config_text='roots = ["src/pkg"]\nselect = ["X"]\n',
            expected_field_name="select",
            expected_value=("X",),
        ),
        ConfigListFieldTestCase(
            description="ignore override is normalized",
            config_text='roots = ["src/pkg"]\nignore = ["SFH002"]\n',
            expected_field_name="ignore",
            expected_value=("SFH002",),
        ),
        ConfigListFieldTestCase(
            description="rule paths override is normalized",
            config_text='roots = ["src/pkg"]\nrule_paths = ["scripts/strata/rules"]\n',
            expected_field_name="rule_paths",
            expected_value=("scripts/strata/rules",),
        ),
        ConfigListFieldTestCase(
            description="rule modules override is normalized",
            config_text=(
                'roots = ["src/pkg"]\nrule_modules = ["scripts.strata.rules.client_ownership"]\n'
            ),
            expected_field_name="rule_modules",
            expected_value=("scripts.strata.rules.client_ownership",),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_list_field_overrides_when_loading_then_normalizes_to_tuple(
    tmp_path: Path,
    test_case: ConfigListFieldTestCase,
) -> None:
    write_strata_toml(root=tmp_path, contents=test_case.config_text)

    config: Config = load_config(tmp_path)

    assert getattr(config, test_case.expected_field_name) == test_case.expected_value


@pytest.mark.parametrize(
    "test_case",
    [
        ConfigThresholdTestCase(
            description="all threshold enum members are present by default",
            config_text='roots = ["src/pkg"]\n',
            expected_threshold_name="max_arguments",
            expected_threshold_value=10,
        ),
        ConfigThresholdTestCase(
            description="global threshold override is applied",
            config_text='roots = ["src/pkg"]\n[thresholds]\nmax_statements = 50\n',
            expected_threshold_name="max_statements",
            expected_threshold_value=50,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_threshold_config_when_loading_then_thresholds_are_complete_and_overridden(
    tmp_path: Path,
    test_case: ConfigThresholdTestCase,
) -> None:
    write_strata_toml(root=tmp_path, contents=test_case.config_text)

    config: Config = load_config(tmp_path)
    threshold: Threshold = Threshold(test_case.expected_threshold_name)

    assert set(config.thresholds) == set(Threshold)
    assert config.thresholds[threshold] == test_case.expected_threshold_value


@pytest.mark.parametrize(
    "test_case",
    [
        ThresholdOverrideConfigTestCase(
            description="threshold override is normalized as immutable ordered data",
            config_text=(
                'roots = ["src/pkg"]\n'
                "[[threshold_overrides]]\n"
                'paths = ["src/pkg/**/main/commands/*.py"]\n'
                'reason = "Product-width command surface."\n'
                "thresholds = { max_main_container_modules = 36 }\n"
            ),
            expected_paths=("src/pkg/**/main/commands/*.py",),
            expected_threshold_name="max_main_container_modules",
            expected_threshold_value=36,
            expected_reason="Product-width command surface.",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_threshold_override_when_loading_then_preserves_immutable_fields(
    tmp_path: Path, test_case: ThresholdOverrideConfigTestCase
) -> None:
    write_strata_toml(root=tmp_path, contents=test_case.config_text)

    config: Config = load_config(tmp_path)
    override: ThresholdOverride = config.threshold_overrides[0]
    threshold: Threshold = Threshold(test_case.expected_threshold_name)

    assert override.paths == test_case.expected_paths
    assert override.thresholds[threshold] == test_case.expected_threshold_value
    assert override.reason == test_case.expected_reason
    with pytest.raises(TypeError):
        override.thresholds[threshold] = 0  # ty: ignore[invalid-assignment]


@pytest.mark.parametrize(
    "test_case",
    [
        ThresholdResolutionTestCase(
            description="path override beats matching role and global values",
            config_text=(
                'roots = ["src/pkg"]\n'
                "[thresholds]\nmax_main_container_modules = 21\n"
                "[roles.main]\nmax_main_container_modules = 22\n"
                "[[threshold_overrides]]\n"
                'paths = ["src/pkg/**/main/**/*.py"]\nreason = "broad"\n'
                "thresholds = { max_main_container_modules = 23 }\n"
            ),
            path="src/pkg/orders/main/read.py",
            role="main",
            threshold_name="max_main_container_modules",
            expected_value=23,
            expected_pattern="src/pkg/**/main/**/*.py",
            expected_reason="broad",
            expected_override_order=0,
        ),
        ThresholdResolutionTestCase(
            description="most semantically specific individual matching pattern wins",
            config_text=(
                'roots = ["src/pkg"]\n'
                "[[threshold_overrides]]\n"
                'paths = ["**/main/*.py", "src/pkg/orders/main/*.py"]\nreason = "specific"\n'
                "thresholds = { max_main_container_modules = 24 }\n"
                "[[threshold_overrides]]\n"
                'paths = ["src/pkg/**/main/*.py"]\nreason = "later broad"\n'
                "thresholds = { max_main_container_modules = 25 }\n"
            ),
            path="src/pkg/orders/main/read.py",
            role="main",
            threshold_name="max_main_container_modules",
            expected_value=24,
            expected_pattern="src/pkg/orders/main/*.py",
            expected_reason="specific",
            expected_override_order=0,
        ),
        ThresholdResolutionTestCase(
            description="more literal segments beat a longer broad pattern",
            config_text=(
                'roots = ["src/pkg"]\n'
                "[[threshold_overrides]]\n"
                'paths = ["src/pkg/orders/very_long_literal_prefix*/**/*.py"]\n'
                'reason = "long broad"\n'
                "thresholds = { max_main_container_modules = 27 }\n"
                "[[threshold_overrides]]\n"
                'paths = ["src/pkg/orders/*/main/read.py"]\n'
                'reason = "constrained"\n'
                "thresholds = { max_main_container_modules = 28 }\n"
            ),
            path="src/pkg/orders/very_long_literal_prefix_value/main/read.py",
            role="main",
            threshold_name="max_main_container_modules",
            expected_value=28,
            expected_pattern="src/pkg/orders/*/main/read.py",
            expected_reason="constrained",
            expected_override_order=1,
        ),
        ThresholdResolutionTestCase(
            description="later declaration wins equal normalized specificity",
            config_text=(
                'roots = ["src/pkg"]\n'
                "[[threshold_overrides]]\n"
                'paths = ["src/pkg/*/main/*.py"]\nreason = "first"\n'
                "thresholds = { max_main_container_modules = 24 }\n"
                "[[threshold_overrides]]\n"
                'paths = ["src/pkg/*/main/*.py"]\nreason = "second"\n'
                "thresholds = { max_main_container_modules = 26 }\n"
            ),
            path="src/pkg/orders/main/read.py",
            role="main",
            threshold_name="max_main_container_modules",
            expected_value=26,
            expected_pattern="src/pkg/*/main/*.py",
            expected_reason="second",
            expected_override_order=1,
        ),
        ThresholdResolutionTestCase(
            description="role value wins when no path override matches",
            config_text=(
                'roots = ["src/pkg"]\n[thresholds]\nmax_main_container_modules = 21\n'
                "[roles.main]\nmax_main_container_modules = 22\n"
            ),
            path="src/pkg/orders/main/read.py",
            role="main",
            threshold_name="max_main_container_modules",
            expected_value=22,
            expected_pattern=None,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_threshold_layers_when_resolving_path_then_applies_precedence(
    tmp_path: Path, test_case: ThresholdResolutionTestCase
) -> None:
    write_strata_toml(root=tmp_path, contents=test_case.config_text)
    config: Config = load_config(tmp_path)
    threshold: Threshold = Threshold(test_case.threshold_name)

    resolution: ThresholdResolution = resolve_threshold(
        config=config, name=threshold, path=test_case.path, role=test_case.role
    )

    assert resolution.effective_value == test_case.expected_value
    assert resolution.matched_pattern == test_case.expected_pattern
    assert resolution.reason == test_case.expected_reason
    assert resolution.override_order == test_case.expected_override_order


@pytest.mark.parametrize(
    "test_case",
    [
        ConfigDefaultsTestCase(
            description="role threshold override is stored separately from global defaults",
            config_text=(
                'roots = ["src/pkg"]\n'
                "[thresholds]\nmax_statements = 50\n"
                "[roles.entry]\nmax_statements = 30\n"
            ),
            expected_roots=("src/pkg",),
            expected_tests=("tests",),
            expected_tooling=(),
            expected_threshold_name="max_statements",
            expected_threshold_value=50,
            expected_role_name="entry",
            expected_role_threshold_name="max_statements",
            expected_role_threshold_value=30,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_role_threshold_override_when_loading_then_global_and_role_values_apply(
    tmp_path: Path,
    test_case: ConfigDefaultsTestCase,
) -> None:
    write_strata_toml(root=tmp_path, contents=test_case.config_text)

    config: Config = load_config(tmp_path)
    threshold: Threshold = Threshold(test_case.expected_threshold_name)
    role_threshold: Threshold = Threshold(test_case.expected_role_threshold_name or "")

    assert config.thresholds[threshold] == test_case.expected_threshold_value
    assert config.role_thresholds[test_case.expected_role_name or ""][role_threshold] == (
        test_case.expected_role_threshold_value
    )


@pytest.mark.parametrize(
    "test_case",
    [
        ConfigContractTestCase(
            description="default validator contract is present",
            config_text='roots = ["src/pkg"]\n',
            expected_pattern="validate_*",
            expected_behavior="no-return",
        ),
        ConfigContractTestCase(
            description="default predicate contract is present",
            config_text='roots = ["src/pkg"]\n',
            expected_pattern="supports_*",
            expected_behavior="returns-bool",
        ),
        ConfigContractTestCase(
            description="default value contract is present",
            config_text='roots = ["src/pkg"]\n',
            expected_pattern="as_*",
            expected_behavior="returns-value",
        ),
        ConfigContractTestCase(
            description="default iterator contract is present",
            config_text='roots = ["src/pkg"]\n',
            expected_pattern="iter_*",
            expected_behavior="returns-iterator",
        ),
        ConfigContractTestCase(
            description="user contract merges with defaults",
            config_text='roots = ["src/pkg"]\n[contracts]\n"write_*" = "no-return"\n',
            expected_pattern="write_*",
            expected_behavior="no-return",
        ),
        ConfigContractTestCase(
            description="custom predicate behavior is accepted",
            config_text=('roots = ["src/pkg"]\n[contracts]\n"eligible_*" = "returns-bool"\n'),
            expected_pattern="eligible_*",
            expected_behavior="returns-bool",
        ),
        ConfigContractTestCase(
            description="custom value behavior is accepted",
            config_text=('roots = ["src/pkg"]\n[contracts]\n"fetch_*" = "returns-value"\n'),
            expected_pattern="fetch_*",
            expected_behavior="returns-value",
        ),
        ConfigContractTestCase(
            description="custom iterator behavior is accepted",
            config_text=('roots = ["src/pkg"]\n[contracts]\n"stream_*" = "returns-iterator"\n'),
            expected_pattern="stream_*",
            expected_behavior="returns-iterator",
        ),
        ConfigContractTestCase(
            description="exact default key is overridden by configured behavior",
            config_text=('roots = ["src/pkg"]\n[contracts]\n"is_*" = "returns-value"\n'),
            expected_pattern="is_*",
            expected_behavior="returns-value",
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_contract_config_when_loading_then_defaults_and_user_contracts_apply(
    tmp_path: Path,
    test_case: ConfigContractTestCase,
) -> None:
    write_strata_toml(root=tmp_path, contents=test_case.config_text)

    config: Config = load_config(tmp_path)

    assert config.contracts[test_case.expected_pattern] == test_case.expected_behavior
    assert config.contracts["enforce_*"] == "no-return"
