"""Tests for the SA Emergency coordinator."""

from unittest.mock import AsyncMock

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed
from pytest_homeassistant_custom_component.common import MockConfigEntry
from tests.ims_helpers import ims_cfs_record, ims_mfs_record, load_ims_attribute_records

from custom_components.sa_emergency.api import SaEmergencyApiError
from custom_components.sa_emergency.const import (
    CONF_INCLUDE_CFS,
    CONF_INCLUDE_MFS,
    CONF_LOCAL_RADIUS_KM,
    CONF_REGIONAL_RADIUS_KM,
    DOMAIN,
    SOURCE_CFS_CURRENT_INCIDENTS,
    SOURCE_IMS_CURRENT_INCIDENTS,
    SOURCE_MFS_CURRENT_INCIDENTS,
    SOURCE_STATUS_DISABLED,
    SOURCE_STATUS_OK,
)
from custom_components.sa_emergency.coordinator import SaEmergencyDataUpdateCoordinator


def _setup_coordinator(
    hass: HomeAssistant,
    *,
    ims_return: list[dict] | None = None,
    ims_side_effect: Exception | None = None,
    options: dict | None = None,
) -> SaEmergencyDataUpdateCoordinator:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={},
        unique_id=DOMAIN,
        options=options or {},
    )
    entry.add_to_hass(hass)
    coordinator = SaEmergencyDataUpdateCoordinator(hass, entry)

    if ims_side_effect is not None:
        coordinator.api.async_get_ims_incidents = AsyncMock(  # type: ignore[method-assign]
            side_effect=ims_side_effect
        )
    else:
        coordinator.api.async_get_ims_incidents = AsyncMock(  # type: ignore[method-assign]
            return_value=ims_return if ims_return is not None else []
        )

    return coordinator


async def test_coordinator_normalizes_ims_records(hass: HomeAssistant) -> None:
    """Test the coordinator stores normalized IMS incidents."""
    coordinator = _setup_coordinator(
        hass,
        ims_return=[
            ims_cfs_record(ident="CFS1"),
            ims_cfs_record(ident="CFS2"),
        ],
    )

    await coordinator.async_refresh()

    assert len(coordinator.data.incidents) == 2
    status = coordinator.data.source_status[SOURCE_CFS_CURRENT_INCIDENTS]
    assert status.status == SOURCE_STATUS_OK
    assert status.raw_count == 2
    assert status.normalized_count == 2
    assert status.skipped_count == 0
    ims_status = coordinator.data.source_status[SOURCE_IMS_CURRENT_INCIDENTS]
    assert ims_status.status == SOURCE_STATUS_OK
    assert ims_status.raw_count == 2
    assert coordinator.data.last_successful_update is not None


async def test_coordinator_skips_records_without_identity(hass: HomeAssistant) -> None:
    """Test records without ident are skipped without failing the update."""
    coordinator = _setup_coordinator(
        hass,
        ims_return=[
            ims_cfs_record(ident="CFS1"),
            {
                "authority": "South Australian Country Fire Service",
                "event": "Grass Fire",
            },
        ],
    )

    await coordinator.async_refresh()

    assert len(coordinator.data.incidents) == 1
    status = coordinator.data.source_status[SOURCE_CFS_CURRENT_INCIDENTS]
    assert status.skipped_count == 1


async def test_coordinator_both_agencies_from_combined_feed(
    hass: HomeAssistant,
) -> None:
    """Test CFS and MFS incidents from one IMS response merge correctly."""
    coordinator = _setup_coordinator(
        hass,
        ims_return=load_ims_attribute_records("ims_combined_features.json"),
    )

    await coordinator.async_refresh()

    assert len(coordinator.data.incidents) == 2
    assert len(coordinator.data.cfs_incidents) == 1
    assert len(coordinator.data.mfs_incidents) == 1


async def test_coordinator_ims_failure_fails_update(hass: HomeAssistant) -> None:
    """Test IMS transport failure fails the coordinator refresh."""
    coordinator = _setup_coordinator(
        hass,
        ims_side_effect=SaEmergencyApiError("IMS unavailable"),
    )

    with pytest.raises(UpdateFailed, match="IMS incident feed unavailable"):
        await coordinator._async_update_data()


async def test_coordinator_both_empty_successful(hass: HomeAssistant) -> None:
    """Test empty successful feeds are not treated as source failures."""
    coordinator = _setup_coordinator(hass, ims_return=[])

    await coordinator.async_refresh()

    assert coordinator.data.incidents == []
    assert (
        coordinator.data.source_status[SOURCE_CFS_CURRENT_INCIDENTS].status
        == SOURCE_STATUS_OK
    )
    assert (
        coordinator.data.source_status[SOURCE_MFS_CURRENT_INCIDENTS].status
        == SOURCE_STATUS_OK
    )
    assert coordinator.data.last_successful_update is not None


