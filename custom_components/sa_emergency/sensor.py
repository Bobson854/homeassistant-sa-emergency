"""Sensor platform for the SA Emergency integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DEFAULT_LOCAL_RADIUS_KM,
    DEFAULT_REGIONAL_RADIUS_KM,
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
    """Temporary development sensor for Milestone 4.

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
        """Return the count of geographically relevant incidents."""
        return len(self.coordinator.data.incidents_relevant)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return development diagnostics."""
        data = self.coordinator.data
        cfs_status = data.source_status.get(SOURCE_CFS_CURRENT_INCIDENTS)
        mfs_status = data.source_status.get(SOURCE_MFS_CURRENT_INCIDENTS)

        sample: list[dict[str, Any]] = []
        for incident in data.incidents_relevant[:DEV_SENSOR_INCIDENT_SAMPLE_LIMIT]:
            sample.append(
                {
                    "incident_id": incident.incident_id,
                    "agency": incident.agency,
                    "incident_type": incident.incident_type,
                    "distance_km": incident.distance_km,
                    "bearing_degrees": incident.bearing_degrees,
                    "bearing_cardinal": incident.bearing_cardinal,
                    "relevance": incident.relevance,
                }
            )

        attributes: dict[str, Any] = {
            "development_sensor": True,
            "total_source_incidents": len(data.incidents_all),
            "relevant_incidents": len(data.incidents_relevant),
            "local_incidents": len(data.incidents_local),
            "regional_incidents": len(data.incidents_regional),
            "non_relevant_incidents": data.non_relevant_incident_count,
            "non_spatial_incidents": data.non_spatial_incident_count,
            "highest_relevance": data.highest_relevance,
            "local_radius_km": DEFAULT_LOCAL_RADIUS_KM,
            "regional_radius_km": DEFAULT_REGIONAL_RADIUS_KM,
            "incident_sample": sample,
        }

        if data.nearest_incident is not None:
            attributes["nearest_incident_id"] = data.nearest_incident.incident_id

        if cfs_status is not None:
            attributes["cfs"] = cfs_status.as_dict()
        if mfs_status is not None:
            attributes["mfs"] = mfs_status.as_dict()

        if data.last_successful_update is not None:
            attributes["last_successful_update"] = (
                data.last_successful_update.isoformat()
            )

        return attributes
