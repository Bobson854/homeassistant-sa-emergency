"""Tests for the SA Emergency config flow."""

from unittest.mock import AsyncMock

import pytest
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.sa_emergency.const import DOMAIN, NAME


async def test_config_flow_user_creates_entry(
    hass: HomeAssistant,
    mock_sa_emergency_setup: AsyncMock,
    assert_no_ims_network: AsyncMock,
) -> None:
    """Test the user step creates a config entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
        data={},
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == NAME
    assert result["data"] == {}

    await hass.async_block_till_done()
    mock_sa_emergency_setup.assert_awaited_once()
    assert_no_ims_network.assert_not_awaited()


async def test_config_flow_prevents_duplicate(
    hass: HomeAssistant,
    mock_sa_emergency_setup: AsyncMock,
    assert_no_ims_network: AsyncMock,
) -> None:
    """Test duplicate configuration is prevented."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
        data={},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
        data={},
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] in {"already_configured", "single_instance_allowed"}
    assert mock_sa_emergency_setup.await_count == 1
    assert_no_ims_network.assert_not_awaited()


async def test_config_flow_requires_ha_location(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test setup is blocked when Home Assistant location is missing."""
    monkeypatch.setattr(hass.config, "latitude", None)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "location_not_configured"}
