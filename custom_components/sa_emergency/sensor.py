"""Sensor platform for the SA Emergency integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DEV_SENSOR_INCIDENT_SAMPLE_LIMIT,
    DOMAIN,
    NAME,
    SCAFFOLD_SENSOR_KEY,
    SOURCE_CFS_CURRENT_INCIDENTS,
    SOURCE_MFS_CURRENT_INCIDENTS,
)
from .coordinator import SaEmergencyConfigEntry, SaEmergencyDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SaEmergencyConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SA Emergency sensor entities."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([SaEmergencyDevelopmentSensor(coordinator, entry)])


class SaEmergencyDevelopmentSensor(
    CoordinatorEntity[SaEmergencyDataUpdateCoordinator], SensorEntity
):
    """Temporary development sensor for Milestone 3.

    This entity is not part of the final V1 sensor contract documented in
    docs/V1_SPEC.md and may change or be removed before release.
    """

    _attr_has_entity_name = True
    _attr_name = "Status"
    _attr_translation_key = "status"
    _attr_native_unit_of_measurement = "incidents"

    def __init__(
        self,
        coordinator: SaEmergencyDataUpdateCoordinator,
        entry: SaEmergencyConfigEntry,
    ) -> None:
        """Initialize the development sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_{SCAFFOLD_SENSOR_KEY}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": NAME,
            "manufacturer": "Mark Jones",
        }

    @property
    def native_value(self) -> int:
        """Return the total normalized incident count across all sources."""
        return len(self.coordinator.data.incidents)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return development diagnostics."""
        data = self.coordinator.data
        cfs_status = data.source_status.get(SOURCE_CFS_CURRENT_INCIDENTS)
        mfs_status = data.source_status.get(SOURCE_MFS_CURRENT_INCIDENTS)

        sample: list[dict[str, Any]] = []
        for incident in data.incidents[:DEV_SENSOR_INCIDENT_SAMPLE_LIMIT]:
            sample.append(incident.as_dict())

        attributes: dict[str, Any] = {
            "development_sensor": True,
            "total_normalized_incidents": len(data.incidents),
            "incident_sample": sample,
        }

        if cfs_status is not None:
            attributes["cfs"] = cfs_status.as_dict()
        if mfs_status is not None:
            attributes["mfs"] = mfs_status.as_dict()

        if data.last_successful_update is not None:
            attributes["last_successful_update"] = (
                data.last_successful_update.isoformat()
            )

        return attributes
