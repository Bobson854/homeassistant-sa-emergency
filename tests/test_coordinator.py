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
