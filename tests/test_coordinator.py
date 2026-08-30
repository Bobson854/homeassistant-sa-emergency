"""Tests for the SA Emergency coordinator."""

from unittest.mock import AsyncMock

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry
from tests.fixtures import load_json_fixture

from custom_components.sa_emergency.const import (
    DOMAIN,
    SOURCE_CFS_CURRENT_INCIDENTS,
    SOURCE_STATUS_OK,
)
from custom_components.sa_emergency.coordinator import SaEmergencyDataUpdateCoordinator


async def test_coordinator_normalizes_cfs_records(hass: HomeAssistant) -> None:
    """Test the coordinator stores normalized CFS incidents."""
    entry = MockConfigEntry(domain=DOMAIN, data={}, unique_id=DOMAIN)
    entry.add_to_hass(hass)

    coordinator = SaEmergencyDataUpdateCoordinator(hass, entry)
    coordinator.api.async_get_cfs_incidents = AsyncMock(  # type: ignore[method-assign]
        return_value=load_json_fixture("cfs_valid_multiple.json")
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
    entry = MockConfigEntry(domain=DOMAIN, data={}, unique_id=DOMAIN)
    entry.add_to_hass(hass)

    payload = [*load_json_fixture("cfs_valid_single.json"), {"Type": "Grass Fire"}]
    coordinator = SaEmergencyDataUpdateCoordinator(hass, entry)
    coordinator.api.async_get_cfs_incidents = AsyncMock(  # type: ignore[method-assign]
        return_value=payload
    )

    await coordinator.async_refresh()

    assert len(coordinator.data.incidents) == 1
    status = coordinator.data.source_status[SOURCE_CFS_CURRENT_INCIDENTS]
    assert status.skipped_count == 1
