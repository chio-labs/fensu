"""Native-backend operation-count invariants proving lazy CPython parsing."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

strata_facts: Any = pytest.importorskip("strata_facts")

from scripts.perfcorpus.main.generate_corpus import generate_corpus  # noqa: E402
from scripts.perfcorpus.models import CorpusSpec  # noqa: E402
from strata.analysis.constants import FACT_BACKEND_ENV_VARIABLE  # noqa: E402
from strata.analysis.types import FactBackend  # noqa: E402
from strata.instrumentation.constants import (  # noqa: E402
    FRESH_EVALUATION_OPERATION,
    NATIVE_PARSE_OPERATION,
    PARSE_OPERATION,
)
from tests.integration.src.strata.instrumentation.classes._test_types import (  # noqa: E402
    NativeEditCountsTestCase,
    NativeUncachedCountsTestCase,
)
from tests.integration.src.strata.instrumentation.classes.helpers import (  # noqa: E402
    appended_module_constant,
    counted_check,
    python_file_count,
)

_MAX_NATIVE_PARSES_PER_FILE: int = 2
_MAX_EDIT_NATIVE_PARSES: int = 4


@pytest.mark.parametrize(
    "test_case",
    [
        NativeUncachedCountsTestCase(
            description="native-backend core-only uncached checks build zero CPython ASTs",
            file_target=120,
            seed=0,
            expected_python_parses=0,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_native_backend_when_checking_uncached_then_no_cpython_ast_is_built(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: NativeUncachedCountsTestCase,
) -> None:
    _ = generate_corpus(
        spec=CorpusSpec(target=tmp_path, file_target=test_case.file_target, seed=test_case.seed)
    )
    files: int = python_file_count(root=tmp_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv(FACT_BACKEND_ENV_VARIABLE, FactBackend.NATIVE.value)

    counts: dict[str, int] = counted_check(argv=("--no-color", "--no-cache"))

    assert counts.get(PARSE_OPERATION, 0) == test_case.expected_python_parses
    assert counts[FRESH_EVALUATION_OPERATION] == files
    assert counts[NATIVE_PARSE_OPERATION] >= files
    assert counts[NATIVE_PARSE_OPERATION] <= files * _MAX_NATIVE_PARSES_PER_FILE


@pytest.mark.parametrize(
    "test_case",
    [
        NativeEditCountsTestCase(
            description="native-backend one edited file re-evaluates without CPython parsing",
            file_target=120,
            seed=0,
            expected_fresh_evaluations=1,
            expected_python_parses=0,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_native_backend_when_one_file_edited_then_no_cpython_ast_is_built(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: NativeEditCountsTestCase,
) -> None:
    _ = generate_corpus(
        spec=CorpusSpec(target=tmp_path, file_target=test_case.file_target, seed=test_case.seed)
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv(FACT_BACKEND_ENV_VARIABLE, FactBackend.NATIVE.value)
    _ = counted_check(argv=("--no-color", "--cache"))
    edited: Path = sorted(tmp_path.rglob("record_shaping.py"))[0]
    _ = appended_module_constant(path=edited)

    counts: dict[str, int] = counted_check(argv=("--no-color", "--cache"))

    assert counts[FRESH_EVALUATION_OPERATION] == test_case.expected_fresh_evaluations
    assert counts.get(PARSE_OPERATION, 0) == test_case.expected_python_parses
    assert counts[NATIVE_PARSE_OPERATION] >= 1
    assert counts[NATIVE_PARSE_OPERATION] <= _MAX_EDIT_NATIVE_PARSES
