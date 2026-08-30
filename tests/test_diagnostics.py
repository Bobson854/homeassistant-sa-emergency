"""Tests for SA Emergency diagnostics."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry
from tests.fixtures import load_json_fixture

from custom_components.sa_emergency.api import SaEmergencyApiError
from custom_components.sa_emergency.const import (
    CONF_INCLUDE_CFS,
    CONF_INCLUDE_MFS,
    CONF_LOCAL_RADIUS_KM,
    CONF_REGIONAL_RADIUS_KM,
    DOMAIN,
    SOURCE_CFS_CURRENT_INCIDENTS,
    SOURCE_MFS_CURRENT_INCIDENTS,
    SOURCE_STATUS_DISABLED,
    SOURCE_STATUS_ERROR,
)
from custom_components.sa_emergency.diagnostics import (
    _build_diagnostics_payload,
    assert_no_home_coordinates,
    async_get_config_entry_diagnostics,
)


def _mock_sources(
    monkeypatch,
    *,
    cfs_return=None,
    cfs_side_effect=None,
    mfs_return=None,
    mfs_side_effect=None,
) -> None:
    if cfs_side_effect is not None:
        monkeypatch.setattr(
            "custom_components.sa_emergency.coordinator.SaEmergencyApi.async_get_cfs_incidents",
            AsyncMock(side_effect=cfs_side_effect),
        )
    else:
        monkeypatch.setattr(
            "custom_components.sa_emergency.coordinator.SaEmergencyApi.async_get_cfs_incidents",
            AsyncMock(return_value=cfs_return if cfs_return is not None else []),
        )

    if mfs_side_effect is not None:
        monkeypatch.setattr(
            "custom_components.sa_emergency.coordinator.SaEmergencyApi.async_get_mfs_incidents",
            AsyncMock(side_effect=mfs_side_effect),
        )
    else:
        monkeypatch.setattr(
            "custom_components.sa_emergency.coordinator.SaEmergencyApi.async_get_mfs_incidents",
            AsyncMock(return_value=mfs_return if mfs_return is not None else []),
        )


async def _setup_entry(
    hass: HomeAssistant,
    monkeypatch,
    *,
    options: dict | None = None,
    cfs_return=None,
    mfs_return=None,
    cfs_side_effect=None,
    mfs_side_effect=None,
) -> MockConfigEntry:
    _mock_sources(
        monkeypatch,
        cfs_return=cfs_return,
        cfs_side_effect=cfs_side_effect,
        mfs_return=mfs_return,
        mfs_side_effect=mfs_side_effect,
    )
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={},
        unique_id=DOMAIN,
        options=options or {},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_diagnostics_normal_data(hass: HomeAssistant, monkeypatch) -> None:
    """Test diagnostics include aggregated runtime information."""
    entry = await _setup_entry(
        hass,
        monkeypatch,
        cfs_return=load_json_fixture("cfs_valid_single.json"),
    )

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)

    assert diagnostics["integration"]["version"] == "0.6.0"
    assert diagnostics["options"]["local_radius_km"] == 25.0
    assert diagnostics["sources"]["cfs"]["status"] == "ok"
    assert diagnostics["incidents"]["relevant"] == 1
    assert diagnostics["incidents"]["total_source"] == 1
    assert "last_successful_update" in diagnostics
    assert "incidents" not in diagnostics or isinstance(diagnostics["incidents"], dict)


async def test_diagnostics_partial_cfs_failure(
    hass: HomeAssistant, monkeypatch
) -> None:
    """Test diagnostics when CFS fails but MFS succeeds."""
    from tests.test_coordinator import _mfs_attributes_records

    entry = await _setup_entry(
        hass,
        monkeypatch,
        cfs_side_effect=SaEmergencyApiError("CFS unavailable"),
        mfs_return=_mfs_attributes_records("mfs_valid_single.json"),
    )

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)

    assert diagnostics["sources"]["cfs"]["status"] == SOURCE_STATUS_ERROR
    assert diagnostics["sources"]["mfs"]["status"] == "ok"
    assert diagnostics["incidents"]["total_source"] == 1


async def test_diagnostics_partial_mfs_failure(
    hass: HomeAssistant, monkeypatch
) -> None:
    """Test diagnostics when MFS fails but CFS succeeds."""
    entry = await _setup_entry(
        hass,
        monkeypatch,
        cfs_return=load_json_fixture("cfs_valid_single.json"),
        mfs_side_effect=SaEmergencyApiError("MFS unavailable"),
    )

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)

    assert diagnostics["sources"]["cfs"]["status"] == "ok"
    assert diagnostics["sources"]["mfs"]["status"] == SOURCE_STATUS_ERROR


async def test_diagnostics_disabled_source(hass: HomeAssistant, monkeypatch) -> None:
    """Test diagnostics represent disabled sources explicitly."""
    entry = await _setup_entry(
        hass,
        monkeypatch,
        options={CONF_INCLUDE_CFS: True, CONF_INCLUDE_MFS: False},
        cfs_return=load_json_fixture("cfs_valid_single.json"),
    )

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)

    assert diagnostics["options"]["include_mfs"] is False
    assert diagnostics["sources"]["mfs"]["status"] == SOURCE_STATUS_DISABLED
    assert diagnostics["sources"]["mfs"]["enabled"] is False


async def test_diagnostics_empty_feeds(hass: HomeAssistant, monkeypatch) -> None:
    """Test diagnostics with successful empty source feeds."""
    entry = await _setup_entry(hass, monkeypatch, cfs_return=[], mfs_return=[])

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)

    assert diagnostics["incidents"]["total_source"] == 0
    assert diagnostics["incidents"]["relevant"] == 0
    assert diagnostics["incidents"]["highest_relevance"] == "none"


async def test_diagnostics_custom_options(hass: HomeAssistant, monkeypatch) -> None:
    """Test diagnostics reflect configured options."""
    entry = await _setup_entry(
        hass,
        monkeypatch,
        options={
            CONF_LOCAL_RADIUS_KM: 40,
            CONF_REGIONAL_RADIUS_KM: 150,
            "scan_interval": 300,
            CONF_INCLUDE_CFS: False,
            CONF_INCLUDE_MFS: True,
        },
        mfs_return=[],
    )

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)

    assert diagnostics["options"]["local_radius_km"] == 40
    assert diagnostics["options"]["scan_interval_seconds"] == 300
    assert diagnostics["options"]["include_cfs"] is False


async def test_diagnostics_no_home_location_leakage(
    hass: HomeAssistant, monkeypatch
) -> None:
    """Test diagnostics never expose Home Assistant home coordinates."""
    entry = await _setup_entry(
        hass,
        monkeypatch,
        cfs_return=load_json_fixture("cfs_valid_single.json"),
    )

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)
    serialized = json.dumps(diagnostics)

    assert "latitude" not in serialized.lower()
    assert "longitude" not in serialized.lower()
    assert str(hass.config.latitude) not in serialized
    assert str(hass.config.longitude) not in serialized
    assert_no_home_coordinates(diagnostics)


def test_build_diagnostics_payload_excludes_raw_incidents() -> None:
    """Test diagnostics builder does not embed raw incident records."""
    from datetime import timedelta

    from custom_components.sa_emergency.models import (
        Incident,
        SaEmergencyData,
        SourceStatus,
    )
    from custom_components.sa_emergency.options import SaEmergencyOptions

    incident = Incident(
        incident_id="CFS:1",
        agency="CFS",
        source=SOURCE_CFS_CURRENT_INCIDENTS,
        incident_type="Grass Fire",
        status="GOING",
        level=None,
        first_reported=None,
        location_name="Test",
        latitude=-35.0,
        longitude=138.0,
        region=None,
        fire_ban_district=None,
        resources=None,
        aircraft_count=None,
        message=None,
        message_url=None,
        distance_km=10.0,
        relevance="local",
    )

    class _CoordinatorStub:
        options = SaEmergencyOptions(
            local_radius_km=25.0,
            regional_radius_km=100.0,
            scan_interval=timedelta(seconds=180),
            include_cfs=True,
            include_mfs=True,
        )
        data = SaEmergencyData(
            incidents_all=[incident],
            incidents_relevant=[incident],
            incidents_local=[incident],
            nearest_incident=incident,
            source_status={
                SOURCE_CFS_CURRENT_INCIDENTS: SourceStatus(status="ok", raw_count=1),
                SOURCE_MFS_CURRENT_INCIDENTS: SourceStatus(status="ok", raw_count=0),
            },
        )

    payload = _build_diagnostics_payload(
        integration_version="0.6.0",
        coordinator=_CoordinatorStub(),  # type: ignore[arg-type]
    )

    serialized = json.dumps(payload)
    assert "Grass Fire" not in serialized
    assert payload["incidents"]["nearest_incident_id"] == "CFS:1"
    assert "url" in payload["sources"]["cfs"]
    assert "features" not in serialized
