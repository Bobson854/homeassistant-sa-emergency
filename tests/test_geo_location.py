"""Tests for SA Emergency geolocation map markers."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry
from tests.ims_helpers import ims_cfs_record

from custom_components.sa_emergency.const import DOMAIN, RELEVANCE_LOCAL, RELEVANCE_NONE
from custom_components.sa_emergency.coordinator import SaEmergencyDataUpdateCoordinator
from custom_components.sa_emergency.geo_location import (
    SaEmergencyGeolocationManager,
    _marker_incidents,
)
from custom_components.sa_emergency.models import Incident, SaEmergencyData
from custom_components.sa_emergency.presentation import incident_geolocation_name


def _mock_ims(monkeypatch: pytest.MonkeyPatch, *, ims_return) -> None:
    monkeypatch.setattr(
        "custom_components.sa_emergency.coordinator.SaEmergencyApi.async_get_ims_incidents",
        AsyncMock(return_value=ims_return),
    )


def _incident(
    incident_id: str,
    *,
    lat: float | None,
    lon: float | None,
    relevance: str = RELEVANCE_LOCAL,
    distance: float = 5.0,
) -> Incident:
    return Incident(
        incident_id=incident_id,
        agency="CFS",
        source="ims_current_incidents",
        incident_type="Burn Off",
        status="Controlled",
        level="1",
        first_reported=datetime(2026, 3, 10, 12, 0, tzinfo=UTC),
        location_name="WOODSIDE",
        latitude=lat,
        longitude=lon,
        region=None,
        fire_ban_district="MOUNT LOFTY RANGES",
        resources=None,
        aircraft_count=None,
        message="Operational text",
        message_url="https://www.cfs.sa.gov.au/incidents",
        distance_km=distance,
        bearing_degrees=90.0,
        bearing_cardinal="E",
        relevance=relevance,
    )


async def test_relevant_incident_creates_geolocation_entity(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A relevant incident with coordinates creates one geo_location entity."""
    _mock_ims(
        monkeypatch,
        ims_return=[
            ims_cfs_record(
                ident="MAP1",
                event="Burn Off",
                lat=-34.95,
                long=138.60,
                location="WOODSIDE",
            )
        ],
    )

    entry = MockConfigEntry(domain=DOMAIN, data={}, unique_id=DOMAIN)
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    states = [
        state
        for state in hass.states.async_all("geo_location")
        if state.attributes.get("source") == DOMAIN
    ]
    assert len(states) == 1
    assert states[0].attributes["incident_id"] == "CFS:MAP1"
    assert states[0].attributes["agency"] == "CFS"


