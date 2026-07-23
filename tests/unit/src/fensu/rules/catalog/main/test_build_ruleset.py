"""Tests for ruleset registry building and custom rule loading."""

from __future__ import annotations

import importlib
import sys
from dataclasses import replace
from pathlib import Path
from types import ModuleType

import pytest

from fensu.config.exceptions import ConfigError, ConfigValidationError
from fensu.config.main.load_project_config import load_project_config
from fensu.config.models import Config, RuleExceptionEntry
from fensu.rules.authoring.main.define import rule
from fensu.rules.authoring.models import RuleOption, RuleSpec
from fensu.rules.authoring.types import Family, RuleKind
from fensu.rules.catalog._helpers import loading as loading_module
from fensu.rules.catalog.constants import CORE_RULES
from fensu.rules.catalog.main._build_rule_selection import build_rule_selection
from fensu.rules.catalog.main.build_catalogue import build_catalogue
from fensu.rules.catalog.main.build_ruleset import build_ruleset
from fensu.rules.catalog.models import RuleSelection
from tests.unit.src.fensu.rules.catalog.main._test_types import (
    CatalogueQualityTestCase,
    CustomRuleLoadTestCase,
    DirectRuleSpecErrorTestCase,
    ModuleIsolationTestCase,
    RegistryErrorTestCase,
    RuleExceptionCodeTestCase,
    RuleSelectionErrorTestCase,
    RuleSelectionTestCase,
    SelectCompositionTestCase,
    UnselectedRuleOptionTestCase,
)
from tests.unit.src.fensu.rules.catalog.main.helpers import (
    catalogue_quality_issues,
    make_core_rule,
    write_custom_rule_file,
    write_direct_custom_rule_file,
    write_importing_custom_rule_package,
    write_module_package,
)


