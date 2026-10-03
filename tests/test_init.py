"""Tests for SA Emergency integration setup and unload."""

from unittest.mock import AsyncMock

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry
from tests.ims_helpers import ims_cfs_record, load_ims_attribute_records

from custom_components.sa_emergency.const import (
    DOMAIN,
    SENSOR_UNIQUE_INCIDENTS,
    SOURCE_CFS_CURRENT_INCIDENTS,
)
from custom_components.sa_emergency.presentation import incident_to_public_dict


def _mock_ims_source(monkeypatch, *, ims_return=None) -> None:
    monkeypatch.setattr(
        "custom_components.sa_emergency.coordinator.SaEmergencyApi.async_get_ims_incidents",
        AsyncMock(return_value=ims_return if ims_return is not None else []),
    )


async def test_setup_and_unload_entry(hass: HomeAssistant, monkeypatch) -> None:
    """Test integration setup loads V1 sensors and unloads cleanly."""
    _mock_ims_source(
        monkeypatch,
        ims_return=[ims_cfs_record(ident="123456", lat=-35.1234, long=139.5678)],
    )

    entry = MockConfigEntry(domain=DOMAIN, data={}, unique_id=DOMAIN)
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert DOMAIN in hass.data
    assert entry.entry_id in hass.data[DOMAIN]

    state = hass.states.get("sensor.sa_emergency_incidents")
    assert state is not None
    assert state.state == "1"
    assert state.attributes["local_count"] == 0
    assert state.attributes["regional_count"] == 1
    assert state.attributes["cfs_count"] == 1
    assert state.attributes["incidents_truncated"] is False
    assert (
        state.attributes["source_status"][SOURCE_CFS_CURRENT_INCIDENTS]["status"]
        == "ok"
    )
    assert "latitude" not in state.attributes
    assert "longitude" not in state.attributes
    assert hass.states.get("sensor.sa_emergency_status") is None

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.entry_id not in hass.data.get(DOMAIN, {})
    assert hass.states.get("sensor.sa_emergency_incidents").state == "unavailable"


async def test_setup_fails_when_ims_unavailable(
    hass: HomeAssistant, monkeypatch
) -> None:
    """Test setup fails when the combined IMS feed is unavailable."""
    from custom_components.sa_emergency.api import SaEmergencyApiError

    monkeypatch.setattr(
        "custom_components.sa_emergency.coordinator.SaEmergencyApi.async_get_ims_incidents",
        AsyncMock(side_effect=SaEmergencyApiError("IMS unavailable")),
    )

    entry = MockConfigEntry(domain=DOMAIN, data={}, unique_id=DOMAIN)
    entry.add_to_hass(hass)

    assert not await hass.config_entries.async_setup(entry.entry_id)


async def test_v1_sensor_entity_registry(hass: HomeAssistant, monkeypatch) -> None:
    """Test stable V1 sensors are registered with expected unique IDs."""
    _mock_ims_source(monkeypatch)

    entry = MockConfigEntry(domain=DOMAIN, data={}, unique_id=DOMAIN)
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    entity_registry = er.async_get(hass)
    entity = entity_registry.async_get("sensor.sa_emergency_incidents")

    assert entity is not None
    assert entity.unique_id == f"{entry.entry_id}_{SENSOR_UNIQUE_INCIDENTS}"
    assert entity.platform == DOMAIN


async def test_incident_public_attribute_schema(
    hass: HomeAssistant, monkeypatch
) -> None:
    """Test exposed incident attributes use the public schema keys."""
    _mock_ims_source(
        monkeypatch,
        ims_return=[ims_cfs_record(ident="123456", lat=-35.1234, long=139.5678)],
    )

    entry = MockConfigEntry(domain=DOMAIN, data={}, unique_id=DOMAIN)
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    incidents = hass.states.get("sensor.sa_emergency_incidents")
    assert incidents is not None
    exposed = incidents.attributes["incidents"][0]
    assert "type" in exposed
    assert "location" in exposed
    assert "bearing" in exposed
    assert "incident_type" not in exposed
    assert "location_name" not in exposed
    assert "resources" not in exposed
    assert "aircraft" not in exposed

    coordinator = hass.data[DOMAIN][entry.entry_id]
    assert exposed == incident_to_public_dict(coordinator.data.incidents_relevant[0])


async def test_combined_feed_populates_cfs_and_mfs_sensors(
    hass: HomeAssistant, monkeypatch
) -> None:
    """Test both agency sensors reflect a combined IMS feed."""
    _mock_ims_source(
        monkeypatch,
        ims_return=load_ims_attribute_records("ims_combined_features.json"),
    )

    entry = MockConfigEntry(domain=DOMAIN, data={}, unique_id=DOMAIN)
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert hass.states.get("sensor.sa_emergency_cfs_incidents").state == "1"
    assert hass.states.get("sensor.sa_emergency_mfs_incidents").state == "1"
