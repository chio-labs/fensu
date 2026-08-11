"""Tests for explicit named analyzer target configuration."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from fensu.analysis.main.analyzer_capability import analyzer_capability
from fensu.analysis.main.require_analyzer_backend import require_analyzer_backend
from fensu.analysis.models import AnalyzerCapability
from fensu.cache.fingerprints._helpers.fingerprints import config_fingerprint
from fensu.cache.fingerprints.models import CacheFingerprint
from fensu.config._helpers.validate import select_config_target
from fensu.config.exceptions import ConfigError
from fensu.config.main.load_target_project_config import load_target_project_config
from fensu.config.models import Config
from fensu.config.types import AnalyzerId
from fensu.rules.authoring.types import Threshold
from tests.unit.src.fensu.config._test_types import (
    AnalyzerCapabilityTestCase,
    AnalyzerIdentityTestCase,
    CanonicalTargetRootTestCase,
    EvaluationFingerprintTestCase,
    InvalidTargetConfigTestCase,
    TargetConfigTestCase,
    WebExceptionPathTestCase,
    WebTargetDefaultsTestCase,
    WebTestLayoutFingerprintTestCase,
    WebThresholdAliasTestCase,
)
from tests.unit.src.fensu.config.helpers import write_fensu_toml

RACEWATCH_WEB_CONFIG: str = """[targets.web]
analyzer = "svelte"
root = "frontend"
roots = ["src"]
tests = ["tests"]
tooling = ["tooling"]
ui_kit = "src/ui-kit"
test_layout = "mirrored"
rule_packs = ["sveltekit"]
select = ["FPSK"]

[targets.web.thresholds]
max_route_script_lines = 200
max_component_script_lines = 250
max_state_lines = 300
max_imported_bindings = 20
max_public_exports = 20
max_state_public_members = 20
max_state_cells = 15
max_total_runes = 20
max_state_functions = 15
max_resource_families = 1
max_main_container_modules = 20
max_helpers_container_modules = 10
max_role_depth = 1
max_function_statements = 70
max_entry_statements = 40
max_entry_distinct_calls = 20
max_entry_locals = 20
max_arguments = 10
max_file_lines = 2000
max_api_lines = 200
max_api_exports = 3

