"""Tests for the SA Emergency coordinator."""

from unittest.mock import AsyncMock

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed
from pytest_homeassistant_custom_component.common import MockConfigEntry
from tests.fixtures import load_json_fixture

from custom_components.sa_emergency.api import SaEmergencyApiError
from custom_components.sa_emergency.const import (
    DOMAIN,
    SOURCE_CFS_CURRENT_INCIDENTS,
    SOURCE_MFS_CURRENT_INCIDENTS,
    SOURCE_STATUS_ERROR,
    SOURCE_STATUS_OK,
)
from custom_components.sa_emergency.coordinator import SaEmergencyDataUpdateCoordinator


def _mfs_attributes_records(fixture_name: str) -> list[dict]:
    records: list[dict] = []
    for feature in load_json_fixture(fixture_name)["features"]:
        if isinstance(feature, dict) and isinstance(feature.get("attributes"), dict):
            records.append(feature["attributes"])
    return records


def _setup_coordinator(
    hass: HomeAssistant,
    *,
    cfs_return: list[dict] | None = None,
    cfs_side_effect: Exception | None = None,
    mfs_return: list[dict] | None = None,
    mfs_side_effect: Exception | None = None,
) -> SaEmergencyDataUpdateCoordinator:
    entry = MockConfigEntry(domain=DOMAIN, data={}, unique_id=DOMAIN)
    entry.add_to_hass(hass)
    coordinator = SaEmergencyDataUpdateCoordinator(hass, entry)

    if cfs_side_effect is not None:
        coordinator.api.async_get_cfs_incidents = AsyncMock(  # type: ignore[method-assign]
            side_effect=cfs_side_effect
        )
    else:
        coordinator.api.async_get_cfs_incidents = AsyncMock(  # type: ignore[method-assign]
            return_value=cfs_return if cfs_return is not None else []
        )

    if mfs_side_effect is not None:
        coordinator.api.async_get_mfs_incidents = AsyncMock(  # type: ignore[method-assign]
            side_effect=mfs_side_effect
        )
    else:
        coordinator.api.async_get_mfs_incidents = AsyncMock(  # type: ignore[method-assign]
            return_value=mfs_return if mfs_return is not None else []
        )

    return coordinator


async def test_coordinator_normalizes_cfs_records(hass: HomeAssistant) -> None:
    """Test the coordinator stores normalized CFS incidents."""
    coordinator = _setup_coordinator(
        hass,
        cfs_return=load_json_fixture("cfs_valid_multiple.json"),
    )

    await coordinator.async_refresh()

    assert len(coordinator.data.incidents) == 2
    status = coordinator.data.source_status[SOURCE_CFS_CURRENT_INCIDENTS]
    assert status.status == SOURCE_STATUS_OK
    assert status.raw_count == 2
    assert status.normalized_count == 2
    assert status.skipped_count == 0
    assert coordinator.data.last_successful_update is not None


async def test_coordinator_skips_records_without_identity(hass: HomeAssistant) -> None:
    """Test records without IncidentNo are skipped without failing the update."""
    payload = [*load_json_fixture("cfs_valid_single.json"), {"Type": "Grass Fire"}]
    coordinator = _setup_coordinator(hass, cfs_return=payload)

    await coordinator.async_refresh()

    assert len(coordinator.data.incidents) == 1
    status = coordinator.data.source_status[SOURCE_CFS_CURRENT_INCIDENTS]
    assert status.skipped_count == 1


async def test_coordinator_both_sources_success(hass: HomeAssistant) -> None:
    """Test CFS and MFS incidents merge into one collection."""
    coordinator = _setup_coordinator(
        hass,
        cfs_return=load_json_fixture("cfs_valid_single.json"),
        mfs_return=_mfs_attributes_records("mfs_valid_single.json"),
    )

    await coordinator.async_refresh()

    assert len(coordinator.data.incidents) == 2
    assert len(coordinator.data.cfs_incidents) == 1
    assert len(coordinator.data.mfs_incidents) == 1
    assert (
        coordinator.data.source_status[SOURCE_CFS_CURRENT_INCIDENTS].status
        == SOURCE_STATUS_OK
    )
    assert (
        coordinator.data.source_status[SOURCE_MFS_CURRENT_INCIDENTS].status
        == SOURCE_STATUS_OK
    )


