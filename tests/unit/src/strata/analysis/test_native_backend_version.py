"""Required native extension version resolution."""

import pytest

import strata.analysis.main.resolve_native_backend_version as version_module
from strata.analysis.exceptions import NativeBackendUnavailableError
from strata.analysis.main.resolve_native_backend_version import resolve_native_backend_version
from tests.unit.src.strata.analysis._test_types import BackendUnavailableTestCase
from tests.unit.src.strata.analysis.helpers import (
    FAKE_NATIVE_VERSION,
    fake_find_spec,
    fake_import_module,
)


@pytest.mark.parametrize(
    "test_case",
    [
        BackendUnavailableTestCase(
            description="missing native module raises an actionable installation error",
            expected_message_fragment="Reinstall stratalint",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_missing_native_module_when_resolving_version_then_raises_actionable_error(
    monkeypatch: pytest.MonkeyPatch,
    test_case: BackendUnavailableTestCase,
) -> None:
    monkeypatch.setattr(version_module, "find_spec", fake_find_spec(available=False))
    resolve_native_backend_version.cache_clear()

    with pytest.raises(NativeBackendUnavailableError) as raised:
        resolve_native_backend_version()
    resolve_native_backend_version.cache_clear()

    assert test_case.expected_message_fragment in str(raised.value)


@pytest.mark.parametrize(
    "test_case",
    [
        BackendUnavailableTestCase(
            description="installed native module reports its extension version",
            expected_message_fragment=FAKE_NATIVE_VERSION,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_installed_native_module_when_resolving_version_then_returns_extension_version(
    monkeypatch: pytest.MonkeyPatch,
    test_case: BackendUnavailableTestCase,
) -> None:
    monkeypatch.setattr(version_module, "find_spec", fake_find_spec(available=True))
    monkeypatch.setattr(version_module, "import_module", fake_import_module)
    resolve_native_backend_version.cache_clear()

    result: str = resolve_native_backend_version()
    resolve_native_backend_version.cache_clear()

    assert result == test_case.expected_message_fragment
