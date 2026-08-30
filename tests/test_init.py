"""Tests for SA Emergency integration setup and unload."""

from unittest.mock import AsyncMock

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry
from tests.fixtures import load_json_fixture

from custom_components.sa_emergency.const import DOMAIN


async def test_setup_and_unload_entry(hass: HomeAssistant, monkeypatch) -> None:
    """Test integration setup loads the development sensor and unloads cleanly."""
    monkeypatch.setattr(
        "custom_components.sa_emergency.coordinator.SaEmergencyApi.async_get_cfs_incidents",
        AsyncMock(return_value=load_json_fixture("cfs_valid_single.json")),
    )

    entry = MockConfigEntry(domain=DOMAIN, data={}, unique_id=DOMAIN)
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert DOMAIN in hass.data
    assert entry.entry_id in hass.data[DOMAIN]

    state = hass.states.get("sensor.sa_emergency_status")
    assert state is not None
    assert state.state == "1"
    assert state.attributes["development_sensor"] is True
    assert state.attributes["source"] == "CFS"
    assert state.attributes["source_status"] == "ok"
    assert state.attributes["normalized_incident_count"] == 1

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.entry_id not in hass.data.get(DOMAIN, {})

    state = hass.states.get("sensor.sa_emergency_status")
    assert state is not None
    assert state.state == "unavailable"


async def test_scaffold_sensor_entity_registry(
    hass: HomeAssistant, monkeypatch
) -> None:
    """Test the temporary development sensor is registered correctly."""
    monkeypatch.setattr(
        "custom_components.sa_emergency.coordinator.SaEmergencyApi.async_get_cfs_incidents",
        AsyncMock(return_value=[]),
    )

    entry = MockConfigEntry(domain=DOMAIN, data={}, unique_id=DOMAIN)
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    entity_registry = er.async_get(hass)
    entity = entity_registry.async_get("sensor.sa_emergency_status")

    assert entity is not None
    assert entity.unique_id == f"{entry.entry_id}_status"
    assert entity.platform == DOMAIN