async def test_coordinator_cfs_success_mfs_failure(hass: HomeAssistant) -> None:
    """Test valid CFS data is retained when MFS fails."""
    coordinator = _setup_coordinator(
        hass,
        cfs_return=load_json_fixture("cfs_valid_single.json"),
        mfs_side_effect=SaEmergencyApiError("MFS unavailable"),
    )

    await coordinator.async_refresh()

    assert len(coordinator.data.cfs_incidents) == 1
    assert coordinator.data.mfs_incidents == []
    assert (
        coordinator.data.source_status[SOURCE_MFS_CURRENT_INCIDENTS].status
        == SOURCE_STATUS_ERROR
    )
    assert coordinator.data.last_successful_update is not None


async def test_coordinator_mfs_success_cfs_failure(hass: HomeAssistant) -> None:
    """Test valid MFS data is retained when CFS fails."""
    coordinator = _setup_coordinator(
        hass,
        cfs_side_effect=SaEmergencyApiError("CFS unavailable"),
        mfs_return=_mfs_attributes_records("mfs_valid_single.json"),
    )

    await coordinator.async_refresh()

    assert coordinator.data.cfs_incidents == []
    assert len(coordinator.data.mfs_incidents) == 1
    assert (
        coordinator.data.source_status[SOURCE_CFS_CURRENT_INCIDENTS].status
        == SOURCE_STATUS_ERROR
    )
    assert coordinator.data.last_successful_update is not None


async def test_coordinator_both_sources_failure(hass: HomeAssistant) -> None:
    """Test overall update fails only when both sources fail."""
    coordinator = _setup_coordinator(
        hass,
        cfs_side_effect=SaEmergencyApiError("CFS unavailable"),
        mfs_side_effect=SaEmergencyApiError("MFS unavailable"),
    )

    with pytest.raises(UpdateFailed, match="No current incident data"):
        await coordinator._async_update_data()


async def test_coordinator_both_empty_successful(hass: HomeAssistant) -> None:
    """Test empty successful feeds are not treated as source failures."""
    coordinator = _setup_coordinator(hass, cfs_return=[], mfs_return=[])

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


async def test_coordinator_empty_cfs_populated_mfs(hass: HomeAssistant) -> None:
    """Test populated MFS with empty CFS succeeds."""
    coordinator = _setup_coordinator(
        hass,
        cfs_return=[],
        mfs_return=_mfs_attributes_records("mfs_valid_multiple.json"),
    )

    await coordinator.async_refresh()

    assert coordinator.data.cfs_incidents == []
    assert len(coordinator.data.mfs_incidents) == 2


async def test_coordinator_populated_cfs_empty_mfs(hass: HomeAssistant) -> None:
    """Test populated CFS with empty MFS succeeds."""
    coordinator = _setup_coordinator(
        hass,
        cfs_return=load_json_fixture("cfs_valid_multiple.json"),
        mfs_return=[],
    )

    await coordinator.async_refresh()

    assert len(coordinator.data.cfs_incidents) == 2
    assert coordinator.data.mfs_incidents == []


async def test_coordinator_malformed_records_within_sources(
    hass: HomeAssistant,
) -> None:
    """Test malformed records in each source are skipped independently."""
    coordinator = _setup_coordinator(
        hass,
        cfs_return=[
            *load_json_fixture("cfs_valid_single.json"),
            {"Type": "Grass Fire"},
        ],
        mfs_return=_mfs_attributes_records("mfs_mixed_valid_invalid_features.json"),
    )

    await coordinator.async_refresh()

    assert len(coordinator.data.cfs_incidents) == 1
    assert len(coordinator.data.mfs_incidents) == 1
    assert (
        coordinator.data.source_status[SOURCE_CFS_CURRENT_INCIDENTS].skipped_count == 1
    )
    assert (
        coordinator.data.source_status[SOURCE_MFS_CURRENT_INCIDENTS].skipped_count == 1
    )


