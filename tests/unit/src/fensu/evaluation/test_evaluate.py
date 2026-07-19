"""Tests for evaluating fake rules over discovered files."""

from __future__ import annotations

from pathlib import Path

import pytest

from fensu.config.models import Config, ThresholdOverride
from fensu.discovery.main.position import position_facts
from fensu.discovery.main.route import families_for_scope
from fensu.discovery.models import PositionFacts, ScopedFile
from fensu.evaluation._helpers.parsing import parse_scoped_file
from fensu.evaluation.exceptions import ModuleUnavailableError
from fensu.evaluation.main.evaluate import evaluate
from fensu.evaluation.models import EvaluationResult, ParsedModule, ThresholdOverrideUse
from fensu.rules.authoring.types import ExecutionOwner, Family, Threshold
from tests.unit.src.fensu.evaluation._test_types import (
    AnalysisContextTestCase,
    AstHelperContextTestCase,
    ContextPropertyTestCase,
    ContextThresholdTestCase,
    EmptyEvaluationTestCase,
    EvaluationFaultTestCase,
    EvaluationOperationTestCase,
    ExecutionOwnerEvaluationTestCase,
    FaultFactoryTestCase,
    ModuleGateTestCase,
    ProjectDependencyEvaluationTestCase,
    ThresholdObservationTestCase,
)
from tests.unit.src.fensu.evaluation.helpers import (
    discover_test_tree,
    make_analysis_context_rule,
    make_config_with_entry_threshold,
    make_context_ast_helper_rule,
    make_context_property_rule,
    make_default_invocation_rule,
    make_fault_factory_rule,
    make_loop_rule,
    make_node_count_rule,
    make_none_location_rule,
    make_owned_invocation_rule,
    make_position_rule,
    make_project_dependency_rule,
    make_runtime_fault_rule,
    make_static_fault_rule,
    make_threshold_rule,
    make_undeclared_module_rule,
    write_sources,
)