async def test_coordinator_cfs_only_in_feed(hass: HomeAssistant) -> None:
    """Test feed with only CFS records yields zero MFS count."""
    coordinator = _setup_coordinator(
        hass,
        ims_return=[ims_cfs_record(ident="CFS1")],
    )

    await coordinator.async_refresh()

    assert len(coordinator.data.cfs_incidents) == 1
    assert coordinator.data.mfs_incidents == []
    assert coordinator.data.source_status[SOURCE_MFS_CURRENT_INCIDENTS].raw_count == 0


async def test_coordinator_mfs_only_in_feed(hass: HomeAssistant) -> None:
    """Test feed with only MFS records yields zero CFS count."""
    coordinator = _setup_coordinator(
        hass,
        ims_return=[ims_mfs_record(ident="MFS1")],
    )

    await coordinator.async_refresh()

    assert coordinator.data.cfs_incidents == []
    assert len(coordinator.data.mfs_incidents) == 1


async def test_coordinator_malformed_and_unknown_authority_records(
    hass: HomeAssistant,
) -> None:
    """Test malformed and unknown-authority records are skipped."""
    coordinator = _setup_coordinator(
        hass,
        ims_return=load_ims_attribute_records("ims_mixed_valid_invalid_features.json"),
    )

    await coordinator.async_refresh()

    assert len(coordinator.data.cfs_incidents) == 1
    assert len(coordinator.data.mfs_incidents) == 1
    ims_status = coordinator.data.source_status[SOURCE_IMS_CURRENT_INCIDENTS]
    assert ims_status.skipped_count >= 2


async def test_coordinator_classifies_local_incident(hass: HomeAssistant) -> None:
    """Test an incident near the HA location is classified as local."""
    coordinator = _setup_coordinator(
        hass,
        ims_return=[
            ims_cfs_record(
                ident="LOCAL1",
                lat=-34.95,
                long=138.60,
                location="LOCAL",
            )
        ],
    )

    await coordinator.async_refresh()

    assert len(coordinator.data.incidents_local) == 1
    assert coordinator.data.incidents_local[0].relevance == "local"
    assert coordinator.data.highest_relevance == "local"


async def test_coordinator_classifies_regional_incident(hass: HomeAssistant) -> None:
    """Test an incident within regional radius is classified as regional."""
    coordinator = _setup_coordinator(
        hass,
        ims_return=[
            ims_cfs_record(
                ident="REG1",
                lat=-35.1234,
                long=139.5678,
            )
        ],
    )

    await coordinator.async_refresh()

    assert len(coordinator.data.incidents_regional) == 1
    assert coordinator.data.incidents_local == []
    assert coordinator.data.highest_relevance == "regional"


async def test_coordinator_retains_outside_radius_in_all(hass: HomeAssistant) -> None:
    """Test distant incidents remain in incidents_all but not relevant sets."""
    coordinator = _setup_coordinator(
        hass,
        ims_return=[
            ims_cfs_record(
                ident="FAR1",
                lat=-37.831,
                long=140.779,
            )
        ],
    )

    await coordinator.async_refresh()

    assert len(coordinator.data.incidents_all) == 1
    assert coordinator.data.incidents_relevant == []
    assert coordinator.data.incidents_all[0].relevance == "none"


async def test_coordinator_non_spatial_incident_non_relevant(
    hass: HomeAssistant,
) -> None:
    """Test non-spatial incidents are retained but not geographically relevant."""
    coordinator = _setup_coordinator(
        hass,
        ims_return=[
            ims_cfs_record(ident="NOCOORD", lat="invalid", long="invalid"),
        ],
    )

    await coordinator.async_refresh()

    assert len(coordinator.data.incidents_all) == 1
    assert coordinator.data.incidents_relevant == []
    assert coordinator.data.non_spatial_incident_count == 1
    assert coordinator.data.highest_relevance == "none"


async def test_coordinator_nearest_incident_from_relevant_only(
    hass: HomeAssistant,
) -> None:
    """Test nearest incident ignores outside-radius and non-spatial incidents."""
    coordinator = _setup_coordinator(
        hass,
        ims_return=[
            ims_cfs_record(ident="LOCAL1", lat=-34.95, long=138.60),
            ims_cfs_record(ident="FAR1", lat=-37.831, long=140.779),
        ],
    )

    await coordinator.async_refresh()

    assert coordinator.data.nearest_incident is not None
    assert coordinator.data.nearest_incident.incident_id == "CFS:LOCAL1"


async def test_coordinator_exact_local_boundary(hass: HomeAssistant) -> None:
    """Test approximately 25 km north remains local using full-precision distance."""
    from custom_components.sa_emergency.geo import calculate_distance_km

    target_lat = hass.config.latitude + (25.0 / 111.32)
    target_lon = hass.config.longitude
    distance = calculate_distance_km(
        hass.config.latitude,
        hass.config.longitude,
        target_lat,
        target_lon,
    )
    assert distance <= 25.0

    coordinator = _setup_coordinator(
        hass,
        ims_return=[
            ims_cfs_record(ident="BOUNDARY", lat=target_lat, long=target_lon),
        ],
    )

    await coordinator.async_refresh()

    assert len(coordinator.data.incidents_local) == 1
    assert coordinator.data.incidents_local[0].relevance == "local"


