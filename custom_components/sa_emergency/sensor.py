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
    SOURCE_STATUS_OK,
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
    """Temporary development sensor for Milestone 2.

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
            "manufacturer": "AgriAutomation",
        }

    @property
    def native_value(self) -> int:
        """Return the normalized CFS incident count."""
        return len(self.coordinator.data.incidents)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return development diagnostics."""
        data = self.coordinator.data
        cfs_status = data.source_status.get(SOURCE_CFS_CURRENT_INCIDENTS)
        sample = [
            incident.as_dict()
            for incident in data.incidents[:DEV_SENSOR_INCIDENT_SAMPLE_LIMIT]
        ]

        attributes: dict[str, Any] = {
            "development_sensor": True,
            "source": "CFS",
            "source_status": cfs_status.status if cfs_status else SOURCE_STATUS_OK,
            "raw_incident_count": cfs_status.raw_count if cfs_status else 0,
            "normalized_incident_count": len(data.incidents),
            "skipped_record_count": cfs_status.skipped_count if cfs_status else 0,
            "incident_sample": sample,
        }

        if data.last_successful_update is not None:
            attributes["last_successful_update"] = (
                data.last_successful_update.isoformat()
            )

        return attributes