@pytest.mark.parametrize(
    "test_case",
    [
        ProjectDependencyEvaluationTestCase(
            description="project query dependencies are returned by evaluation",
            source="value: int = 1\n",
            expected_dependency_name="missing.py",
            expected_dependency_kind="is_file",
            expected_dependency_answer=False,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_project_query_when_evaluating_then_returns_observed_dependency(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: ProjectDependencyEvaluationTestCase,
) -> None:
    write_sources(
        repo_root=tmp_path,
        files=(("src/pkg/config/core/models.py", test_case.source),),
    )
    monkeypatch.chdir(tmp_path)
    config: Config = Config(roots=("src/pkg",))

    result: EvaluationResult = evaluate(
        tree=discover_test_tree(config=config),
        ruleset=(make_project_dependency_rule(),),
        config=config,
    )

    assert tuple(item.requester.name for item in result.dependencies) == ("models.py",)
    assert tuple(item.query_path.name for item in result.dependencies) == (
        test_case.expected_dependency_name,
    )
    assert tuple(item.kind for item in result.dependencies) == (test_case.expected_dependency_kind,)
    assert tuple(item.answer for item in result.dependencies) == (
        test_case.expected_dependency_answer,
    )
    assert tuple(item.path.name for item in result.file_evaluations) == ("models.py",)
    assert result.file_evaluations[0].dependencies == result.dependencies


@pytest.mark.parametrize(
    "test_case",
    [
        AnalysisContextTestCase(
            description="public analysis zones create backend-neutral fault locations",
            source="def run() -> None:\n    call()\n",
            expected_line=2,
            expected_column=4,
            expected_message="call()|1|Expr",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_analysis_context_when_reporting_handle_then_fault_uses_source_location(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: AnalysisContextTestCase,
) -> None:
    write_sources(
        repo_root=tmp_path,
        files=(("src/pkg/config/core/main/load.py", test_case.source),),
    )
    monkeypatch.chdir(tmp_path)

    result: EvaluationResult = evaluate(
        tree=discover_test_tree(config=Config(roots=("src/pkg",))),
        ruleset=(make_analysis_context_rule(),),
        config=Config(roots=("src/pkg",)),
    )

    assert result.faults[0].line == test_case.expected_line
    assert result.faults[0].column == test_case.expected_column
    assert result.faults[0].message == test_case.expected_message


@pytest.mark.parametrize(
    "test_case",
    [
        EvaluationOperationTestCase(
            description="prewarm avoids strict reparsing while position and routing run once",
            files=(
                ("src/pkg/config/core/models.py", "value: int = 1\n"),
                ("src/pkg/config/core/types.py", "from typing import TypeAlias\n"),
            ),
            expected_parse_count=0,
            expected_position_count=2,
            expected_routing_count=2,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_multiple_rules_when_evaluating_then_file_facts_are_computed_once(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: EvaluationOperationTestCase,
) -> None:
    write_sources(repo_root=tmp_path, files=test_case.files)
    monkeypatch.chdir(tmp_path)
    config: Config = Config(roots=("src/pkg",))
    parse_counts: list[int] = [0]
    position_counts: list[int] = [0]
    routing_counts: list[int] = [0]

    def count_parse(scoped_file: ScopedFile) -> ParsedModule:
        parse_counts[0] += 1
        return parse_scoped_file(scoped_file=scoped_file)

    def count_position(scoped_file: ScopedFile) -> PositionFacts:
        position_counts[0] += 1
        return position_facts(scoped_file)

    def count_routing(*, scoped_file: ScopedFile) -> frozenset[Family]:
        routing_counts[0] += 1
        return families_for_scope(scoped_file=scoped_file)

    monkeypatch.setattr(
        "fensu.evaluation._helpers.project_analysis.parse_scoped_file",
        count_parse,
    )
    monkeypatch.setattr("fensu.evaluation._helpers.parsing.position_facts", count_position)
    monkeypatch.setattr(
        "fensu.evaluation._helpers.file_evaluation.families_for_scope",
        count_routing,
    )

    _result: EvaluationResult = evaluate(
        tree=discover_test_tree(config=config),
        ruleset=(make_runtime_fault_rule(), make_runtime_fault_rule()),
        config=config,
    )

    assert parse_counts[0] == test_case.expected_parse_count
    assert position_counts[0] == test_case.expected_position_count
    assert routing_counts[0] == test_case.expected_routing_count


@pytest.mark.parametrize(
    "test_case",
    [
        ExecutionOwnerEvaluationTestCase(
            description="omitted ownership invokes the rule for every applicable file",
            files=(
                ("src/pkg/alpha/main/a.py", "VALUE: int = 1\n"),
                ("src/pkg/alpha/models.py", "VALUE: int = 2\n"),
            ),
            execution_owner=ExecutionOwner.FILE,
            expected_invocation_paths=(
                "src/pkg/alpha/main/a.py",
                "src/pkg/alpha/models.py",
            ),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_omitted_owner_when_evaluating_then_invokes_every_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: ExecutionOwnerEvaluationTestCase,
) -> None:
    write_sources(repo_root=tmp_path, files=test_case.files)
    monkeypatch.chdir(tmp_path)
    config: Config = Config(roots=("src/pkg",))
    invocations: list[Path] = []

    _result: EvaluationResult = evaluate(
        tree=discover_test_tree(config=config),
        ruleset=(make_default_invocation_rule(invocations=invocations),),
        config=config,
    )

    assert tuple(path.relative_to(tmp_path).as_posix() for path in invocations) == (
        test_case.expected_invocation_paths
    )


@pytest.mark.parametrize(
    "test_case",
    [
        ExecutionOwnerEvaluationTestCase(
            description="package ownership invokes one direct-module anchor per package",
            files=(
                ("src/pkg/alpha/__init__.py", ""),
                ("src/pkg/alpha/z.py", "VALUE: int = 1\n"),
                ("src/pkg/beta/z.py", "VALUE: int = 2\n"),
                ("src/pkg/beta/a.py", "VALUE: int = 3\n"),
            ),
            execution_owner=ExecutionOwner.PACKAGE,
            expected_invocation_paths=(
                "src/pkg/alpha/__init__.py",
                "src/pkg/beta/a.py",
            ),
        ),
        ExecutionOwnerEvaluationTestCase(
            description="domain ownership invokes one deterministic anchor per domain",
            files=(
                ("src/pkg/alpha/__init__.py", ""),
                ("src/pkg/alpha/models.py", "VALUE: int = 1\n"),
                ("src/pkg/beta/main/z.py", "VALUE: int = 2\n"),
            ),
            execution_owner=ExecutionOwner.DOMAIN,
            expected_invocation_paths=(
                "src/pkg/alpha/__init__.py",
                "src/pkg/beta/main/z.py",
            ),
        ),
        ExecutionOwnerEvaluationTestCase(
            description="leaf ownership invokes one anchor per domain location",
            files=(
                ("src/pkg/alpha/__init__.py", ""),
                ("src/pkg/alpha/models.py", "VALUE: int = 1\n"),
                ("src/pkg/alpha/red/__init__.py", ""),
                ("src/pkg/alpha/red/main/z.py", "VALUE: int = 2\n"),
                ("src/pkg/beta/models.py", "VALUE: int = 3\n"),
                ("src/pkg/gamma/classes/a.py", "VALUE: int = 4\n"),
                ("src/pkg/gamma/constants.py", "VALUE: int = 5\n"),
            ),
            execution_owner=ExecutionOwner.LEAF,
            expected_invocation_paths=(
                "src/pkg/alpha/__init__.py",
                "src/pkg/alpha/red/__init__.py",
                "src/pkg/beta/models.py",
                "src/pkg/gamma/constants.py",
            ),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_broader_owner_when_evaluating_then_invokes_one_anchor_per_owner(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: ExecutionOwnerEvaluationTestCase,
) -> None:
    write_sources(repo_root=tmp_path, files=test_case.files)
    monkeypatch.chdir(tmp_path)
    config: Config = Config(roots=("src/pkg",))
    invocations: list[Path] = []

    _result: EvaluationResult = evaluate(
        tree=discover_test_tree(config=config),
        ruleset=(
            make_owned_invocation_rule(
                invocations=invocations,
                execution_owner=test_case.execution_owner,
            ),
        ),
        config=config,
    )

    assert tuple(path.relative_to(tmp_path).as_posix() for path in invocations) == (
        test_case.expected_invocation_paths
    )


@pytest.mark.parametrize(
    "test_case",
    [
        EvaluationFaultTestCase(
            description="rule using shared node index reports all calls",
            files=(
                (
                    "src/pkg/config/core/main/load.py",
                    "def run() -> None:\n    one()\n    two()\n",
                ),
            ),
            expected_fault_codes=("XEV001", "XEV001"),
            expected_fault_lines=(2, 3),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_ruleset_when_evaluating_then_rule_sees_shared_node_index(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: EvaluationFaultTestCase,
) -> None:
    write_sources(repo_root=tmp_path, files=test_case.files)
    monkeypatch.chdir(tmp_path)
    config: Config = Config(roots=("src/pkg",))

    result: EvaluationResult = evaluate(
        tree=discover_test_tree(config=config),
        ruleset=(make_node_count_rule(),),
        config=config,
    )

    assert tuple(fault.code for fault in result.faults) == test_case.expected_fault_codes
    assert tuple(fault.line for fault in result.faults) == test_case.expected_fault_lines


@pytest.mark.parametrize(
    "test_case",
    [
        EmptyEvaluationTestCase(
            description="empty ruleset returns no faults",
            files=(("src/pkg/config/core/models.py", "x: int = 1\n"),),
            expected_fault_count=0,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_empty_ruleset_when_evaluating_then_returns_no_faults(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: EmptyEvaluationTestCase,
) -> None:
    write_sources(repo_root=tmp_path, files=test_case.files)
    monkeypatch.chdir(tmp_path)
    config: Config = Config(roots=("src/pkg",))

    result: EvaluationResult = evaluate(
        tree=discover_test_tree(config=config),
        ruleset=(),
        config=config,
    )

    assert len(result.faults) == test_case.expected_fault_count


@pytest.mark.parametrize(
    "test_case",
    [
        EmptyEvaluationTestCase(
            description="runtime-only rule skips test-scoped files",
            files=(("tests/unit/src/pkg/test_example.py", "assert True\n"),),
            expected_fault_count=0,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_runtime_rule_when_evaluating_test_scope_then_rule_is_not_executed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: EmptyEvaluationTestCase,
) -> None:
    write_sources(repo_root=tmp_path, files=test_case.files)
    monkeypatch.chdir(tmp_path)
    config: Config = Config(roots=(), tests=("tests",))

    result: EvaluationResult = evaluate(
        tree=discover_test_tree(config=config),
        ruleset=(make_runtime_fault_rule(),),
        config=config,
    )

    assert len(result.faults) == test_case.expected_fault_count


@pytest.mark.parametrize(
    "test_case",
    [
        ContextPropertyTestCase(
            description="context exposes path root source and relative parts",
            file_path="src/pkg/config/core/models.py",
            source="value: int = 1\n",
            expected_message_prefix="models.py|",
            expected_message_suffix="|config/core/models.py",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_context_when_reading_properties_then_reports_expected_file_facts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: ContextPropertyTestCase,
) -> None:
    write_sources(repo_root=tmp_path, files=((test_case.file_path, test_case.source),))
    monkeypatch.chdir(tmp_path)
    config: Config = Config(roots=("src/pkg",))

    result: EvaluationResult = evaluate(
        tree=discover_test_tree(config=config),
        ruleset=(make_context_property_rule(),),
        config=config,
    )

    assert result.faults[0].message.startswith(test_case.expected_message_prefix)
    assert result.faults[0].message.endswith(test_case.expected_message_suffix)


@pytest.mark.parametrize(
    "test_case",
    [
        FaultFactoryTestCase(
            description="fault factory uses defaults and explicit overrides",
            source="value: int = 1\n",
            expected_messages=("rule message", "custom message"),
            expected_remediations=("rule remediation", "custom remediation"),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_context_when_creating_faults_then_defaults_and_overrides_are_applied(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: FaultFactoryTestCase,
) -> None:
    write_sources(repo_root=tmp_path, files=(("src/pkg/config/core/models.py", test_case.source),))
    monkeypatch.chdir(tmp_path)
    config: Config = Config(roots=("src/pkg",))

    result: EvaluationResult = evaluate(
        tree=discover_test_tree(config=config),
        ruleset=(make_fault_factory_rule(),),
        config=config,
    )

    assert tuple(fault.message for fault in result.faults) == test_case.expected_messages
    assert tuple(fault.remediation for fault in result.faults) == test_case.expected_remediations


@pytest.mark.parametrize(
    "test_case",
    [
        ContextThresholdTestCase(
            description="role threshold override is used for main files",
            file_path="src/pkg/config/core/main/load.py",
            threshold=Threshold.MAX_STATEMENTS,
            expected_threshold=30,
        ),
        ContextThresholdTestCase(
            description="global threshold is used when role has no override",
            file_path="src/pkg/config/core/_helpers/load.py",
            threshold=Threshold.MAX_STATEMENTS,
            expected_threshold=40,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_context_when_reading_threshold_then_returns_role_or_global_value(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: ContextThresholdTestCase,
) -> None:
    write_sources(repo_root=tmp_path, files=((test_case.file_path, "x: int = 1\n"),))
    monkeypatch.chdir(tmp_path)
    config: Config = make_config_with_entry_threshold()

    result: EvaluationResult = evaluate(
        tree=discover_test_tree(config=config),
        ruleset=(make_threshold_rule(threshold=test_case.threshold),),
        config=config,
    )

    assert result.faults[0].message == str(test_case.expected_threshold)


@pytest.mark.parametrize(
    "test_case",
    [
        ThresholdObservationTestCase(
            description=f"records actual use of {threshold.value}",
            threshold=threshold,
            expected_value=99,
            expected_pattern="src/pkg/**/*.py",
        )
        for threshold in Threshold
    ],
    ids=lambda case: case.description,
)
def test_given_matching_override_when_rule_reads_any_threshold_then_records_resolution(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: ThresholdObservationTestCase,
) -> None:
    file_path: str = "src/pkg/config/_helpers/load.py"
    write_sources(repo_root=tmp_path, files=((file_path, "x: int = 1\n"),))
    monkeypatch.chdir(tmp_path)
    config: Config = Config(
        roots=("src/pkg",),
        threshold_overrides=(
            ThresholdOverride(
                paths=(test_case.expected_pattern,),
                thresholds={test_case.threshold: test_case.expected_value},
                reason="Exhaustive threshold observation.",
            ),
        ),
    )

    result: EvaluationResult = evaluate(
        tree=discover_test_tree(config=config),
        ruleset=(make_threshold_rule(threshold=test_case.threshold),),
        config=config,
    )
    use: ThresholdOverrideUse = result.threshold_override_uses[0]

    assert len(result.threshold_override_uses) == 1
    assert use.threshold is test_case.threshold
    assert use.effective_value == test_case.expected_value
    assert use.matched_pattern == test_case.expected_pattern
    assert use.repository_path == file_path


@pytest.mark.parametrize(
    "test_case",
    [
        EvaluationFaultTestCase(
            description="position helpers reflect current file",
            files=(
                (
                    "src/pkg/config/core/main/load.py",
                    "x: int = 1\n",
                ),
            ),
            expected_fault_codes=("XPO001",),
            expected_fault_lines=(1,),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_context_when_reading_position_then_reports_current_file_facts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: EvaluationFaultTestCase,
) -> None:
    write_sources(repo_root=tmp_path, files=test_case.files)
    monkeypatch.chdir(tmp_path)
    config: Config = Config(roots=("src/pkg",))

    result: EvaluationResult = evaluate(
        tree=discover_test_tree(config=config),
        ruleset=(make_position_rule(),),
        config=config,
    )

    assert tuple(fault.code for fault in result.faults) == test_case.expected_fault_codes
    assert tuple(fault.line for fault in result.faults) == test_case.expected_fault_lines
    assert result.faults[0].message == "config:core:main:True"


@pytest.mark.parametrize(
    "test_case",
    [
        EvaluationFaultTestCase(
            description="inside loop helper finds loop-contained call",
            files=(
                (
                    "src/pkg/config/core/main/load.py",
                    "def run() -> None:\n    outside()\n    for item in []:\n        inside()\n",
                ),
            ),
            expected_fault_codes=("XLP001",),
            expected_fault_lines=(4,),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_context_when_checking_loop_membership_then_reports_only_loop_calls(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: EvaluationFaultTestCase,
) -> None:
    write_sources(repo_root=tmp_path, files=test_case.files)
    monkeypatch.chdir(tmp_path)
    config: Config = Config(roots=("src/pkg",))

    result: EvaluationResult = evaluate(
        tree=discover_test_tree(config=config),
        ruleset=(make_loop_rule(),),
        config=config,
    )

    assert tuple(fault.code for fault in result.faults) == test_case.expected_fault_codes
    assert tuple(fault.line for fault in result.faults) == test_case.expected_fault_lines
    assert result.faults[0].message == "inside"


@pytest.mark.parametrize(
    "test_case",
    [
        AstHelperContextTestCase(
            description="context ast helpers expose base name body functions and missing node buckets",
            files=(
                (
                    "src/pkg/config/core/main/load.py",
                    '"doc"\ndef run(value: int) -> None:\n    svc.client.call(value)\n',
                ),
            ),
            expected_fault_codes=("XAH001",),
            expected_fault_lines=(2,),
            expected_message="svc|1|0|value",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_context_when_reading_ast_helpers_then_reports_expected_facts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: AstHelperContextTestCase,
) -> None:
    write_sources(repo_root=tmp_path, files=test_case.files)
    monkeypatch.chdir(tmp_path)
    config: Config = Config(roots=("src/pkg",))

    result: EvaluationResult = evaluate(
        tree=discover_test_tree(config=config),
        ruleset=(make_context_ast_helper_rule(),),
        config=config,
    )

    assert tuple(fault.code for fault in result.faults) == test_case.expected_fault_codes
    assert tuple(fault.line for fault in result.faults) == test_case.expected_fault_lines
    assert result.faults[0].message == test_case.expected_message


@pytest.mark.parametrize(
    "test_case",
    [
        EvaluationFaultTestCase(
            description="faults are sorted by path line column and code",
            files=(
                ("src/pkg/b.py", "x: int = 1\n"),
                ("src/pkg/a.py", "x: int = 1\n"),
            ),
            expected_fault_codes=("XNO001", "XAA001", "XBB001", "XNO001", "XAA001", "XBB001"),
            expected_fault_lines=(None, 1, 2, None, 1, 2),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_unsorted_faults_when_evaluating_then_returns_stable_sorted_faults(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: EvaluationFaultTestCase,
) -> None:
    write_sources(repo_root=tmp_path, files=test_case.files)
    monkeypatch.chdir(tmp_path)
    config: Config = Config(roots=("src/pkg",))

    result: EvaluationResult = evaluate(
        tree=discover_test_tree(config=config),
        ruleset=(
            make_none_location_rule(),
            make_static_fault_rule(code="XBB001", line=2, message="b"),
            make_static_fault_rule(code="XAA001", line=1, message="a"),
        ),
        config=config,
    )

    assert tuple(fault.code for fault in result.faults) == test_case.expected_fault_codes
    assert tuple(fault.line for fault in result.faults) == test_case.expected_fault_lines
    assert result.faults[0].line is None
    assert result.faults[0].column is None
    assert tuple(fault.path.name for fault in result.faults) == (
        "a.py",
        "a.py",
        "a.py",
        "b.py",
        "b.py",
        "b.py",
    )


@pytest.mark.parametrize(
    "test_case",
    [
        ModuleGateTestCase(
            description="undeclared module read fails loud instead of parsing",
            files=(("src/pkg/models.py", "value: int = 1\n"),),
            expected_error_type=ModuleUnavailableError,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_module_free_declaration_when_rule_reads_module_then_raises(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: ModuleGateTestCase,
) -> None:
    write_sources(repo_root=tmp_path, files=test_case.files)
    monkeypatch.chdir(tmp_path)
    config: Config = Config(roots=("src/pkg",))

    with pytest.raises(test_case.expected_error_type):
        _ = evaluate(
            tree=discover_test_tree(config=config),
            ruleset=(make_undeclared_module_rule(),),
            config=config,
        )