async def test_coordinator_uses_hass_config_location(hass: HomeAssistant) -> None:
    """Test geographic processing uses Home Assistant config coordinates."""
    hass.config.latitude = -35.0
    hass.config.longitude = 139.0

    coordinator = _setup_coordinator(
        hass,
        ims_return=[ims_cfs_record(ident="HOME", lat=-35.0, long=139.0)],
    )

    await coordinator.async_refresh()

    incident = coordinator.data.incidents_all[0]
    assert incident.distance_km == 0.0
    assert incident.bearing_degrees is None


async def test_coordinator_missing_home_location_fails(hass: HomeAssistant) -> None:
    """Test coordinator fails clearly when HA location is unavailable."""
    hass.config.latitude = None
    hass.config.longitude = None
    coordinator = _setup_coordinator(
        hass,
        ims_return=[ims_cfs_record(ident="CFS1")],
    )

    with pytest.raises(UpdateFailed, match="Home Assistant location is not configured"):
        await coordinator._async_update_data()


async def test_coordinator_only_non_spatial_incidents(hass: HomeAssistant) -> None:
    """Test successful update with only non-spatial incidents."""
    coordinator = _setup_coordinator(
        hass,
        ims_return=[ims_cfs_record(ident="NOCOORD", lat=None, long=None)],
    )

    await coordinator.async_refresh()

    assert len(coordinator.data.incidents_all) == 1
    assert coordinator.data.incidents_relevant == []
    assert coordinator.data.highest_relevance == "none"
    assert coordinator.data.last_successful_update is not None


async def test_coordinator_custom_radii_alter_classification(
    hass: HomeAssistant,
) -> None:
    """Test configured radii change relevance classification."""
    coordinator = _setup_coordinator(
        hass,
        ims_return=[ims_cfs_record(ident="REG1", lat=-35.1234, long=139.5678)],
        options={
            CONF_LOCAL_RADIUS_KM: 200.0,
            CONF_REGIONAL_RADIUS_KM: 250.0,
        },
    )

    await coordinator.async_refresh()

    assert len(coordinator.data.incidents_local) == 1
    assert coordinator.data.incidents_regional == []


async def test_coordinator_custom_scan_interval(hass: HomeAssistant) -> None:
    """Test configured polling interval sets coordinator update interval."""
    from datetime import timedelta

    from homeassistant.const import CONF_SCAN_INTERVAL

    coordinator = _setup_coordinator(
        hass,
        options={CONF_SCAN_INTERVAL: 300},
    )

    assert coordinator.update_interval == timedelta(seconds=300)


async def test_coordinator_disabled_cfs_filters_after_single_fetch(
    hass: HomeAssistant,
) -> None:
    """Test disabled CFS still uses one IMS fetch but excludes CFS incidents."""
    ims_mock = AsyncMock(
        return_value=load_ims_attribute_records("ims_combined_features.json")
    )
    coordinator = _setup_coordinator(
        hass,
        options={CONF_INCLUDE_CFS: False, CONF_INCLUDE_MFS: True},
    )
    coordinator.api.async_get_ims_incidents = ims_mock  # type: ignore[method-assign]

    await coordinator.async_refresh()

    ims_mock.assert_called_once()
    assert (
        coordinator.data.source_status[SOURCE_CFS_CURRENT_INCIDENTS].status
        == SOURCE_STATUS_DISABLED
    )
    assert len(coordinator.data.mfs_incidents) == 1
    assert coordinator.data.cfs_incidents == []


async def test_coordinator_disabled_mfs_filters_after_single_fetch(
    hass: HomeAssistant,
) -> None:
    """Test disabled MFS still uses one IMS fetch but excludes MFS incidents."""
    ims_mock = AsyncMock(
        return_value=load_ims_attribute_records("ims_combined_features.json")
    )
    coordinator = _setup_coordinator(
        hass,
        options={CONF_INCLUDE_CFS: True, CONF_INCLUDE_MFS: False},
    )
    coordinator.api.async_get_ims_incidents = ims_mock  # type: ignore[method-assign]

    await coordinator.async_refresh()

    ims_mock.assert_called_once()
    assert (
        coordinator.data.source_status[SOURCE_MFS_CURRENT_INCIDENTS].status
        == SOURCE_STATUS_DISABLED
    )
    assert len(coordinator.data.cfs_incidents) == 1
    assert coordinator.data.mfs_incidents == []


async def test_coordinator_only_enabled_source_failure_fails(
    hass: HomeAssistant,
) -> None:
    """Test failure of the IMS feed fails the update when only CFS is enabled."""
    coordinator = _setup_coordinator(
        hass,
        ims_side_effect=SaEmergencyApiError("IMS unavailable"),
        options={CONF_INCLUDE_CFS: True, CONF_INCLUDE_MFS: False},
    )

    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()
