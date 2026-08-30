"""Tests for V1 sensor behaviour."""

from unittest.mock import AsyncMock

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.sa_emergency.const import (
    AGENCY_CFS,
    CONF_INCLUDE_CFS,
    CONF_INCLUDE_MFS,
    DOMAIN,
    MAX_RELEVANT_INCIDENTS,
    RELEVANCE_LOCAL,
    RELEVANCE_REGIONAL,
    SOURCE_CFS_CURRENT_INCIDENTS,
    SOURCE_STATUS_DISABLED,
    SOURCE_STATUS_ERROR,
)
from custom_components.sa_emergency.models import (
    Incident,
    SaEmergencyData,
)
from custom_components.sa_emergency.presentation import nearest_incident_state
from custom_components.sa_emergency.sensor import _incidents_attributes


def _incident(incident_id: str, *, relevance: str, distance: float) -> Incident:
    return Incident(
        incident_id=incident_id,
        agency=AGENCY_CFS,
        source=SOURCE_CFS_CURRENT_INCIDENTS,
        incident_type=f"Type {incident_id}",
        status="GOING",
        level=None,
        first_reported=None,
        location_name=f"Location {incident_id}",
        latitude=-34.95,
        longitude=138.60,
        region=None,
        fire_ban_district=None,
        resources=None,
        aircraft_count=None,
        message=None,
        message_url=None,
        distance_km=distance,
        bearing_degrees=90.0,
        bearing_cardinal="E",
        relevance=relevance,
    )


def test_incidents_attribute_truncates_at_max_relevant() -> None:
    """Test primary sensor exposes only 50 incidents while state uses full count."""
    from custom_components.sa_emergency.options import SaEmergencyOptions

    relevant = [
        _incident(f"CFS:{index}", relevance=RELEVANCE_LOCAL, distance=float(index))
        for index in range(60)
    ]
    data = SaEmergencyData(
        incidents_all=relevant,
        incidents_relevant=relevant,
        incidents_local=relevant,
        incidents_regional=[],
        highest_relevance=RELEVANCE_LOCAL,
        nearest_incident=relevant[0],
    )
    options = SaEmergencyOptions(
        local_radius_km=25.0,
        regional_radius_km=100.0,
        scan_interval=__import__("datetime").timedelta(seconds=180),
        include_cfs=True,
        include_mfs=True,
    )

    attributes = _incidents_attributes(data, options)

    assert len(data.incidents_relevant) == 60
    assert attributes["local_count"] == 60
    assert len(attributes["incidents"]) == MAX_RELEVANT_INCIDENTS
    assert attributes["incidents_exposed"] == MAX_RELEVANT_INCIDENTS
    assert attributes["incidents_truncated"] is True
    assert attributes["incidents"][0]["incident_id"] == "CFS:0"


def test_incidents_attribute_not_truncated_below_cap() -> None:
    """Test truncation flags are false when relevant count is below the cap."""
    from custom_components.sa_emergency.options import SaEmergencyOptions

    relevant = [_incident("CFS:1", relevance=RELEVANCE_REGIONAL, distance=50.0)]
    data = SaEmergencyData(
        incidents_all=relevant,
        incidents_relevant=relevant,
        incidents_regional=relevant,
        highest_relevance=RELEVANCE_REGIONAL,
        nearest_incident=relevant[0],
    )
    options = SaEmergencyOptions(
        local_radius_km=25.0,
        regional_radius_km=100.0,
        scan_interval=__import__("datetime").timedelta(seconds=180),
        include_cfs=True,
        include_mfs=True,
    )

    attributes = _incidents_attributes(data, options)

    assert attributes["incidents_truncated"] is False
    assert attributes["incidents_exposed"] == 1


def test_nearest_incident_state_prefers_type_then_location() -> None:
    """Test nearest incident state uses type, then location, then ID."""
    incident = _incident("CFS:1", relevance=RELEVANCE_LOCAL, distance=1.0)
    assert nearest_incident_state(incident) == "Type CFS:1"

    incident.incident_type = None
    assert nearest_incident_state(incident) == "Location CFS:1"

    incident.location_name = None
    assert nearest_incident_state(incident) == "CFS:1"

    assert nearest_incident_state(None) is None


