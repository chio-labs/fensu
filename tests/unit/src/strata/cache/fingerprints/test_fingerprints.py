"""Tests for canonical persistent cache fingerprints."""

from __future__ import annotations

from pathlib import Path
from types import MappingProxyType
from unittest.mock import Mock

import pytest

import strata.cache.fingerprints._helpers.fingerprints as fingerprint_module
from strata.cache.fingerprints._helpers.fingerprints import (
    canonical_fingerprint,
    config_fingerprint,
    custom_rules_fingerprint,
    global_fingerprint,
    implementation_fingerprint,
    ruleset_fingerprint,
    source_fingerprint,
)
from strata.cache.fingerprints.main._file_result import file_result_fingerprints
from strata.cache.fingerprints.main.build_global import build_global_fingerprint
from strata.cache.fingerprints.models import (
    CacheFingerprint,
    FileResultFingerprints,
    GlobalFingerprintBuild,
)
from strata.cache.results._helpers.serialization import file_result_to_record
from strata.cache.results.models import CachedFileResult
from strata.cache.storage.main._encode_record import encode_record
from strata.cache.storage.main._record_identity import record_content_fingerprint
from strata.cache.storage.models import CacheRecord
from strata.config.models import (
    CacheConfig,
    Config,
    EvaluationConfig,
    MemoryConfig,
    MemoryTasksConfig,
    SkillsConfig,
    ThresholdOverride,
)
from strata.rules.authoring.models import RuleSpec
from strata.rules.authoring.types import ExecutionOwner, Threshold
from strata.rules.catalog.constants import CORE_RULES
from strata.rules.catalog.main.build_ruleset import build_ruleset
from tests.unit.src.strata.cache.fingerprints._test_types import (
    CacheBlockedRulesetTestCase,
    CachePreferenceFingerprintTestCase,
    CanonicalFingerprintTestCase,
    ConfigFingerprintTestCase,
    ConfigLayoutFingerprintTestCase,
    ContractFingerprintTestCase,
    CustomRulesFingerprintTestCase,
    EvaluationFingerprintTestCase,
    FileResultFingerprintTestCase,
    GlobalFingerprintBuilderTestCase,
    GlobalFingerprintTestCase,
    GlobalRuntimeFingerprintTestCase,
    ImplementationFingerprintTestCase,
    MemoryPreferenceFingerprintTestCase,
    NativeBackendFingerprintTestCase,
    RulesetExecutionOwnerFingerprintTestCase,
    RulesetFingerprintTestCase,
    RulesetSourceReuseTestCase,
    SkillsFingerprintTestCase,
    SourceFingerprintTestCase,
    ThresholdOverrideFingerprintTestCase,
    WarningFingerprintTestCase,
    WarningModeFingerprintTestCase,
)
from tests.unit.src.strata.cache.fingerprints.helpers import (
    cached_file_result,
    config_with_statement_threshold,
    configure_package_availability,
    custom_fingerprint_rule,
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
        FileResultFingerprintTestCase(
            description="equivalent result preserves both identities",
            first_global="g" * 64,
            second_global="g" * 64,
            first_dependency_answer=False,
            second_dependency_answer=False,
            first_fault_message="missing annotation",
            second_fault_message="missing annotation",
            expected_result_equal=True,
            expected_record_equal=True,
        ),
        FileResultFingerprintTestCase(
            description="normalized dependency answer does not duplicate file-record identity",
            first_global="g" * 64,
            second_global="g" * 64,
            first_dependency_answer=False,
            second_dependency_answer=True,
            first_fault_message="missing annotation",
            second_fault_message="missing annotation",
            expected_result_equal=True,
            expected_record_equal=True,
        ),
        FileResultFingerprintTestCase(
            description="fault mutation changes integrity but not correctness inputs",
            first_global="g" * 64,
            second_global="g" * 64,
            first_dependency_answer=False,
            second_dependency_answer=False,
            first_fault_message="missing annotation",
            second_fault_message="changed diagnostic",
            expected_result_equal=False,
            expected_record_equal=False,
        ),
        FileResultFingerprintTestCase(
            description="global mutation changes correctness but not record integrity",
            first_global="g" * 64,
            second_global="h" * 64,
            first_dependency_answer=False,
            second_dependency_answer=False,
            first_fault_message="missing annotation",
            second_fault_message="missing annotation",
            expected_result_equal=False,
            expected_record_equal=True,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_file_results_when_fingerprinting_then_separates_correctness_and_integrity(
    test_case: FileResultFingerprintTestCase,
) -> None:
    first_result: CachedFileResult = cached_file_result(
        dependency_answer=test_case.first_dependency_answer,
        fault_message=test_case.first_fault_message,
    )
    second_result: CachedFileResult = cached_file_result(
        dependency_answer=test_case.second_dependency_answer,
        fault_message=test_case.second_fault_message,
    )
    first_record: CacheRecord = file_result_to_record(first_result)
    second_record: CacheRecord = file_result_to_record(second_result)
    first: FileResultFingerprints = file_result_fingerprints(
        global_fingerprint=CacheFingerprint(test_case.first_global),
        encoded=encode_record(record=first_record),
    )
    second: FileResultFingerprints = file_result_fingerprints(
        global_fingerprint=CacheFingerprint(test_case.second_global),
        encoded=encode_record(record=second_record),
    )

    assert (first.result == second.result) is test_case.expected_result_equal
    assert (first.record == second.record) is test_case.expected_record_equal
    assert first.record == record_content_fingerprint(record=first_record)
    assert len(first.result.value) == 64
    assert len(first.record.value) == 64


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
        RulesetExecutionOwnerFingerprintTestCase(
            description="execution-owner change invalidates ruleset identity",
            first_owner=ExecutionOwner.FILE,
            second_owner=ExecutionOwner.DOMAIN,
            expected_equal=False,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_execution_owner_when_fingerprinting_then_captures_owner_semantics(
    test_case: RulesetExecutionOwnerFingerprintTestCase,
) -> None:
    first_rule: RuleSpec = rule_with_message(
        "message",
        execution_owner=test_case.first_owner,
    )
    second_rule: RuleSpec = rule_with_message(
        "message",
        execution_owner=test_case.second_owner,
    )

    first: CacheFingerprint = ruleset_fingerprint((first_rule,))
    second: CacheFingerprint = ruleset_fingerprint((second_rule,))

    assert (first == second) is test_case.expected_equal


@pytest.mark.parametrize(
    "test_case",
    [
        ContractFingerprintTestCase(
            description="contract behavior change invalidates global config identity",
            first_behavior="returns-bool",
            second_behavior="returns-value",
            expected_equal=False,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_contract_behavior_change_when_fingerprinting_then_invalidates_config_identity(
    test_case: ContractFingerprintTestCase,
) -> None:
    first: CacheFingerprint = config_fingerprint(
        Config(
            roots=("src/pkg",),
            contracts=MappingProxyType({"is_*": test_case.first_behavior}),
        )
    )
    second: CacheFingerprint = config_fingerprint(
        Config(
            roots=("src/pkg",),
            contracts=MappingProxyType({"is_*": test_case.second_behavior}),
        )
    )

    assert (first == second) is test_case.expected_equal


@pytest.mark.parametrize(
    "test_case",
    [
        WarningFingerprintTestCase(
            description="warning selection change invalidates global config identity",
            first_warn=(),
            second_warn=("SFS102",),
            expected_equal=False,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_warning_selection_change_when_fingerprinting_then_invalidates_config_identity(
    test_case: WarningFingerprintTestCase,
) -> None:
    first: CacheFingerprint = config_fingerprint(
        Config(roots=("src/pkg",), warn=test_case.first_warn)
    )
    second: CacheFingerprint = config_fingerprint(
        Config(roots=("src/pkg",), warn=test_case.second_warn)
    )

    assert (first == second) is test_case.expected_equal


@pytest.mark.parametrize(
    "test_case",
    [
        SkillsFingerprintTestCase(
            description="persistent skill identity change invalidates config fingerprint",
            first_name="api",
            second_name="worker",
            expected_equal=False,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_skill_name_change_when_fingerprinting_then_invalidates_config_identity(
    test_case: SkillsFingerprintTestCase,
) -> None:
    first: CacheFingerprint = config_fingerprint(
        Config(roots=("src/pkg",), skills=SkillsConfig(name=test_case.first_name))
    )
    second: CacheFingerprint = config_fingerprint(
        Config(roots=("src/pkg",), skills=SkillsConfig(name=test_case.second_name))
    )

    assert (first == second) is test_case.expected_equal


@pytest.mark.parametrize(
    "test_case",
    [
        CachePreferenceFingerprintTestCase(
            description="cache preference does not alter diagnostic identity",
            first_enabled=True,
            second_enabled=False,
            expected_equal=True,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_cache_preferences_when_fingerprinting_then_excludes_operational_mode(
    test_case: CachePreferenceFingerprintTestCase,
) -> None:
    first: CacheFingerprint = config_fingerprint(
        Config(
            roots=("src/pkg",),
            cache=CacheConfig(enabled=test_case.first_enabled),
        )
    )
    second: CacheFingerprint = config_fingerprint(
        Config(
            roots=("src/pkg",),
            cache=CacheConfig(enabled=test_case.second_enabled),
        )
    )

    assert (first == second) is test_case.expected_equal


@pytest.mark.parametrize(
    "test_case",
    [
        MemoryPreferenceFingerprintTestCase(
            description="memory preferences do not alter diagnostic identity",
            first_enabled=False,
            second_enabled=True,
            first_archive_after_days=7,
            second_archive_after_days=30,
            expected_equal=True,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_memory_preferences_when_fingerprinting_then_excludes_operational_state(
    test_case: MemoryPreferenceFingerprintTestCase,
) -> None:
    first: CacheFingerprint = config_fingerprint(
        Config(
            roots=("src/pkg",),
            memory=MemoryConfig(
                enabled=test_case.first_enabled,
                tasks=MemoryTasksConfig(archive_after_days=test_case.first_archive_after_days),
            ),
        )
    )
    second: CacheFingerprint = config_fingerprint(
        Config(
            roots=("src/pkg",),
            memory=MemoryConfig(
                enabled=test_case.second_enabled,
                tasks=MemoryTasksConfig(archive_after_days=test_case.second_archive_after_days),
            ),
        )
    )

    assert (first == second) is test_case.expected_equal


@pytest.mark.parametrize(
    "test_case",
    [
        EvaluationFingerprintTestCase(
            description="evaluation selection change invalidates global config identity",
            first_include=("src/pkg/new/**",),
            second_include=("src/pkg/**",),
            expected_equal=False,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_evaluation_selection_when_fingerprinting_then_changes_config_identity(
    test_case: EvaluationFingerprintTestCase,
) -> None:
    first: CacheFingerprint = config_fingerprint(
        Config(
            roots=("src/pkg",),
            evaluation=EvaluationConfig(include=test_case.first_include),
        )
    )
    second: CacheFingerprint = config_fingerprint(
        Config(
            roots=("src/pkg",),
            evaluation=EvaluationConfig(include=test_case.second_include),
        )
    )

    assert (first == second) is test_case.expected_equal


@pytest.mark.parametrize(
    "test_case",
    [
        ThresholdOverrideFingerprintTestCase(
            description="threshold override declaration order changes semantic identity",
            expected_equal=False,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_threshold_overrides_when_fingerprinting_then_preserves_declaration_order(
    test_case: ThresholdOverrideFingerprintTestCase,
) -> None:
    first_override: ThresholdOverride = ThresholdOverride(
        paths=("src/pkg/**/*.py",),
        thresholds=MappingProxyType({Threshold.MAX_ROLE_DEPTH: 2}),
        reason="first",
    )
    second_override: ThresholdOverride = ThresholdOverride(
        paths=("src/pkg/**/main/*.py",),
        thresholds=MappingProxyType({Threshold.MAX_MAIN_CONTAINER_MODULES: 30}),
        reason="second",
    )
    first_order: tuple[ThresholdOverride, ...] = (first_override, second_override)
    second_order: tuple[ThresholdOverride, ...] = (second_override, first_override)

    first: CacheFingerprint = config_fingerprint(
        Config(roots=("src/pkg",), threshold_overrides=first_order)
    )
    second: CacheFingerprint = config_fingerprint(
        Config(roots=("src/pkg",), threshold_overrides=second_order)
    )

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
        ImplementationFingerprintTestCase(
            description="orphan bytecode mutation changes implementation identity",
            first="first bytecode",
            second="second bytecode",
            expected_equal=False,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_orphan_bytecode_when_fingerprinting_then_captures_executable_changes(
    tmp_path: Path,
    test_case: ImplementationFingerprintTestCase,
) -> None:
    package_root: Path = tmp_path / "strata"
    package_root.mkdir()
    (package_root / "__init__.py").write_text("", encoding="utf-8")
    bytecode: Path = package_root / "__pycache__/module.cpython-312.pyc"
    bytecode.parent.mkdir()
    bytecode.write_text(test_case.first, encoding="utf-8")
    first: CacheFingerprint = implementation_fingerprint(package_root=package_root)
    bytecode.write_text(test_case.second, encoding="utf-8")
    second: CacheFingerprint = implementation_fingerprint(package_root=package_root)

    assert (first == second) is test_case.expected_equal


@pytest.mark.parametrize(
    "test_case",
    [
        ImplementationFingerprintTestCase(
            description="native module mutation changes implementation identity",
            first="first native module",
            second="second native module",
            expected_equal=False,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_native_module_when_fingerprinting_then_captures_executable_changes(
    tmp_path: Path,
    test_case: ImplementationFingerprintTestCase,
) -> None:
    package_root: Path = tmp_path / "strata"
    package_root.mkdir()
    (package_root / "__init__.py").write_text("", encoding="utf-8")
    native_module: Path = package_root / "module.so"
    native_module.write_text(test_case.first, encoding="utf-8")
    first: CacheFingerprint = implementation_fingerprint(package_root=package_root)
    native_module.write_text(test_case.second, encoding="utf-8")
    second: CacheFingerprint = implementation_fingerprint(package_root=package_root)

    assert (first == second) is test_case.expected_equal


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
        RulesetSourceReuseTestCase(
            description="rules sharing one module hash its source once",
            expected_source_reads=1,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_rules_from_same_module_when_fingerprinting_then_reuses_source_identity(
    monkeypatch: pytest.MonkeyPatch,
    test_case: RulesetSourceReuseTestCase,
) -> None:
    source_fingerprint_reader: Mock = Mock(wraps=fingerprint_module._source_path_fingerprint)
    monkeypatch.setattr(
        fingerprint_module,
        "_source_path_fingerprint",
        source_fingerprint_reader,
    )
    ruleset: tuple[RuleSpec, ...] = (
        rule_with_message("first message"),
        rule_with_message("second message"),
    )

    _ = ruleset_fingerprint(ruleset)

    assert source_fingerprint_reader.call_count == test_case.expected_source_reads


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
    first: CacheFingerprint = ruleset_fingerprint(build_ruleset(config=config, repo_root=tmp_path))
    write_custom_rule(path=rule_path, returns_fault=True)
    second: CacheFingerprint = ruleset_fingerprint(build_ruleset(config=config, repo_root=tmp_path))

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
        custom_rules=common,
        native_backend_version="0.1.0",
        strata_version=test_case.first_version,
    )
    second: CacheFingerprint = global_fingerprint(
        implementation=common,
        config=common,
        ruleset=common,
        custom_rules=common,
        native_backend_version="0.1.0",
        strata_version=test_case.second_version,
    )

    assert (first == second) is test_case.expected_equal


@pytest.mark.parametrize(
    "test_case",
    [
        NativeBackendFingerprintTestCase(
            description="native extension version change invalidates global identity",
            first_backend_version="0.1.0",
            second_backend_version="0.2.0",
            expected_equal=False,
        ),
        NativeBackendFingerprintTestCase(
            description="matching native extension versions share the global identity",
            first_backend_version="0.1.0",
            second_backend_version="0.1.0",
            expected_equal=True,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_native_extension_version_when_fingerprinting_then_captures_backend_contract(
    test_case: NativeBackendFingerprintTestCase,
) -> None:
    common: CacheFingerprint = source_fingerprint(b"common")

    first: CacheFingerprint = global_fingerprint(
        implementation=common,
        config=common,
        ruleset=common,
        custom_rules=common,
        native_backend_version=test_case.first_backend_version,
        strata_version="1.0.0",
    )
    second: CacheFingerprint = global_fingerprint(
        implementation=common,
        config=common,
        ruleset=common,
        custom_rules=common,
        native_backend_version=test_case.second_backend_version,
        strata_version="1.0.0",
    )

    assert (first == second) is test_case.expected_equal


@pytest.mark.parametrize(
    "test_case",
    [
        WarningModeFingerprintTestCase(
            description="plain and warning modes have distinct identities with no warning rules",
            first_enabled=False,
            second_enabled=True,
            expected_equal=False,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_warning_mode_state_when_fingerprinting_then_captures_invocation_identity(
    test_case: WarningModeFingerprintTestCase,
) -> None:
    common: CacheFingerprint = source_fingerprint(b"common")

    first: CacheFingerprint = global_fingerprint(
        implementation=common,
        config=common,
        ruleset=common,
        custom_rules=common,
        native_backend_version="0.1.0",
        warnings_enabled=test_case.first_enabled,
        strata_version="1.0.0",
    )
    second: CacheFingerprint = global_fingerprint(
        implementation=common,
        config=common,
        ruleset=common,
        custom_rules=common,
        native_backend_version="0.1.0",
        warnings_enabled=test_case.second_enabled,
        strata_version="1.0.0",
    )

    assert (first == second) is test_case.expected_equal


@pytest.mark.parametrize(
    "test_case",
    [
        GlobalRuntimeFingerprintTestCase(
            description="Python implementation change invalidates global identity",
            first_python_implementation="CPython",
            second_python_implementation="PyPy",
            first_contract_version=1,
            second_contract_version=1,
            expected_equal=False,
        ),
        GlobalRuntimeFingerprintTestCase(
            description="evaluation contract change invalidates global identity",
            first_python_implementation="CPython",
            second_python_implementation="CPython",
            first_contract_version=1,
            second_contract_version=2,
            expected_equal=False,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_runtime_semantics_when_fingerprinting_then_captures_contract_identity(
    monkeypatch: pytest.MonkeyPatch,
    test_case: GlobalRuntimeFingerprintTestCase,
) -> None:
    common: CacheFingerprint = source_fingerprint(b"common")
    monkeypatch.setattr(
        fingerprint_module.platform,
        "python_implementation",
        lambda: test_case.first_python_implementation,
    )
    monkeypatch.setattr(
        fingerprint_module,
        "EVALUATION_FINGERPRINT_CONTRACT_VERSION",
        test_case.first_contract_version,
    )
    first: CacheFingerprint = global_fingerprint(
        implementation=common,
        config=common,
        ruleset=common,
        custom_rules=common,
        native_backend_version="0.1.0",
        strata_version="1.0.0",
    )
    monkeypatch.setattr(
        fingerprint_module.platform,
        "python_implementation",
        lambda: test_case.second_python_implementation,
    )
    monkeypatch.setattr(
        fingerprint_module,
        "EVALUATION_FINGERPRINT_CONTRACT_VERSION",
        test_case.second_contract_version,
    )
    second: CacheFingerprint = global_fingerprint(
        implementation=common,
        config=common,
        ruleset=common,
        custom_rules=common,
        native_backend_version="0.1.0",
        strata_version="1.0.0",
    )

    assert (first == second) is test_case.expected_equal


@pytest.mark.parametrize(
    "test_case",
    [
        GlobalFingerprintBuilderTestCase(
            description="loaded source package builds repeatable complete identity",
            package_available=True,
            source_available=True,
            complete_source=True,
            expected_available=True,
            expected_implementation_scans=2,
        ),
        GlobalFingerprintBuilderTestCase(
            description="unavailable package conservatively disables caching",
            package_available=False,
            source_available=False,
            complete_source=False,
            expected_available=False,
            expected_implementation_scans=0,
        ),
        GlobalFingerprintBuilderTestCase(
            description="source-less package conservatively disables caching",
            package_available=True,
            source_available=False,
            complete_source=False,
            expected_available=False,
            expected_implementation_scans=0,
        ),
        GlobalFingerprintBuilderTestCase(
            description="orphan bytecode participates in complete implementation identity",
            package_available=True,
            source_available=True,
            complete_source=False,
            expected_available=True,
            expected_implementation_scans=2,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_loaded_package_when_building_global_then_requires_complete_source_identity(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: GlobalFingerprintBuilderTestCase,
) -> None:
    configure_package_availability(
        monkeypatch=monkeypatch,
        available=test_case.package_available,
        source_available=test_case.source_available,
        complete_source=test_case.complete_source,
        empty_package_root=tmp_path / "strata",
    )
    implementation_paths: Mock = Mock(wraps=fingerprint_module._implementation_paths)
    monkeypatch.setattr(fingerprint_module, "_implementation_paths", implementation_paths)

    first: GlobalFingerprintBuild = build_global_fingerprint(
        config=Config(roots=()), ruleset=(), repo_root=tmp_path
    )
    second: GlobalFingerprintBuild = build_global_fingerprint(
        config=Config(roots=()), ruleset=(), repo_root=tmp_path
    )

    assert (first.fingerprint is not None) is test_case.expected_available
    assert (first.disabled_reason is None) is test_case.expected_available
    assert implementation_paths.call_count == test_case.expected_implementation_scans
    assert first == second
    assert not (tmp_path / ".strata").exists()


@pytest.mark.parametrize(
    "test_case",
    [
        CustomRulesFingerprintTestCase(
            description="rule helper file edit changes the custom implementation identity",
            first_helper_source="LIMIT: int = 1\n",
            second_helper_source="LIMIT: int = 2\n",
            expected_equal=False,
            expected_missing_none=True,
        ),
        CustomRulesFingerprintTestCase(
            description="unchanged rule sources keep a stable custom implementation identity",
            first_helper_source="LIMIT: int = 1\n",
            second_helper_source="LIMIT: int = 1\n",
            expected_equal=True,
            expected_missing_none=True,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_rule_path_sources_when_fingerprinting_then_tracks_every_file(
    tmp_path: Path,
    test_case: CustomRulesFingerprintTestCase,
) -> None:
    rules_dir: Path = tmp_path / "rules"
    rules_dir.mkdir()
    (rules_dir / "custom.py").write_text("RULE: int = 0\n", encoding="utf-8")
    helper: Path = rules_dir / "helper.py"
    helper.write_text(test_case.first_helper_source, encoding="utf-8")
    config: Config = Config(roots=(), rule_paths=("rules",))

    first: CacheFingerprint | None = custom_rules_fingerprint(config=config, repo_root=tmp_path)
    helper.write_text(test_case.second_helper_source, encoding="utf-8")
    second: CacheFingerprint | None = custom_rules_fingerprint(config=config, repo_root=tmp_path)
    missing: CacheFingerprint | None = custom_rules_fingerprint(
        config=Config(roots=(), rule_paths=("absent",)),
        repo_root=tmp_path,
    )

    assert first is not None
    assert second is not None
    assert (first == second) is test_case.expected_equal
    assert (missing is None) is test_case.expected_missing_none


@pytest.mark.parametrize(
    "test_case",
    [
        CacheBlockedRulesetTestCase(
            description="custom-only non-cacheable ruleset disables caching entirely",
            cacheable=False,
            include_core=False,
            expected_blocked=True,
            expected_reason_fragment="no cacheable rules are selected",
        ),
        CacheBlockedRulesetTestCase(
            description="declared cacheable custom rule does not block the identity",
            cacheable=True,
            include_core=False,
            expected_blocked=False,
            expected_reason_fragment="no cacheable rules are selected",
        ),
        CacheBlockedRulesetTestCase(
            description="mixed core and non-cacheable custom ruleset keeps the identity",
            cacheable=False,
            include_core=True,
            expected_blocked=False,
            expected_reason_fragment="no cacheable rules are selected",
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_custom_ruleset_when_building_global_then_names_blocking_rules(
    tmp_path: Path,
    test_case: CacheBlockedRulesetTestCase,
) -> None:
    core_rules: tuple[RuleSpec, ...] = {False: (), True: CORE_RULES[:1]}[test_case.include_core]
    ruleset: tuple[RuleSpec, ...] = (
        *core_rules,
        custom_fingerprint_rule(code="XFP001", cacheable=test_case.cacheable),
    )

    build: GlobalFingerprintBuild = build_global_fingerprint(
        config=Config(roots=()),
        ruleset=ruleset,
        repo_root=tmp_path,
    )

    blocked: bool = (
        build.disabled_reason is not None
        and test_case.expected_reason_fragment in build.disabled_reason
    )
    assert blocked is test_case.expected_blocked
