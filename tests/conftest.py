"""Tests for the SA Emergency integration."""

import asyncio
import sys
from unittest.mock import AsyncMock

import pytest

if sys.platform == "win32":
    import pytest_socket

    def _allow_sockets_on_windows(*_args: object, **_kwargs: object) -> None:
        """Skip socket blocking on Windows where asyncio needs socketpair()."""

    pytest_socket.disable_socket = _allow_sockets_on_windows  # type: ignore[assignment]
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

pytest_plugins = "pytest_homeassistant_custom_component"

# Public South Australian reference coordinates for geographic tests.
TEST_HOME_LAT = -34.9285
TEST_HOME_LON = 138.6007


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Load custom integration fixtures for every test."""
    return


@pytest.fixture(autouse=True)
def set_test_home_location(hass):
    """Use a stable Adelaide reference location for geographic processing."""
    hass.config.latitude = TEST_HOME_LAT
    hass.config.longitude = TEST_HOME_LON
    return


@pytest.fixture
def mock_sa_emergency_setup(monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
    """Block real integration setup during config-flow tests."""
    setup_mock = AsyncMock(return_value=True)
    monkeypatch.setattr(
        "custom_components.sa_emergency.async_setup_entry",
        setup_mock,
    )
    return setup_mock


@pytest.fixture
def mock_config_entry_reload(hass, monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
    """Block real config-entry reload during options-flow save tests."""
    reload_mock = AsyncMock(return_value=True)
    monkeypatch.setattr(hass.config_entries, "async_reload", reload_mock)
    return reload_mock


@pytest.fixture
def assert_no_ims_network(monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
    """Fail if flow tests reach the live IMS API client."""
    api_mock = AsyncMock(
        side_effect=AssertionError(
            "SaEmergencyApi.async_get_ims_incidents must not run in flow tests"
        )
    )
    monkeypatch.setattr(
        "custom_components.sa_emergency.api.SaEmergencyApi.async_get_ims_incidents",
        api_mock,
    )
    return api_mock
