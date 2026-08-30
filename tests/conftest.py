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


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Load custom integration fixtures for every test."""
    return
