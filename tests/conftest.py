"""Tests for the SA Emergency integration."""

import asyncio
import sys

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
