"""Sensor platform for the SA Emergency integration."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, NAME, SCAFFOLD_SENSOR_KEY
from .coordinator import SaEmergencyConfigEntry, SaEmergencyDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SaEmergencyConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SA Emergency sensor entities."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([SaEmergencyScaffoldSensor(coordinator, entry)])


class SaEmergencyScaffoldSensor(
    CoordinatorEntity[SaEmergencyDataUpdateCoordinator], SensorEntity
):
    """Temporary scaffold sensor for Milestone 1.

    This entity exists only to verify integration loading and coordinator wiring.
    It will be replaced by the planned stable V1 sensors documented in docs/V1_SPEC.md.
    """

    _attr_has_entity_name = True
    _attr_name = "Status"
    _attr_translation_key = "status"

    def __init__(
        self,
        coordinator: SaEmergencyDataUpdateCoordinator,
        entry: SaEmergencyConfigEntry,
    ) -> None:
        """Initialize the scaffold sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_{SCAFFOLD_SENSOR_KEY}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": NAME,
            "manufacturer": "AgriAutomation",
        }

    @property
    def native_value(self) -> str:
        """Return scaffold status."""
        return str(self.coordinator.data.get("status", "unknown"))

    @property
    def extra_state_attributes(self) -> dict[str, str | float | bool | list[str]]:
        """Return scaffold diagnostic attributes."""
        data = self.coordinator.data
        return {
            "scaffold": data.get("scaffold", True),
            "message": data.get("message", ""),
            "reference_latitude": data.get("reference_latitude"),
            "reference_longitude": data.get("reference_longitude"),
            "last_checked": data.get("last_checked"),
            "incident_count": len(data.get("incidents", [])),
        }