async def test_coordinator_classifies_local_incident(hass: HomeAssistant) -> None:
    """Test an incident near the HA location is classified as local."""
    coordinator = _setup_coordinator(
        hass,
        cfs_return=[
            {
                "IncidentNo": "LOCAL1",
                "Date": "30/08/2026",
                "Time": "14:30",
                "Type": "Grass Fire",
                "Status": "GOING",
                "Location": "-34.95,138.60",
            }
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
        cfs_return=load_json_fixture("cfs_valid_single.json"),
    )

    await coordinator.async_refresh()

    assert len(coordinator.data.incidents_regional) == 1
    assert coordinator.data.incidents_local == []
    assert coordinator.data.highest_relevance == "regional"


async def test_coordinator_retains_outside_radius_in_all(hass: HomeAssistant) -> None:
    """Test distant incidents remain in incidents_all but not relevant sets."""
    coordinator = _setup_coordinator(
        hass,
        cfs_return=[
            {
                "IncidentNo": "FAR1",
                "Date": "30/08/2026",
                "Time": "14:30",
                "Type": "Grass Fire",
                "Status": "GOING",
                "Location": "-37.831,140.779",
            }
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
        cfs_return=[
            {
                "IncidentNo": "NOCOORD",
                "Date": "30/08/2026",
                "Time": "14:30",
                "Type": "Grass Fire",
                "Status": "GOING",
                "Location": "invalid",
            }
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
        cfs_return=[
            {
                "IncidentNo": "LOCAL1",
                "Date": "30/08/2026",
                "Time": "14:30",
                "Type": "Grass Fire",
                "Status": "GOING",
                "Location": "-34.95,138.60",
            },
            {
                "IncidentNo": "FAR1",
                "Date": "30/08/2026",
                "Time": "14:30",
                "Type": "Grass Fire",
                "Status": "GOING",
                "Location": "-37.831,140.779",
            },
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
        cfs_return=[
            {
                "IncidentNo": "BOUNDARY",
                "Date": "30/08/2026",
                "Time": "14:30",
                "Type": "Grass Fire",
                "Status": "GOING",
                "Location": f"{target_lat},{target_lon}",
            }
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
        cfs_return=[
            {
                "IncidentNo": "HOME",
                "Date": "30/08/2026",
                "Time": "14:30",
                "Type": "Grass Fire",
                "Status": "GOING",
                "Location": "-35.0,139.0",
            }
        ],
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
        cfs_return=load_json_fixture("cfs_valid_single.json"),
    )

    with pytest.raises(UpdateFailed, match="Home Assistant location is not configured"):
        await coordinator._async_update_data()


async def test_coordinator_partial_failure_still_applies_geography(
    hass: HomeAssistant,
) -> None:
    """Test geography is applied to incidents from the successful source."""
    coordinator = _setup_coordinator(
        hass,
        cfs_return=load_json_fixture("cfs_valid_single.json"),
        mfs_side_effect=SaEmergencyApiError("MFS unavailable"),
    )

    await coordinator.async_refresh()

    assert len(coordinator.data.incidents_regional) == 1
    assert coordinator.data.mfs_incidents == []
    assert (
        coordinator.data.source_status[SOURCE_MFS_CURRENT_INCIDENTS].status
        == SOURCE_STATUS_ERROR
    )


async def test_coordinator_only_non_spatial_incidents(hass: HomeAssistant) -> None:
    """Test successful update with only non-spatial incidents."""
    coordinator = _setup_coordinator(
        hass,
        cfs_return=[
            {
                "IncidentNo": "NOCOORD",
                "Date": "30/08/2026",
                "Time": "14:30",
                "Type": "Grass Fire",
                "Status": "GOING",
            }
        ],
    )

    await coordinator.async_refresh()

    assert len(coordinator.data.incidents_all) == 1
    assert coordinator.data.incidents_relevant == []
    assert coordinator.data.highest_relevance == "none"
    assert coordinator.data.last_successful_update is not None
