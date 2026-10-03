"""Tests for SA Emergency diagnostics."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry
from tests.ims_helpers import load_ims_attribute_records

from custom_components.sa_emergency.api import SaEmergencyApiError
from custom_components.sa_emergency.const import (
    CONF_INCLUDE_CFS,
    CONF_INCLUDE_MFS,
    CONF_LOCAL_RADIUS_KM,
    CONF_REGIONAL_RADIUS_KM,
    DOMAIN,
    IMS_INCIDENTS_URL,
    SOURCE_CFS_CURRENT_INCIDENTS,
    SOURCE_IMS_CURRENT_INCIDENTS,
    SOURCE_MFS_CURRENT_INCIDENTS,
    SOURCE_STATUS_DISABLED,
)
from custom_components.sa_emergency.diagnostics import (
    _build_diagnostics_payload,
    assert_no_home_coordinates,
    async_get_config_entry_diagnostics,
)


def _mock_ims_source(
    monkeypatch,
    *,
    ims_return=None,
    ims_side_effect=None,
) -> None:
    if ims_side_effect is not None:
        monkeypatch.setattr(
            "custom_components.sa_emergency.coordinator.SaEmergencyApi.async_get_ims_incidents",
            AsyncMock(side_effect=ims_side_effect),
        )
    else:
        monkeypatch.setattr(
            "custom_components.sa_emergency.coordinator.SaEmergencyApi.async_get_ims_incidents",
            AsyncMock(return_value=ims_return if ims_return is not None else []),
        )


async def _setup_entry(
    hass: HomeAssistant,
    monkeypatch,
    *,
    options: dict | None = None,
    ims_return=None,
    ims_side_effect=None,
) -> MockConfigEntry:
    _mock_ims_source(
        monkeypatch,
        ims_return=ims_return,
        ims_side_effect=ims_side_effect,
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
        ims_return=load_ims_attribute_records("ims_combined_features.json"),
    )

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)

    assert diagnostics["integration"]["version"] == "0.6.1"
    assert diagnostics["options"]["local_radius_km"] == 25.0
    assert diagnostics["sources"]["ims_incidents"]["status"] == "ok"
    assert diagnostics["sources"]["ims_incidents"]["url"] == IMS_INCIDENTS_URL
    assert diagnostics["sources"]["cfs"]["status"] == "ok"
    assert diagnostics["incidents"]["total_source"] == 2
    assert "last_successful_update" in diagnostics
    serialized = json.dumps(diagnostics)
    assert "features" not in serialized
    assert "Burn Off" not in serialized


async def test_diagnostics_setup_fails_when_ims_unavailable(
    hass: HomeAssistant, monkeypatch
) -> None:
    """Test integration setup fails when the IMS feed is unavailable."""
    _mock_ims_source(
        monkeypatch, ims_side_effect=SaEmergencyApiError("IMS unavailable")
    )
    entry = MockConfigEntry(domain=DOMAIN, data={}, unique_id=DOMAIN)
    entry.add_to_hass(hass)

    assert not await hass.config_entries.async_setup(entry.entry_id)


async def test_diagnostics_disabled_source(hass: HomeAssistant, monkeypatch) -> None:
    """Test diagnostics represent disabled sources explicitly."""
    entry = await _setup_entry(
        hass,
        monkeypatch,
        options={CONF_INCLUDE_CFS: True, CONF_INCLUDE_MFS: False},
        ims_return=load_ims_attribute_records("ims_combined_features.json"),
    )

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)

    assert diagnostics["options"]["include_mfs"] is False
    assert diagnostics["sources"]["mfs"]["status"] == SOURCE_STATUS_DISABLED
    assert diagnostics["sources"]["mfs"]["enabled"] is False


async def test_diagnostics_empty_feeds(hass: HomeAssistant, monkeypatch) -> None:
    """Test diagnostics with successful empty IMS feed."""
    entry = await _setup_entry(hass, monkeypatch, ims_return=[])

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)

    assert diagnostics["incidents"]["total_source"] == 0
    assert diagnostics["incidents"]["relevant"] == 0
    assert diagnostics["incidents"]["highest_relevance"] == "none"
    assert diagnostics["sources"]["ims_incidents"]["raw_count"] == 0


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
        ims_return=[],
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
        ims_return=load_ims_attribute_records("ims_cfs_onkaparinga_hills.json"),
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
        source=SOURCE_IMS_CURRENT_INCIDENTS,
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
                SOURCE_IMS_CURRENT_INCIDENTS: SourceStatus(status="ok", raw_count=1),
                SOURCE_CFS_CURRENT_INCIDENTS: SourceStatus(status="ok", raw_count=1),
                SOURCE_MFS_CURRENT_INCIDENTS: SourceStatus(status="ok", raw_count=0),
            },
        )

    payload = _build_diagnostics_payload(
        integration_version="0.6.1",
        coordinator=_CoordinatorStub(),  # type: ignore[arg-type]
    )

    serialized = json.dumps(payload)
    assert "Grass Fire" not in serialized
    assert payload["incidents"]["nearest_incident_id"] == "CFS:1"
    assert payload["sources"]["ims_incidents"]["url"] == IMS_INCIDENTS_URL
    assert "features" not in serialized