[targets.web.evaluation]
include = ["src/**/*.{ts,js,svelte}", "tests/**/*.ts", "tooling/**/*.ts"]
exclude = []
"""


@pytest.mark.skipif(sys.platform == "win32", reason="symlink creation requires Windows privileges")
@pytest.mark.parametrize(
    "test_case",
    [
        CanonicalTargetRootTestCase(
            description="internal alias canonicalizes effective config and cache identity",
            alias="alias",
            configured_alias="alias/missing",
            canonical="canonical",
            expected_target_root="canonical/missing",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_internal_target_alias_when_loading_then_effective_root_and_cache_are_canonical(
    tmp_path: Path,
    test_case: CanonicalTargetRootTestCase,
) -> None:
    canonical: Path = tmp_path / test_case.canonical
    (canonical / "src/app").mkdir(parents=True)
    (tmp_path / test_case.alias).symlink_to(canonical, target_is_directory=True)
    alias_config: str = (
        "[targets.app]\n"
        'analyzer = "python"\n'
        f'root = "{test_case.configured_alias}"\n'
        'roots = ["src/app"]\n'
    )
    canonical_config: str = alias_config.replace(test_case.alias, test_case.canonical)
    write_fensu_toml(root=tmp_path, contents=alias_config)

    alias_loaded: Config = load_target_project_config(start=tmp_path, target="app").config
    alias_fingerprint: CacheFingerprint = config_fingerprint(alias_loaded)
    write_fensu_toml(root=tmp_path, contents=canonical_config)
    canonical_loaded: Config = load_target_project_config(start=tmp_path, target="app").config
    canonical_fingerprint: CacheFingerprint = config_fingerprint(canonical_loaded)

    assert alias_loaded.target_root == test_case.expected_target_root
    assert canonical_loaded.target_root == test_case.expected_target_root
    assert alias_fingerprint == canonical_fingerprint


@pytest.mark.parametrize(
    "test_case",
    [
        TargetConfigTestCase(
            description="one explicit Python target is selected automatically",
            config_text=(
                "[targets.app]\n"
                'analyzer = "python"\n'
                'roots = ["src/app"]\n'
                'tests = ["tests/app"]\n'
                'tooling = ["scripts/app"]\n'
                'select = ["FFA"]\n'
            ),
            target=None,
            expected_target="app",
            expected_target_root=".",
            expected_roots=("src/app",),
            expected_select=("FFA",),
        ),
        TargetConfigTestCase(
            description="named selection chooses one of multiple Python targets",
            config_text=(
                "[targets.api]\n"
                'analyzer = "python"\n'
                'roots = ["src/api"]\n'
                'select = ["FFA"]\n'
                "[targets.worker]\n"
                'analyzer = "python"\n'
                'root = "."\n'
                'roots = ["src/worker"]\n'
                'select = ["FFL"]\n'
            ),
            target="worker",
            expected_target="worker",
            expected_target_root=".",
            expected_roots=("src/worker",),
            expected_select=("FFL",),
        ),
        TargetConfigTestCase(
            description="non-dot target root is normalized without rewriting local paths",
            config_text=(
                "[targets.frontend]\n"
                'analyzer = "python"\n'
                'root = "./frontend/nested/.."\n'
                'roots = ["src/app"]\n'
                'tests = ["tests"]\n'
                'tooling = ["scripts"]\n'
                'select = ["FFA"]\n'
            ),
            target=None,
            expected_target="frontend",
            expected_target_root="frontend",
            expected_roots=("src/app",),
            expected_select=("FFA",),
        ),
        TargetConfigTestCase(
            description="backslash traversal normalizes with POSIX traversal semantics",
            config_text=(
                "[targets.backend]\n"
                'analyzer = "python"\n'
                "root = 'frontend\\..\\backend'\n"
                'roots = ["src/app"]\n'
                'select = ["FFA"]\n'
            ),
            target=None,
            expected_target="backend",
            expected_target_root="backend",
            expected_roots=("src/app",),
            expected_select=("FFA",),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_explicit_targets_when_loading_then_selects_flat_python_config(
    tmp_path: Path, test_case: TargetConfigTestCase
) -> None:
    write_fensu_toml(root=tmp_path, contents=test_case.config_text)

    config: Config = load_target_project_config(start=tmp_path, target=test_case.target).config

    assert config.analyzer == "python"
    assert config.target == test_case.expected_target
    assert config.target_root == test_case.expected_target_root
    assert config.roots == test_case.expected_roots
    assert config.select == test_case.expected_select


@pytest.mark.parametrize(
    "test_case",
    [
        WebTargetDefaultsTestCase(
            description="generic TypeScript has no SvelteKit or shadcn default",
            analyzer="typescript",
            extra_config="",
            expected_rule_packs=(),
            expected_shadcn=None,
            expected_ui_kit=None,
            expected_test_layout="mirrored",
        ),
        WebTargetDefaultsTestCase(
            description="Svelte does not imply a SvelteKit policy pack",
            analyzer="svelte",
            extra_config="",
            expected_rule_packs=(),
            expected_shadcn=None,
            expected_ui_kit=None,
            expected_test_layout="mirrored",
        ),
        WebTargetDefaultsTestCase(
            description="SvelteKit policy activation remains explicit",
            analyzer="svelte",
            extra_config=(
                'rule_packs = ["sveltekit"]\n'
                'ui_kit = "src/lib/design/ui-kit"\n'
                'test_layout = "colocated"\n'
            ),
            expected_rule_packs=("sveltekit",),
            expected_shadcn=None,
            expected_ui_kit="src/lib/design/ui-kit",
            expected_test_layout="colocated",
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_web_target_when_loading_then_rule_pack_activation_is_explicit(
    tmp_path: Path, test_case: WebTargetDefaultsTestCase
) -> None:
    write_fensu_toml(
        root=tmp_path,
        contents=(
            "[targets.web]\n"
            f'analyzer = "{test_case.analyzer}"\n'
            'roots = ["src"]\n'
            f"{test_case.extra_config}"
        ),
    )

    config: Config = load_target_project_config(start=tmp_path, target="web").config

    assert config.rule_packs == test_case.expected_rule_packs
    assert config.shadcn == test_case.expected_shadcn
    assert config.ui_kit == test_case.expected_ui_kit
    assert config.test_layout == test_case.expected_test_layout


@pytest.mark.parametrize(
    "test_case",
    [
        WebTestLayoutFingerprintTestCase(
            description="mirrored and colocated web layouts have distinct fingerprints",
            first_layout="mirrored",
            second_layout="colocated",
            expected_equal=False,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_web_test_layout_change_when_fingerprinting_then_identity_changes(
    tmp_path: Path, test_case: WebTestLayoutFingerprintTestCase
) -> None:
    template: str = '[targets.web]\nanalyzer = "typescript"\nroots = ["src"]\ntest_layout = "{}"\n'
    (tmp_path / "src").mkdir()
    write_fensu_toml(root=tmp_path, contents=template.format(test_case.first_layout))
    first: CacheFingerprint = config_fingerprint(
        load_target_project_config(start=tmp_path, target="web").config
    )
    write_fensu_toml(root=tmp_path, contents=template.format(test_case.second_layout))
    second: CacheFingerprint = config_fingerprint(
        load_target_project_config(start=tmp_path, target="web").config
    )

    assert (first == second) is test_case.expected_equal


@pytest.mark.parametrize(
    "test_case",
    [
        WebThresholdAliasTestCase(
            description="TypeScript target normalizes familiar web thresholds",
            analyzer="typescript",
            expected_analyzer="typescript",
            expected_fingerprints_equal=True,
        ),
        WebThresholdAliasTestCase(
            description="Svelte target normalizes familiar web thresholds",
            analyzer="svelte",
            expected_analyzer="svelte",
            expected_fingerprints_equal=True,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_explicit_web_threshold_aliases_when_loading_then_canonical_identity_is_preserved(
    tmp_path: Path, test_case: WebThresholdAliasTestCase
) -> None:
    write_fensu_toml(
        root=tmp_path,
        contents=(
            "[targets.web]\n"
            f'analyzer = "{test_case.analyzer}"\n'
            'roots = ["src"]\n'
            "[targets.web.thresholds]\n"
            "max_entry_statements = 41\n"
            "max_entry_distinct_calls = 21\n"
            "max_entry_locals = 22\n"
            "max_function_statements = 71\n"
            "[targets.web.roles.main]\n"
            "max_entry_statements = 31\n"
            "[[targets.web.threshold_overrides]]\n"
            'paths = ["src/routes/**"]\n'
            'reason = "Route-specific entry budget."\n'
            "thresholds = { max_entry_statements = 51, max_function_statements = 81 }\n"
        ),
    )

    config: Config = load_target_project_config(start=tmp_path, target="web").config

    assert config.analyzer == test_case.expected_analyzer
    assert config.thresholds[Threshold.MAX_STATEMENTS] == 41
    assert config.thresholds[Threshold.MAX_DISTINCT_CALLS] == 21
    assert config.thresholds[Threshold.MAX_LOCALS] == 22
    assert config.thresholds[Threshold.MAX_STATEMENTS_GLOBAL] == 71
    assert config.role_thresholds["main"][Threshold.MAX_STATEMENTS] == 31
    assert config.threshold_overrides[0].thresholds == {
        Threshold.MAX_STATEMENTS: 51,
        Threshold.MAX_STATEMENTS_GLOBAL: 81,
    }


@pytest.mark.parametrize(
    "test_case",
    [
        WebThresholdAliasTestCase(
            description="alias and canonical web thresholds share a fingerprint",
            analyzer="typescript",
            expected_analyzer="typescript",
            expected_fingerprints_equal=True,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_alias_and_canonical_web_configs_when_fingerprinting_then_identity_matches(
    tmp_path: Path, test_case: WebThresholdAliasTestCase
) -> None:
    template: str = (
        f'[targets.web]\nanalyzer = "{test_case.analyzer}"\nroots = ["src"]\n'
        "[targets.web.thresholds]\n{} = 41\n"
    )
    (tmp_path / "src").mkdir()
    write_fensu_toml(root=tmp_path, contents=template.format("max_entry_statements"))
    alias: CacheFingerprint = config_fingerprint(
        load_target_project_config(start=tmp_path, target="web").config
    )
    write_fensu_toml(root=tmp_path, contents=template.format("max_statements"))
    canonical: CacheFingerprint = config_fingerprint(
        load_target_project_config(start=tmp_path, target="web").config
    )

    assert (alias == canonical) is test_case.expected_fingerprints_equal


@pytest.mark.parametrize(
    "test_case",
    [
        EvaluationFingerprintTestCase(
            description="RaceWatch empty web exclusion matches omission",
            config_text=RACEWATCH_WEB_CONFIG,
            target="web",
            expected_include=(
                "src/**/*.{ts,js,svelte}",
                "tests/**/*.ts",
                "tooling/**/*.ts",
            ),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_racewatch_web_empty_exclude_when_fingerprinting_then_identity_matches_omission(
    tmp_path: Path, test_case: EvaluationFingerprintTestCase
) -> None:
    (tmp_path / "frontend/src").mkdir(parents=True)
    write_fensu_toml(root=tmp_path, contents=test_case.config_text)

    explicit: Config = load_target_project_config(start=tmp_path, target=test_case.target).config
    explicit_fingerprint: CacheFingerprint = config_fingerprint(explicit)
    write_fensu_toml(
        root=tmp_path,
        contents=test_case.config_text.replace("exclude = []\n", ""),
    )
    omitted: Config = load_target_project_config(start=tmp_path, target=test_case.target).config

    assert explicit.evaluation.include == test_case.expected_include
    assert explicit.evaluation.exclude == ()
    assert explicit_fingerprint == config_fingerprint(omitted)


@pytest.mark.parametrize(
    "test_case",
    [
        WebExceptionPathTestCase(
            description="TypeScript exceptions accept TypeScript modules",
            analyzer="typescript",
            expected_path="src/module.ts",
        ),
        WebExceptionPathTestCase(
            description="TypeScript exceptions accept JavaScript modules",
            analyzer="typescript",
            expected_path="src/module.js",
        ),
        WebExceptionPathTestCase(
            description="Svelte exceptions accept component modules",
            analyzer="svelte",
            expected_path="src/Component.svelte",
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_analyzer_compatible_web_exception_when_loading_then_path_is_accepted(
    tmp_path: Path, test_case: WebExceptionPathTestCase
) -> None:
    write_fensu_toml(
        root=tmp_path,
        contents=(
            "[targets.web]\n"
            f'analyzer = "{test_case.analyzer}"\n'
            'roots = ["src"]\nrule_packs = ["typescript"]\nselect = ["FPTSA003"]\n'
            "[[targets.web.rule_exceptions]]\n"
            'rule = "FPTSA003"\n'
            f'path = "{test_case.expected_path}"\n'
            'reason = "external contract"\n'
        ),
    )

    config: Config = load_target_project_config(start=tmp_path, target="web").config

    assert config.rule_exceptions[0].path == test_case.expected_path


@pytest.mark.parametrize(
    "test_case",
    [
        InvalidTargetConfigTestCase(
            description="targets must be a table",
            config_text="targets = []\n",
            target=None,
            expected_error_fragment="targets must be a table of named targets",
        ),
        InvalidTargetConfigTestCase(
            description="targets table must not be empty",
            config_text="targets = {}\n",
            target=None,
            expected_error_fragment="must define at least one named target",
        ),
        InvalidTargetConfigTestCase(
            description="named target must be a table",
            config_text='targets = { app = "python" }\n',
            target=None,
            expected_error_fragment="target app must be a table",
        ),
        InvalidTargetConfigTestCase(
            description="legacy and explicit configuration cannot be mixed",
            config_text=(
                'roots = ["src/legacy"]\n[targets.app]\nanalyzer = "python"\nroots = ["src/app"]\n'
            ),
            target=None,
            expected_error_fragment="cannot be mixed with legacy top-level config keys: roots",
        ),
        InvalidTargetConfigTestCase(
            description="target analyzer is required",
            config_text='[targets.app]\nroots = ["src/app"]\n',
            target=None,
            expected_error_fragment="targets.app.analyzer must be a non-empty string",
        ),
        InvalidTargetConfigTestCase(
            description="unknown analyzers fail closed",
            config_text=('[targets.web]\nanalyzer = "ruby"\nroots = ["src/web"]\n'),
            target=None,
            expected_error_fragment="Unknown analyzer for target web: ruby",
        ),
        InvalidTargetConfigTestCase(
            description="target roots cannot traverse above the repository",
            config_text=(
                '[targets.app]\nanalyzer = "python"\nroot = "../frontend"\nroots = ["src/app"]\n'
            ),
            target=None,
            expected_error_fragment="must not escape the repository",
        ),
        InvalidTargetConfigTestCase(
            description="backslash target roots cannot traverse above the repository",
            config_text=(
                "[targets.app]\n"
                'analyzer = "python"\n'
                "root = 'frontend\\..\\..\\backend'\n"
                'roots = ["src/app"]\n'
            ),
            target=None,
            expected_error_fragment="must not escape the repository",
        ),
        InvalidTargetConfigTestCase(
            description="target roots cannot be absolute",
            config_text=(
                '[targets.app]\nanalyzer = "python"\nroot = "/frontend"\nroots = ["src/app"]\n'
            ),
            target=None,
            expected_error_fragment="must be repository-relative",
        ),
        InvalidTargetConfigTestCase(
            description="unknown target-local fields are rejected",
            config_text=(
                '[targets.app]\nanalyzer = "python"\nroots = ["src/app"]\nlanguage = "python"\n'
            ),
            target=None,
            expected_error_fragment="Unknown targets.app config key(s): language",
        ),
        InvalidTargetConfigTestCase(
            description="unknown requested target names are rejected",
            config_text=('[targets.app]\nanalyzer = "python"\nroots = ["src/app"]\n'),
            target="missing",
            expected_error_fragment="Unknown target name: missing",
        ),
        InvalidTargetConfigTestCase(
            description="multiple targets require explicit selection",
            config_text=(
                "[targets.api]\n"
                'analyzer = "python"\n'
                'roots = ["src/api"]\n'
                "[targets.worker]\n"
                'analyzer = "python"\n'
                'roots = ["src/worker"]\n'
            ),
            target=None,
            expected_error_fragment="select one with --target TARGET",
        ),
        InvalidTargetConfigTestCase(
            description="legacy config rejects named target selection",
            config_text='roots = ["src/app"]\n',
            target="app",
            expected_error_fragment="Unknown target name: app",
        ),
        InvalidTargetConfigTestCase(
            description="unselected target must define non-empty roots",
            config_text=(
                "[targets.valid]\n"
                'analyzer = "python"\n'
                'roots = ["src/valid"]\n'
                "[targets.invalid]\n"
                'analyzer = "python"\n'
                "roots = []\n"
            ),
            target="valid",
            expected_error_fragment="must define at least one root in roots",
        ),
        InvalidTargetConfigTestCase(
            description="legacy flat config cannot configure web test layout",
            config_text='roots = ["src/app"]\ntest_layout = "mirrored"\n',
            target=None,
            expected_error_fragment="supported only by TypeScript and Svelte analyzers",
        ),
        InvalidTargetConfigTestCase(
            description="Python targets cannot configure web test layout",
            config_text=(
                '[targets.app]\nanalyzer = "python"\nroots = ["src/app"]\n'
                'test_layout = "mirrored"\n'
            ),
            target="app",
            expected_error_fragment="supported only by TypeScript and Svelte analyzers",
        ),
        InvalidTargetConfigTestCase(
            description="web test layout values fail closed",
            config_text=(
                '[targets.web]\nanalyzer = "svelte"\nroots = ["src"]\ntest_layout = "adjacent"\n'
            ),
            target="web",
            expected_error_fragment="must be 'mirrored' or 'colocated'",
        ),
        InvalidTargetConfigTestCase(
            description="legacy flat config rejects web threshold aliases",
            config_text=('roots = ["src/app"]\n[thresholds]\nmax_entry_statements = 40\n'),
            target=None,
            expected_error_fragment="Unknown threshold key in thresholds: max_entry_statements",
        ),
        InvalidTargetConfigTestCase(
            description="Python targets reject web threshold aliases",
            config_text=(
                '[targets.app]\nanalyzer = "python"\nroots = ["src/app"]\n'
                "[targets.app.thresholds]\nmax_function_statements = 70\n"
            ),
            target="app",
            expected_error_fragment="Unknown threshold key in thresholds: max_function_statements",
        ),
        InvalidTargetConfigTestCase(
            description="web targets reject conflicting alias and canonical thresholds",
            config_text=(
                '[targets.web]\nanalyzer = "typescript"\nroots = ["src"]\n'
                "[targets.web.thresholds]\nmax_entry_statements = 40\nmax_statements = 41\n"
            ),
            target="web",
            expected_error_fragment="Conflicting threshold values in thresholds",
        ),
        InvalidTargetConfigTestCase(
            description="web overrides reject conflicting alias and canonical thresholds",
            config_text=(
                '[targets.web]\nanalyzer = "svelte"\nroots = ["src"]\n'
                "[[targets.web.threshold_overrides]]\n"
                'paths = ["src/**"]\nreason = "conflict"\n'
                "thresholds = { max_entry_locals = 20, max_locals = 21 }\n"
            ),
            target="web",
            expected_error_fragment="Conflicting threshold values in threshold_overrides.thresholds",
        ),
        InvalidTargetConfigTestCase(
            description="explicit targets reject an empty evaluation include",
            config_text=(
                '[targets.web]\nanalyzer = "svelte"\nroots = ["src"]\n'
                "[targets.web.evaluation]\ninclude = []\n"
            ),
            target="web",
            expected_error_fragment="evaluation.include must not be empty",
        ),
        InvalidTargetConfigTestCase(
            description="removed framework configuration is rejected",
            config_text=(
                '[targets.web]\nanalyzer = "svelte"\nroots = ["src"]\nframework = "sveltekit"\n'
            ),
            target="web",
            expected_error_fragment="Unknown targets.web config key(s): framework",
        ),
        InvalidTargetConfigTestCase(
            description="TypeScript exceptions reject Python paths",
            config_text=(
                '[targets.web]\nanalyzer = "typescript"\nroots = ["src"]\n'
                '[[targets.web.rule_exceptions]]\nrule = "FPTSA003"\n'
                'path = "src/module.py"\nreason = "wrong analyzer"\n'
            ),
            target="web",
            expected_error_fragment="not an exact repository-relative POSIX source for typescript",
        ),
        InvalidTargetConfigTestCase(
            description="portable web dependencies reject Windows drives",
            config_text=(
                '[targets.web]\nanalyzer = "svelte"\nroots = ["src"]\n'
                'openapi = "C:/contracts/openapi.json"\n'
            ),
            target="web",
            expected_error_fragment="repository-relative path",
        ),
        InvalidTargetConfigTestCase(
            description="explicit missing OpenAPI dependencies fail closed",
            config_text=(
                '[targets.web]\nanalyzer = "svelte"\nroots = ["src"]\n'
                'openapi = "contracts/openapi.json"\n'
            ),
            target="web",
            expected_error_fragment="web dependency does not exist: contracts/openapi.json",
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_invalid_explicit_targets_when_loading_then_fails_closed(
    tmp_path: Path, test_case: InvalidTargetConfigTestCase
) -> None:
    write_fensu_toml(root=tmp_path, contents=test_case.config_text)

    with pytest.raises(ConfigError) as error:
        load_target_project_config(start=tmp_path, target=test_case.target)

    assert test_case.expected_error_fragment in str(error.value)


@pytest.mark.skipif(sys.platform == "win32", reason="symlink creation requires Windows privileges")
@pytest.mark.parametrize(
    "test_case",
    [
        InvalidTargetConfigTestCase(
            description="OpenAPI symlink cannot escape a web target",
            config_text=(
                '[targets.web]\nanalyzer = "svelte"\nroot = "frontend"\n'
                'roots = ["src"]\nopenapi = "contracts/openapi.json"\n'
            ),
            target="web",
            expected_error_fragment="web dependency escapes the target: contracts/openapi.json",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_web_dependency_symlink_when_loading_then_target_escape_fails_closed(
    tmp_path: Path, test_case: InvalidTargetConfigTestCase
) -> None:
    write_fensu_toml(root=tmp_path, contents=test_case.config_text)
    (tmp_path / "frontend/src").mkdir(parents=True)
    (tmp_path / "frontend/contracts").mkdir(parents=True)
    (tmp_path / "outside").mkdir()
    outside: Path = tmp_path / "outside/openapi.json"
    outside.write_text('{"paths": {}}\n')
    (tmp_path / "frontend/contracts/openapi.json").symlink_to(outside)

    with pytest.raises(ConfigError) as error:
        load_target_project_config(start=tmp_path, target=test_case.target)

    assert test_case.expected_error_fragment in str(error.value)


@pytest.mark.parametrize(
    "test_case",
    [
        AnalyzerIdentityTestCase(
            description="Python analyzer identity round trips",
            value="python",
            expected_analyzer=AnalyzerId.PYTHON,
            expected_error_fragment=None,
        ),
        AnalyzerIdentityTestCase(
            description="TypeScript analyzer identity round trips",
            value="typescript",
            expected_analyzer=AnalyzerId.TYPESCRIPT,
            expected_error_fragment=None,
        ),
        AnalyzerIdentityTestCase(
            description="Svelte analyzer identity round trips",
            value="svelte",
            expected_analyzer=AnalyzerId.SVELTE,
            expected_error_fragment=None,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_exact_analyzer_spelling_when_parsing_then_typed_identity_round_trips(
    test_case: AnalyzerIdentityTestCase,
) -> None:
    _, _, parsed, _ = select_config_target(
        raw={"targets": {"app": {"analyzer": test_case.value, "roots": ["src"]}}},
        target="app",
    )

    assert parsed is test_case.expected_analyzer
    assert str(parsed) == test_case.value


@pytest.mark.parametrize(
    "test_case",
    [
        AnalyzerIdentityTestCase(
            description=f"noncanonical analyzer {value} is unknown",
            value=value,
            expected_analyzer=None,
            expected_error_fragment=f"Unknown analyzer for target app: {value}",
        )
        for value in ("Python", "TypeScript", "SVELTE", "ruby")
    ],
    ids=lambda case: case.description,
)
def test_given_noncanonical_analyzer_spelling_when_parsing_then_identity_is_unknown(
    test_case: AnalyzerIdentityTestCase,
) -> None:
    expected_error: str | None = test_case.expected_error_fragment
    assert expected_error is not None
    with pytest.raises(ConfigError, match=expected_error):
        select_config_target(
            raw={"targets": {"app": {"analyzer": test_case.value, "roots": ["src"]}}},
            target="app",
        )


@pytest.mark.parametrize(
    "test_case",
    [
        AnalyzerCapabilityTestCase(
            description=f"known {analyzer.value} backend is publicly available",
            analyzer=analyzer,
            expected_available=True,
            expected_cache_contract=f"{analyzer.value}-policy-v4",
        )
        for analyzer in (AnalyzerId.TYPESCRIPT, AnalyzerId.SVELTE)
    ],
    ids=lambda case: case.description,
)
def test_given_known_web_analyzer_when_resolving_backend_then_is_publicly_available(
    test_case: AnalyzerCapabilityTestCase,
) -> None:
    capability: AnalyzerCapability = analyzer_capability(test_case.analyzer)

    assert capability.available is test_case.expected_available
    assert capability.cache_contract == test_case.expected_cache_contract
    assert require_analyzer_backend(test_case.analyzer) == capability