async def test_geolocation_entity_metadata(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Entity exposes source, distance, coordinates, unique id, and attributes."""
    _mock_ims(
        monkeypatch,
        ims_return=[
            ims_cfs_record(
                ident="META1",
                event="Grass Fire",
                inc_status="GOING",
                lat=-34.95,
                long=138.60,
                location="TEST AREA",
            )
        ],
    )

    entry = MockConfigEntry(domain=DOMAIN, data={}, unique_id=DOMAIN)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    entity_registry = er.async_get(hass)
    geo_state = next(
        state
        for state in hass.states.async_all("geo_location")
        if state.attributes.get("incident_id") == "CFS:META1"
    )

    reg_entity = entity_registry.async_get(geo_state.entity_id)
    assert reg_entity is not None
    assert reg_entity.unique_id == f"{entry.entry_id}_CFS:META1"
    assert geo_state.attributes["source"] == DOMAIN
    assert geo_state.attributes["latitude"] is not None
    assert geo_state.attributes["longitude"] is not None
    assert float(geo_state.state) >= 0
    assert geo_state.attributes["type"] == "Grass Fire"
    assert geo_state.attributes["location"] == "TEST AREA"
    assert reg_entity.device_id is None


async def test_non_spatial_incident_no_geolocation_entity(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Incidents without coordinates do not create geolocation entities."""
    _mock_ims(
        monkeypatch,
        ims_return=[ims_cfs_record(ident="NOCOORD", lat="invalid", long="invalid")],
    )

    entry = MockConfigEntry(domain=DOMAIN, data={}, unique_id=DOMAIN)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert not [
        s
        for s in hass.states.async_all("geo_location")
        if s.attributes.get("source") == DOMAIN
    ]


async def test_outside_regional_radius_no_geolocation_entity(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Incidents outside the regional radius are not exposed as map markers."""
    _mock_ims(
        monkeypatch,
        ims_return=[ims_cfs_record(ident="FAR1", lat=-37.831, long=140.779)],
    )

    entry = MockConfigEntry(domain=DOMAIN, data={}, unique_id=DOMAIN)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert not [
        s
        for s in hass.states.async_all("geo_location")
        if s.attributes.get("source") == DOMAIN
    ]


async def test_geolocation_entity_updates_on_coordinator_refresh(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An existing marker updates when coordinator data changes."""
    ims_mock = AsyncMock(
        return_value=[
            ims_cfs_record(
                ident="UPD1",
                event="Grass Fire",
                lat=-34.95,
                long=138.60,
            )
        ]
    )
    monkeypatch.setattr(
        "custom_components.sa_emergency.coordinator.SaEmergencyApi.async_get_ims_incidents",
        ims_mock,
    )

    entry = MockConfigEntry(domain=DOMAIN, data={}, unique_id=DOMAIN)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    state = next(
        s
        for s in hass.states.async_all("geo_location")
        if s.attributes.get("incident_id") == "CFS:UPD1"
    )
    assert state.attributes["type"] == "Grass Fire"

    ims_mock.return_value = [
        ims_cfs_record(
            ident="UPD1",
            event="Structure Fire",
            lat=-34.95,
            long=138.60,
        )
    ]
    coordinator: SaEmergencyDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    await coordinator.async_request_refresh()
    await hass.async_block_till_done()

    state = hass.states.get(state.entity_id)
    assert state is not None
    assert state.attributes["type"] == "Structure Fire"


async def test_removed_incident_force_removed_from_registry(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Markers are removed from state and entity registry when no longer relevant."""
    ims_mock = AsyncMock(
        return_value=[
            ims_cfs_record(ident="REM1", lat=-34.95, long=138.60),
        ]
    )
    monkeypatch.setattr(
        "custom_components.sa_emergency.coordinator.SaEmergencyApi.async_get_ims_incidents",
        ims_mock,
    )

    entry = MockConfigEntry(domain=DOMAIN, data={}, unique_id=DOMAIN)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    entity_registry = er.async_get(hass)
    state = next(
        s
        for s in hass.states.async_all("geo_location")
        if s.attributes.get("incident_id") == "CFS:REM1"
    )
    entity_id = state.entity_id
    assert entity_registry.async_get(entity_id) is not None

    ims_mock.return_value = []
    coordinator: SaEmergencyDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    await coordinator.async_request_refresh()
    await hass.async_block_till_done()
    await coordinator._geo_location_manager.async_sync_from_coordinator()

    assert hass.states.get(entity_id) is None
    assert entity_registry.async_get(entity_id) is None


def test_marker_incidents_filters_coordinates() -> None:
    """Manager helper only returns relevant incidents with coordinates."""
    local = _incident("CFS:1", lat=-34.0, lon=138.0)
    non_spatial = _incident("CFS:2", lat=None, lon=None, relevance=RELEVANCE_NONE)
    far = _incident("CFS:3", lat=-40.0, lon=141.0, relevance=RELEVANCE_NONE)

    class _CoordinatorStub:
        data = SaEmergencyData(
            incidents_relevant=[local],
            incidents_all=[local, non_spatial, far],
        )

    assert _marker_incidents(_CoordinatorStub()) == [local]  # type: ignore[arg-type]


def test_incident_geolocation_name_type_location_agency() -> None:
    """Geolocation names lead with type, then location, then agency in parentheses."""
    assert (
        incident_geolocation_name(
            _incident("CFS:X", lat=1.0, lon=2.0, relevance=RELEVANCE_LOCAL)
        )
        == "Burn Off — WOODSIDE (CFS)"
    )


def test_incident_geolocation_name_long_location() -> None:
    """Long location labels are preserved after the incident type."""
    incident = _incident("CFS:X", lat=1.0, lon=2.0)
    incident.location_name = "GERANIUM NORTH, GERANIUM"
    incident.incident_type = "Structure Fire"
    assert (
        incident_geolocation_name(incident)
        == "Structure Fire — GERANIUM NORTH, GERANIUM (CFS)"
    )


def test_incident_geolocation_name_type_only() -> None:
    """Type and agency without location omit the middle segment."""
    incident = _incident("MFS:X", lat=1.0, lon=2.0)
    incident.agency = "MFS"
    incident.incident_type = "Fire Alarm"
    incident.location_name = None
    assert incident_geolocation_name(incident) == "Fire Alarm (MFS)"


def test_incident_geolocation_name_location_only() -> None:
    """Location and agency without type omit the type segment."""
    incident = _incident("CFS:X", lat=1.0, lon=2.0)
    incident.incident_type = None
    incident.location_name = "WOODSIDE"
    assert incident_geolocation_name(incident) == "WOODSIDE (CFS)"


def test_incident_geolocation_name_fallback_to_incident_id() -> None:
    """Missing type and location fall back to incident_id plus agency."""
    incident = _incident("CFS:F2610030053", lat=1.0, lon=2.0)
    incident.incident_type = None
    incident.location_name = None
    assert incident_geolocation_name(incident) == "CFS:F2610030053 (CFS)"


async def test_manager_sync_removes_stale_entity(hass: HomeAssistant) -> None:
    """Direct manager sync removes entities not in coordinator data."""
    added: list = []

    def _add(entities, update_before_add=True) -> None:
        added.extend(entities)
        for entity in entities:
            entity.hass = hass
            entity.async_write_ha_state = lambda: None  # type: ignore[method-assign]
            entity.schedule_update_ha_state = lambda: None  # type: ignore[method-assign]

    entry = MockConfigEntry(domain=DOMAIN, data={}, unique_id=DOMAIN)
    entry.add_to_hass(hass)

    coordinator = SaEmergencyDataUpdateCoordinator(hass, entry)
    coordinator.data = SaEmergencyData(
        incidents_relevant=[_incident("CFS:RM", lat=-34.95, lon=138.6)],
    )

    manager = SaEmergencyGeolocationManager(coordinator, entry.entry_id, _add)
    await manager.async_sync_from_coordinator()
    assert "CFS:RM" in manager._entities

    remove_calls: list[bool] = []

    async def _fake_remove(*_args, force_remove=False, **_kwargs) -> None:
        remove_calls.append(force_remove)

    entity = manager._entities["CFS:RM"]
    entity.async_remove = _fake_remove  # type: ignore[method-assign]
    coordinator.data = SaEmergencyData(incidents_relevant=[])
    await manager.async_sync_from_coordinator()

    assert remove_calls == [True]
    assert "CFS:RM" not in manager._entities