async def test_sensor_states_after_setup(hass: HomeAssistant, monkeypatch) -> None:
    """Test final sensor states for mixed local/regional incidents."""
    monkeypatch.setattr(
        "custom_components.sa_emergency.coordinator.SaEmergencyApi.async_get_cfs_incidents",
        AsyncMock(
            return_value=[
                {
                    "IncidentNo": "LOCAL1",
                    "Date": "30/08/2026",
                    "Time": "14:30",
                    "Type": "Grass Fire",
                    "Status": "GOING",
                    "Location": "-34.95,138.60",
                },
                {
                    "IncidentNo": "REGIONAL1",
                    "Date": "30/08/2026",
                    "Time": "14:30",
                    "Type": "Structure Fire",
                    "Status": "GOING",
                    "Location": "-35.12,139.57",
                },
            ]
        ),
    )
    monkeypatch.setattr(
        "custom_components.sa_emergency.coordinator.SaEmergencyApi.async_get_mfs_incidents",
        AsyncMock(return_value=[]),
    )

    entry = MockConfigEntry(domain=DOMAIN, data={}, unique_id=DOMAIN)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert hass.states.get("sensor.sa_emergency_incidents").state == "2"
    assert hass.states.get("sensor.sa_emergency_local_incidents").state == "1"
    assert hass.states.get("sensor.sa_emergency_regional_incidents").state == "1"
    assert hass.states.get("sensor.sa_emergency_highest_relevance").state == "local"
    assert hass.states.get("sensor.sa_emergency_nearest_incident").state == "Grass Fire"
    assert hass.states.get("sensor.sa_emergency_cfs_incidents").state == "2"


async def test_agency_sensor_unknown_on_source_error(
    hass: HomeAssistant, monkeypatch
) -> None:
    """Test agency count sensors distinguish source failure from zero incidents."""
    from custom_components.sa_emergency.api import SaEmergencyApiError

    monkeypatch.setattr(
        "custom_components.sa_emergency.coordinator.SaEmergencyApi.async_get_cfs_incidents",
        AsyncMock(side_effect=SaEmergencyApiError("CFS unavailable")),
    )
    monkeypatch.setattr(
        "custom_components.sa_emergency.coordinator.SaEmergencyApi.async_get_mfs_incidents",
        AsyncMock(return_value=[]),
    )

    entry = MockConfigEntry(domain=DOMAIN, data={}, unique_id=DOMAIN)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    cfs = hass.states.get("sensor.sa_emergency_cfs_incidents")
    assert cfs.state in {"unknown", "unavailable", "None", ""}
    assert cfs.attributes["status"] == SOURCE_STATUS_ERROR


async def test_agency_sensor_disabled_source(hass: HomeAssistant, monkeypatch) -> None:
    """Test disabled agency sensors remain present with disabled status."""
    monkeypatch.setattr(
        "custom_components.sa_emergency.coordinator.SaEmergencyApi.async_get_cfs_incidents",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        "custom_components.sa_emergency.coordinator.SaEmergencyApi.async_get_mfs_incidents",
        AsyncMock(return_value=[]),
    )

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={},
        unique_id=DOMAIN,
        options={CONF_INCLUDE_CFS: True, CONF_INCLUDE_MFS: False},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    mfs = hass.states.get("sensor.sa_emergency_mfs_incidents")
    assert mfs is not None
    assert mfs.state in {"unknown", "unavailable", "None", ""}
    assert mfs.attributes["status"] == SOURCE_STATUS_DISABLED
    assert mfs.attributes["enabled"] is False


async def test_no_relevant_incidents_nearest_sensor(
    hass: HomeAssistant, monkeypatch
) -> None:
    """Test nearest and highest relevance sensors with no relevant incidents."""
    monkeypatch.setattr(
        "custom_components.sa_emergency.coordinator.SaEmergencyApi.async_get_cfs_incidents",
        AsyncMock(
            return_value=[
                {
                    "IncidentNo": "FAR1",
                    "Date": "30/08/2026",
                    "Time": "14:30",
                    "Type": "Grass Fire",
                    "Status": "GOING",
                    "Location": "-37.831,140.779",
                }
            ]
        ),
    )
    monkeypatch.setattr(
        "custom_components.sa_emergency.coordinator.SaEmergencyApi.async_get_mfs_incidents",
        AsyncMock(return_value=[]),
    )

    entry = MockConfigEntry(domain=DOMAIN, data={}, unique_id=DOMAIN)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    nearest = hass.states.get("sensor.sa_emergency_nearest_incident")
    assert nearest.state in {"unknown", "unavailable", "None", ""}
    assert hass.states.get("sensor.sa_emergency_highest_relevance").state == "none"
    assert hass.states.get("sensor.sa_emergency_incidents").state == "0"
