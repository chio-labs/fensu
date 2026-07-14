"""Fact backend selection behavior across environments and installs."""

import pytest

import strata.analysis.main.select_fact_backend as selection_module
from strata.analysis.constants import FACT_BACKEND_ENV_VARIABLE
from strata.analysis.exceptions import NativeBackendUnavailableError
from strata.analysis.main.select_fact_backend import select_fact_backend
from strata.analysis.models import FactBackendSelection
from tests.unit.src.strata.analysis._test_types import (
    BackendUnavailableTestCase,
    FactBackendSelectionTestCase,
)
from tests.unit.src.strata.analysis.helpers import (
    FAKE_NATIVE_VERSION,
    fake_find_spec,
    fake_import_module,
)


@pytest.mark.parametrize(
    "test_case",
    [
        FactBackendSelectionTestCase(
            description="default selection prefers the installed native backend",
            requested_value="",
            native_available=True,
            expected_backend="native",
            expected_native_version=FAKE_NATIVE_VERSION,
            expected_warning_present=False,
        ),
        FactBackendSelectionTestCase(
            description="requesting python keeps python even with the native module installed",
            requested_value="python",
            native_available=True,
            expected_backend="python",
            expected_native_version=FAKE_NATIVE_VERSION,
            expected_warning_present=False,
        ),
        FactBackendSelectionTestCase(
            description="requesting native selects native when installed",
            requested_value="native",
            native_available=True,
            expected_backend="native",
            expected_native_version=FAKE_NATIVE_VERSION,
            expected_warning_present=False,
        ),
        FactBackendSelectionTestCase(
            description="unknown values warn and keep the default backend",
            requested_value="rust",
            native_available=True,
            expected_backend="native",
            expected_native_version=FAKE_NATIVE_VERSION,
            expected_warning_present=True,
        ),
        FactBackendSelectionTestCase(
            description="requested values are case and whitespace insensitive",
            requested_value="  NATIVE  ",
            native_available=True,
            expected_backend="native",
            expected_native_version=FAKE_NATIVE_VERSION,
            expected_warning_present=False,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_environment_and_install_state_when_selecting_backend_then_resolves_expected_backend(
    monkeypatch: pytest.MonkeyPatch,
    test_case: FactBackendSelectionTestCase,
) -> None:
    monkeypatch.setenv(FACT_BACKEND_ENV_VARIABLE, test_case.requested_value or "")
    monkeypatch.setattr(
        selection_module,
        "find_spec",
        fake_find_spec(available=test_case.native_available),
    )
    monkeypatch.setattr(selection_module, "import_module", fake_import_module)
    select_fact_backend.cache_clear()

    selection: FactBackendSelection = select_fact_backend()
    select_fact_backend.cache_clear()

    assert selection.backend.value == test_case.expected_backend
    assert selection.native_version == test_case.expected_native_version
    assert (selection.warning is not None) is test_case.expected_warning_present


@pytest.mark.parametrize(
    "test_case",
    [
        BackendUnavailableTestCase(
            description="default selection rejects a missing native module",
            requested_value="",
            expected_message_fragment="Reinstall stratalint",
        ),
        BackendUnavailableTestCase(
            description="requesting native rejects a missing native module",
            requested_value="native",
            expected_message_fragment="Reinstall stratalint",
        ),
        BackendUnavailableTestCase(
            description="unknown values reject a missing native module",
            requested_value="rust",
            expected_message_fragment="Reinstall stratalint",
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_missing_native_module_when_selecting_backend_then_raises_actionable_error(
    monkeypatch: pytest.MonkeyPatch,
    test_case: BackendUnavailableTestCase,
) -> None:
    monkeypatch.setenv(FACT_BACKEND_ENV_VARIABLE, test_case.requested_value)
    monkeypatch.setattr(selection_module, "find_spec", fake_find_spec(available=False))
    monkeypatch.setattr(selection_module, "import_module", fake_import_module)
    select_fact_backend.cache_clear()

    with pytest.raises(NativeBackendUnavailableError) as raised:
        select_fact_backend()
    select_fact_backend.cache_clear()

    assert test_case.expected_message_fragment in str(raised.value)