@pytest.mark.parametrize(
    "test_case",
    [
        UnselectedRuleOptionTestCase(
            description="unselected discovered rule still validates required options",
            rule_code="XOP010",
            expected_error_fragment=("Required option required_count for rule XOP010 is missing"),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_unselected_discovered_rule_when_loading_config_then_validates_options(
    tmp_path: Path,
    test_case: UnselectedRuleOptionTestCase,
) -> None:
    _ = write_custom_rule_file(
        root=tmp_path,
        relative_path="rules/unselected.py",
        rule_code=test_case.rule_code,
        prelude=(
            "from fensu import RuleOption\n\n"
            "_REQUIRED_COUNT = RuleOption.integer("
            "name='required_count', required=True)\n"
        ),
        decorator_arguments=", options=(_REQUIRED_COUNT,)",
    )
    (tmp_path / "fensu.toml").write_text(
        'roots = ["src/pkg"]\ntests = []\ntooling = []\nselect = []\n'
        'rule_paths = ["rules/unselected.py"]\n',
        encoding="utf-8",
    )

    with pytest.raises(ConfigValidationError) as error:
        load_project_config(tmp_path)

    assert test_case.expected_error_fragment in str(error.value)


@pytest.mark.parametrize(
    "test_case",
    [
        RuleExceptionCodeTestCase(
            description="unknown exact rule exception code is rejected",
            rule_code="FFS999",
            expected_error_fragment="Unknown rule exception code: FFS999",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_unknown_exception_code_when_building_catalogue_then_raises_config_error(
    test_case: RuleExceptionCodeTestCase,
) -> None:
    config: Config = Config(
        roots=("src/pkg",),
        rule_exceptions=(
            RuleExceptionEntry(
                rule=test_case.rule_code,
                path="src/pkg/a.py",
                symbols=("run",),
                reason="External caller.",
            ),
        ),
    )

    with pytest.raises(ConfigError) as error:
        build_ruleset(config=config)

    assert test_case.expected_error_fragment in str(error.value)


@pytest.mark.parametrize(
    "test_case",
    [
        CatalogueQualityTestCase(
            description="every core rule provides actionable agent-ready metadata",
            forbidden_message_fragments=(
                "role surface violation",
                "role layout violation",
                "role shape violation",
                "test convention violation",
            ),
            max_message_length=120,
            max_remediation_length=400,
            expected_issues=(),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_core_catalogue_when_reviewing_metadata_then_every_rule_is_actionable(
    test_case: CatalogueQualityTestCase,
) -> None:
    issues: tuple[str, ...] = catalogue_quality_issues(
        rules=CORE_RULES,
        forbidden_message_fragments=test_case.forbidden_message_fragments,
        max_message_length=test_case.max_message_length,
        max_remediation_length=test_case.max_remediation_length,
    )

    assert issues == test_case.expected_issues


@pytest.mark.parametrize(
    "test_case",
    [
        CustomRuleLoadTestCase(
            description="custom rule file loads with source path",
            rule_code="XRG001",
            expected_code="XRG001",
            expected_source_fragment="rules/custom_rule.py",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_rule_path_when_building_ruleset_then_loads_custom_rule_with_source(
    tmp_path: Path,
    test_case: CustomRuleLoadTestCase,
) -> None:
    path: Path = write_custom_rule_file(
        root=tmp_path, relative_path="rules/custom_rule.py", rule_code=test_case.rule_code
    )
    config: Config = Config(
        roots=("src/pkg",), rule_paths=(str(path),), select=(test_case.rule_code,)
    )

    ruleset: tuple[RuleSpec, ...] = build_ruleset(config=config, repo_root=tmp_path)

    assert tuple(rule.code for rule in ruleset) == (test_case.expected_code,)
    assert test_case.expected_source_fragment in (ruleset[0].source or "")
    assert loading_module._synthetic_module_name(path) not in sys.modules


@pytest.mark.parametrize(
    "test_case",
    [
        CustomRuleLoadTestCase(
            description="custom rule file loads without sys path mutation",
            rule_code="XRG002",
            expected_code="XRG002",
            expected_source_fragment="rules/custom_rule.py",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_rule_path_when_building_ruleset_then_does_not_add_rule_dir_to_sys_path(
    tmp_path: Path,
    test_case: CustomRuleLoadTestCase,
) -> None:
    path: Path = write_custom_rule_file(
        root=tmp_path, relative_path="rules/custom_rule.py", rule_code=test_case.rule_code
    )
    config: Config = Config(
        roots=("src/pkg",), rule_paths=(str(path),), select=(test_case.rule_code,)
    )

    ruleset: tuple[RuleSpec, ...] = build_ruleset(config=config, repo_root=tmp_path)

    assert tuple(rule.code for rule in ruleset) == (test_case.expected_code,)
    assert str(path.parent) not in sys.path


@pytest.mark.parametrize(
    "test_case",
    [
        CustomRuleLoadTestCase(
            description="scripts rule package imports its local helper through repository root",
            rule_code="XRG004",
            expected_code="XRG004",
            expected_source_fragment="scripts/fensu/rules/custom.py",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_rule_path_with_package_import_when_building_then_resolves_repository_package(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: CustomRuleLoadTestCase,
) -> None:
    _ = importlib.import_module("scripts.benchmarking")
    path: Path = write_importing_custom_rule_package(root=tmp_path, rule_code=test_case.rule_code)
    monkeypatch.chdir(tmp_path)
    config: Config = Config(
        roots=("src/pkg",), rule_paths=(str(path),), select=(test_case.rule_code,)
    )

    ruleset: tuple[RuleSpec, ...] = build_ruleset(config=config, repo_root=tmp_path)

    assert tuple(rule.code for rule in ruleset) == (test_case.expected_code,)
    assert test_case.expected_source_fragment in (ruleset[0].source or "")
    assert str(tmp_path) not in sys.path


@pytest.mark.parametrize(
    "test_case",
    [
        CustomRuleLoadTestCase(
            description="configured module displaces and restores conflicting scripts package",
            rule_code="XRG005",
            expected_code="XRG005",
            expected_source_fragment="scripts/fensu/rules/custom.py",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_rule_module_with_conflicting_package_when_building_then_restores_import_state(
    tmp_path: Path,
    test_case: CustomRuleLoadTestCase,
) -> None:
    scripts_package: ModuleType = importlib.import_module("scripts")
    benchmarking_package: ModuleType = importlib.import_module("scripts.benchmarking")
    _ = write_importing_custom_rule_package(root=tmp_path, rule_code=test_case.rule_code)
    config: Config = Config(
        roots=("src/pkg",),
        rule_modules=("scripts.fensu.rules.custom",),
        select=(test_case.rule_code,),
    )
    previous_path: tuple[str, ...] = tuple(sys.path)

    ruleset: tuple[RuleSpec, ...] = build_ruleset(config=config, repo_root=tmp_path)

    assert tuple(rule.code for rule in ruleset) == (test_case.expected_code,)
    assert test_case.expected_source_fragment in (ruleset[0].source or "")
    assert sys.modules["scripts"] is scripts_package
    assert sys.modules["scripts.benchmarking"] is benchmarking_package
    assert "scripts.fensu.rules.custom" not in sys.modules
    assert tuple(sys.path) == previous_path


@pytest.mark.parametrize(
    "test_case",
    [
        CustomRuleLoadTestCase(
            description="custom rule module is registered only while executing",
            rule_code="XRG003",
            expected_code="XRG003",
            expected_source_fragment="rules/custom_rule.py",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_rule_path_when_executing_then_synthetic_module_is_temporary(
    tmp_path: Path,
    test_case: CustomRuleLoadTestCase,
) -> None:
    path: Path = write_custom_rule_file(
        root=tmp_path,
        relative_path="rules/custom_rule.py",
        rule_code=test_case.rule_code,
        prelude=(
            "import sys\n"
            "if __name__ not in sys.modules:\n"
            "    raise RuntimeError('module is not registered during execution')\n"
        ),
    )
    config: Config = Config(
        roots=("src/pkg",), rule_paths=(str(path),), select=(test_case.rule_code,)
    )

    ruleset: tuple[RuleSpec, ...] = build_ruleset(config=config, repo_root=tmp_path)

    assert tuple(rule.code for rule in ruleset) == (test_case.expected_code,)
    assert test_case.expected_source_fragment in (ruleset[0].source or "")
    assert loading_module._synthetic_module_name(path) not in sys.modules


@pytest.mark.parametrize(
    "test_case",
    [
        CustomRuleLoadTestCase(
            description="custom rule module loads with module source",
            rule_code="XRM001",
            expected_code="XRM001",
            expected_source_fragment="custom_rules_pkg/__init__.py",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_rule_module_when_building_ruleset_then_loads_custom_rule_with_source(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: CustomRuleLoadTestCase,
) -> None:
    module_name: str = write_module_package(
        root=tmp_path, package_name="custom_rules_pkg", rule_code=test_case.rule_code
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    config: Config = Config(
        roots=("src/pkg",), rule_modules=(module_name,), select=(test_case.rule_code,)
    )

    ruleset: tuple[RuleSpec, ...] = build_ruleset(config=config, repo_root=tmp_path)

    assert tuple(rule.code for rule in ruleset) == (test_case.expected_code,)
    assert test_case.expected_source_fragment in (ruleset[0].source or "")


@pytest.mark.parametrize(
    "test_case",
    [
        RegistryErrorTestCase(
            description="syntax error in custom file raises config error naming file",
            rule_source="def broken(:\n    pass\n",
            expected_error_fragment="bad_rule.py",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_syntax_error_custom_rule_file_when_building_ruleset_then_raises_config_error(
    tmp_path: Path,
    test_case: RegistryErrorTestCase,
) -> None:
    path: Path = tmp_path / "rules" / "bad_rule.py"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(test_case.rule_source, encoding="utf-8")
    config: Config = Config(roots=("src/pkg",), rule_paths=(str(path),))

    with pytest.raises(ConfigError) as error:
        build_ruleset(config=config, repo_root=tmp_path)

    assert test_case.expected_error_fragment in str(error.value)
    assert loading_module._synthetic_module_name(path) not in sys.modules


@pytest.mark.parametrize(
    "test_case",
    [
        RegistryErrorTestCase(
            description="custom file using FF namespace is rejected",
            rule_source="FFL999",
            expected_error_fragment="X* namespace",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_custom_rule_file_with_sf_namespace_when_building_ruleset_then_raises_config_error(
    tmp_path: Path,
    test_case: RegistryErrorTestCase,
) -> None:
    path: Path = write_custom_rule_file(
        root=tmp_path, relative_path="rules/bad_rule.py", rule_code=test_case.rule_source
    )
    config: Config = Config(roots=("src/pkg",), rule_paths=(str(path),))

    with pytest.raises(ConfigError) as error:
        build_ruleset(config=config, repo_root=tmp_path)

    assert test_case.expected_error_fragment in str(error.value)


@pytest.mark.parametrize(
    "test_case",
    [
        RegistryErrorTestCase(
            description="malformed direct custom code cannot bypass source policy",
            rule_source="XDB-rule",
            expected_error_fragment="exact X* rule code",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_direct_custom_spec_with_malformed_code_when_loading_then_raises_config_error(
    tmp_path: Path,
    test_case: RegistryErrorTestCase,
) -> None:
    path: Path = write_direct_custom_rule_file(
        root=tmp_path,
        rule_code=test_case.rule_source,
        kind=RuleKind.CUSTOM,
        cacheable=True,
    )

    with pytest.raises(ConfigError) as error:
        build_ruleset(
            config=Config(roots=("src/pkg",), rule_paths=(str(path),)),
            repo_root=tmp_path,
        )

    assert test_case.expected_error_fragment in str(error.value)


@pytest.mark.parametrize(
    "test_case",
    [
        RegistryErrorTestCase(
            description="kind-inconsistent direct custom code cannot bypass source policy",
            rule_source="XDB901",
            expected_error_fragment="X* namespace",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_direct_custom_spec_with_core_kind_when_loading_then_raises_config_error(
    tmp_path: Path,
    test_case: RegistryErrorTestCase,
) -> None:
    path: Path = write_direct_custom_rule_file(
        root=tmp_path,
        rule_code=test_case.rule_source,
        kind=RuleKind.CORE,
        cacheable=True,
    )

    with pytest.raises(ConfigError) as error:
        build_ruleset(
            config=Config(roots=("src/pkg",), rule_paths=(str(path),)),
            repo_root=tmp_path,
        )

    assert test_case.expected_error_fragment in str(error.value)


@pytest.mark.parametrize(
    "test_case",
    [
        DirectRuleSpecErrorTestCase(
            description="path-loaded direct spec with list code raises structured error",
            rule_code=[],
            family_expression="Family.CUSTOM",
            expected_error_fragment="exact X* rule code",
        ),
        DirectRuleSpecErrorTestCase(
            description="path-loaded direct spec with None code raises structured error",
            rule_code=None,
            family_expression="Family.CUSTOM",
            expected_error_fragment="exact X* rule code",
        ),
        DirectRuleSpecErrorTestCase(
            description="path-loaded direct spec with string family raises structured error",
            rule_code="XDM002",
            family_expression="'custom'",
            expected_error_fragment="valid Family member",
        ),
        DirectRuleSpecErrorTestCase(
            description="path-loaded direct spec with None family raises structured error",
            rule_code="XDM003",
            family_expression="None",
            expected_error_fragment="valid Family member",
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_path_loaded_direct_spec_with_malformed_identity_when_building_then_config_error(
    tmp_path: Path,
    test_case: DirectRuleSpecErrorTestCase,
) -> None:
    path: Path = write_direct_custom_rule_file(
        root=tmp_path,
        rule_code=test_case.rule_code,
        family_expression=test_case.family_expression,
        kind=RuleKind.CUSTOM,
    )

    with pytest.raises(ConfigError) as error:
        build_ruleset(
            config=Config(roots=("src/pkg",), rule_paths=(str(path),)),
            repo_root=tmp_path,
        )

    assert test_case.expected_error_fragment in str(error.value)


@pytest.mark.parametrize(
    "test_case",
    [
        RegistryErrorTestCase(
            description="duplicate custom rule codes are rejected",
            rule_source="XDU001",
            expected_error_fragment="Duplicate rule code XDU001",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_duplicate_custom_codes_when_building_ruleset_then_raises_config_error(
    tmp_path: Path,
    test_case: RegistryErrorTestCase,
) -> None:
    first_path: Path = write_custom_rule_file(
        root=tmp_path, relative_path="rules/first.py", rule_code=test_case.rule_source
    )
    second_path: Path = write_custom_rule_file(
        root=tmp_path, relative_path="rules/second.py", rule_code=test_case.rule_source
    )
    config: Config = Config(roots=("src/pkg",), rule_paths=(str(first_path), str(second_path)))

    with pytest.raises(ConfigError) as error:
        build_ruleset(config=config, repo_root=tmp_path)

    assert test_case.expected_error_fragment in str(error.value)


@pytest.mark.parametrize(
    "test_case",
    [
        ModuleIsolationTestCase(
            description="decorated rule from another module does not leak into custom file",
            stale_rule_code="XCL001",
            loaded_rule_code="XCL002",
            expected_codes=("XCL002",),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_foreign_decorated_rule_when_loading_custom_file_then_module_metadata_is_isolated(
    tmp_path: Path,
    test_case: ModuleIsolationTestCase,
) -> None:
    rule(code=test_case.stale_rule_code, family=Family.CUSTOM, slug="clear", message="clear")(
        lambda module, ctx: []
    )
    path: Path = write_custom_rule_file(
        root=tmp_path, relative_path="rules/custom_rule.py", rule_code=test_case.loaded_rule_code
    )

    ruleset: tuple[RuleSpec, ...] = build_ruleset(
        config=Config(
            roots=("src/pkg",),
            rule_paths=(str(path),),
            select=(test_case.stale_rule_code, test_case.loaded_rule_code),
        ),
        repo_root=tmp_path,
    )

    assert tuple(rule.code for rule in ruleset) == test_case.expected_codes


@pytest.mark.parametrize(
    "test_case",
    [
        SelectCompositionTestCase(
            description="family select respects default-off while explicit code enables it",
            select=("FFH",),
            ignore=(),
            expected_codes=("FFH001",),
        ),
        SelectCompositionTestCase(
            description="explicit code select enables default-off rule",
            select=("FFH099",),
            ignore=(),
            expected_codes=("FFH099",),
        ),
        SelectCompositionTestCase(
            description="ignore removes default-on rule",
            select=("FFH",),
            ignore=("FFH001",),
            expected_codes=(),
        ),
        SelectCompositionTestCase(
            description="valid unpopulated core selector matches no rules",
            select=("FFX",),
            ignore=(),
            expected_codes=(),
        ),
        SelectCompositionTestCase(
            description="valid unpopulated exact core code matches no rules",
            select=("FFX001",),
            ignore=(),
            expected_codes=(),
        ),
        SelectCompositionTestCase(
            description="core spelling ignore removes only core codes",
            select=("FF", "X"),
            ignore=("FFH",),
            expected_codes=("XRG001", "XDB001"),
        ),
        SelectCompositionTestCase(
            description="custom family ignore removes custom rules",
            select=("FF", "X"),
            ignore=("X",),
            expected_codes=("FFH001",),
        ),
        SelectCompositionTestCase(
            description="custom root selector includes all default-on custom namespaces",
            select=("X",),
            ignore=(),
            expected_codes=("XRG001", "XDB001"),
        ),
        SelectCompositionTestCase(
            description="core selector does not select custom rule declaring roles family",
            select=("FFR",),
            ignore=(),
            expected_codes=(),
        ),
        SelectCompositionTestCase(
            description="core root selector selects core codes only",
            select=("FF",),
            ignore=(),
            expected_codes=("FFH001",),
        ),
        SelectCompositionTestCase(
            description="custom namespace selector selects its default-on rules",
            select=("XDB",),
            ignore=(),
            expected_codes=("XDB001",),
        ),
        SelectCompositionTestCase(
            description="custom namespace prefix does not activate default-off descendant",
            select=("XDB0",),
            ignore=(),
            expected_codes=("XDB001",),
        ),
        SelectCompositionTestCase(
            description="exact custom code activates default-off rule",
            select=("XDB099",),
            ignore=(),
            expected_codes=("XDB099",),
        ),
        SelectCompositionTestCase(
            description="ignore prefix wins over exact default-off activation",
            select=("XDB099",),
            ignore=("XDB",),
            expected_codes=(),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_select_and_ignore_when_building_ruleset_then_applies_expected_composition(
    monkeypatch: pytest.MonkeyPatch,
    test_case: SelectCompositionTestCase,
) -> None:
    monkeypatch.setattr(
        loading_module,
        "CORE_RULES",
        (
            make_core_rule(code="FFH001", family=Family.HYGIENE),
            make_core_rule(code="FFH099", family=Family.HYGIENE, enabled_by_default=False),
            make_core_rule(code="XRG001", family=Family.ROLES),
            make_core_rule(code="XDB001", family=Family.ROLES),
            make_core_rule(code="XDB099", family=Family.CUSTOM, enabled_by_default=False),
        ),
    )

    ruleset: tuple[RuleSpec, ...] = build_ruleset(
        config=Config(roots=("src/pkg",), select=test_case.select, ignore=test_case.ignore)
    )

    assert tuple(rule.code for rule in ruleset) == test_case.expected_codes


@pytest.mark.parametrize(
    "test_case",
    [
        RuleSelectionTestCase(
            description="exact default-off warning does not overlap broad blocking selection",
            select=("FFH",),
            warn=("FFH099",),
            ignore=(),
            expected_blocking_codes=("FFH001",),
            expected_warning_codes=("FFH099",),
            expected_ignored_codes=(),
        ),
        RuleSelectionTestCase(
            description="warning family selection respects default-off semantics",
            select=(),
            warn=("FFH",),
            ignore=(),
            expected_blocking_codes=(),
            expected_warning_codes=("FFH001",),
            expected_ignored_codes=(),
        ),
        RuleSelectionTestCase(
            description="ignore subtracts from broad blocking selection",
            select=("FFH",),
            warn=(),
            ignore=("FFH001",),
            expected_blocking_codes=(),
            expected_warning_codes=(),
            expected_ignored_codes=("FFH001",),
        ),
        RuleSelectionTestCase(
            description="unknown valid warning selector resolves to no rules",
            select=(),
            warn=("FFX",),
            ignore=(),
            expected_blocking_codes=(),
            expected_warning_codes=(),
            expected_ignored_codes=(),
        ),
        RuleSelectionTestCase(
            description="custom warning namespace selects default-on custom rules",
            select=(),
            warn=("XDB",),
            ignore=(),
            expected_blocking_codes=(),
            expected_warning_codes=("XDB001",),
            expected_ignored_codes=(),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_policy_selectors_when_resolving_then_returns_distinct_rule_sets(
    monkeypatch: pytest.MonkeyPatch,
    test_case: RuleSelectionTestCase,
) -> None:
    monkeypatch.setattr(
        loading_module,
        "CORE_RULES",
        (
            make_core_rule(code="FFH001", family=Family.HYGIENE),
            make_core_rule(code="FFH099", family=Family.HYGIENE, enabled_by_default=False),
            make_core_rule(code="XDB001", family=Family.CUSTOM),
            make_core_rule(code="XDB099", family=Family.CUSTOM, enabled_by_default=False),
        ),
    )

    selection: RuleSelection = build_rule_selection(
        config=Config(
            roots=("src/pkg",),
            select=test_case.select,
            warn=test_case.warn,
            ignore=test_case.ignore,
        )
    )

    assert tuple(rule.code for rule in selection.blocking) == test_case.expected_blocking_codes
    assert tuple(rule.code for rule in selection.warnings) == test_case.expected_warning_codes
    assert tuple(rule.code for rule in selection.ignored) == test_case.expected_ignored_codes


@pytest.mark.parametrize(
    "test_case",
    [
        RuleSelectionErrorTestCase(
            description="one rule cannot be blocking and warning",
            select=("FFH",),
            warn=("FFH001",),
            ignore=(),
            expected_error="Rule FFH001 cannot be configured as both blocking and warning.",
        ),
        RuleSelectionErrorTestCase(
            description="one rule cannot be warning and ignored",
            select=("FFH",),
            warn=("FFH001",),
            ignore=("FFH001",),
            expected_error="Rule FFH001 cannot be configured as both warning and ignored.",
        ),
        RuleSelectionErrorTestCase(
            description="overlap errors report the first rule code deterministically",
            select=("FFH",),
            warn=("FFH",),
            ignore=(),
            expected_error="Rule FFH001 cannot be configured as both blocking and warning.",
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_overlapping_policy_tiers_when_resolving_then_raises_config_error(
    monkeypatch: pytest.MonkeyPatch,
    test_case: RuleSelectionErrorTestCase,
) -> None:
    monkeypatch.setattr(
        loading_module,
        "CORE_RULES",
        (
            make_core_rule(code="FFH002", family=Family.HYGIENE),
            make_core_rule(code="FFH001", family=Family.HYGIENE),
        ),
    )

    with pytest.raises(ConfigError) as error:
        build_rule_selection(
            config=Config(
                roots=("src/pkg",),
                select=test_case.select,
                warn=test_case.warn,
                ignore=test_case.ignore,
            )
        )

    assert str(error.value) == test_case.expected_error


@pytest.mark.parametrize(
    "test_case",
    [
        RuleSelectionErrorTestCase(
            description="native-backed core option declaration fails loudly",
            select=(),
            warn=(),
            ignore=(),
            expected_error="Native-backed core rule FFH001 cannot declare options in this release.",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_native_backed_option_declaration_when_discovering_then_rejects_it(
    monkeypatch: pytest.MonkeyPatch,
    test_case: RuleSelectionErrorTestCase,
) -> None:
    native_rule: RuleSpec = replace(
        make_core_rule(code="FFH001", family=Family.HYGIENE),
        check=None,
        options=(RuleOption.boolean(name="enabled", default=True),),
    )
    monkeypatch.setattr(loading_module, "CORE_RULES", (native_rule,))

    with pytest.raises(ConfigError) as error:
        build_catalogue(config=Config(roots=("src/pkg",)), repo_root=Path.cwd())

    assert str(error.value) == test_case.expected_error
