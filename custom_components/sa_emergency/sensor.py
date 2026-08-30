"""Sensor platform for the SA Emergency integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    MAX_RELEVANT_INCIDENTS,
    NAME,
    RELEVANCE_LOCAL,
    RELEVANCE_NONE,
    RELEVANCE_REGIONAL,
    SENSOR_UNIQUE_CFS_INCIDENTS,
    SENSOR_UNIQUE_HIGHEST_RELEVANCE,
    SENSOR_UNIQUE_INCIDENTS,
    SENSOR_UNIQUE_LOCAL_INCIDENTS,
    SENSOR_UNIQUE_MFS_INCIDENTS,
    SENSOR_UNIQUE_NEAREST_INCIDENT,
    SENSOR_UNIQUE_REGIONAL_INCIDENTS,
    SOURCE_CFS_CURRENT_INCIDENTS,
    SOURCE_MFS_CURRENT_INCIDENTS,
    SOURCE_STATUS_ERROR,
)
from .coordinator import SaEmergencyConfigEntry, SaEmergencyDataUpdateCoordinator
from .models import SaEmergencyData, SourceStatus
from .options import SaEmergencyOptions
from .presentation import (
    build_source_status_attributes,
    format_last_successful_update,
    incident_to_public_dict,
    nearest_incident_state,
    source_status_to_public_dict,
)


@dataclass(frozen=True, kw_only=True)
class SaEmergencySensorEntityDescription(SensorEntityDescription):
    """Describe a standard SA Emergency coordinator sensor."""

    unique_id_suffix: str
    value_fn: Callable[[SaEmergencyData, SaEmergencyOptions], StateType]
    attributes_fn: (
        Callable[[SaEmergencyData, SaEmergencyOptions], dict[str, Any]] | None
    ) = None


def _device_info(entry_id: str) -> dict[str, Any]:
    return {
        "identifiers": {(DOMAIN, entry_id)},
        "name": NAME,
        "manufacturer": "Mark Jones",
    }


def _agency_count_value(
    data: SaEmergencyData,
    options: SaEmergencyOptions,
    *,
    include: bool,
    source_key: str,
    relevant_incidents: Callable[[SaEmergencyData], list],
) -> StateType:
    if not include:
        return None
    status = data.source_status.get(source_key)
    if status is not None and status.status == SOURCE_STATUS_ERROR:
        return None
    return len(relevant_incidents(data))


def _incidents_attributes(
    data: SaEmergencyData, options: SaEmergencyOptions
) -> dict[str, Any]:
    relevant = data.incidents_relevant
    exposed = relevant[:MAX_RELEVANT_INCIDENTS]
    attributes: dict[str, Any] = {
        "local_count": len(data.incidents_local),
        "regional_count": len(data.incidents_regional),
        "cfs_count": len(data.cfs_relevant_incidents),
        "mfs_count": len(data.mfs_relevant_incidents),
        "highest_relevance": data.highest_relevance,
        "source_status": build_source_status_attributes(data),
        "incidents": [incident_to_public_dict(incident) for incident in exposed],
        "incidents_exposed": len(exposed),
        "incidents_truncated": len(relevant) > MAX_RELEVANT_INCIDENTS,
    }
    if data.nearest_incident is not None:
        attributes["nearest_incident_id"] = data.nearest_incident.incident_id
    last_update = format_last_successful_update(data.last_successful_update)
    if last_update is not None:
        attributes["last_successful_update"] = last_update
    return attributes


def _local_attributes(
    data: SaEmergencyData, options: SaEmergencyOptions
) -> dict[str, Any]:
    attributes: dict[str, Any] = {"radius_km": options.local_radius_km}
    if data.incidents_local:
        attributes["nearest_incident_id"] = data.incidents_local[0].incident_id
    return attributes


def _regional_attributes(
    data: SaEmergencyData, options: SaEmergencyOptions
) -> dict[str, Any]:
    return {"radius_km": options.regional_radius_km}


def _agency_attributes(
    data: SaEmergencyData,
    options: SaEmergencyOptions,
    *,
    include: bool,
    source_key: str,
) -> dict[str, Any]:
    status = data.source_status.get(source_key)
    return source_status_to_public_dict(
        status
        if status is not None
        else SourceStatus(status=SOURCE_STATUS_ERROR, enabled=include)
    )


INCIDENT_SENSOR_DESCRIPTIONS: tuple[SaEmergencySensorEntityDescription, ...] = (
    SaEmergencySensorEntityDescription(
        key="incidents",
        translation_key="incidents",
        unique_id_suffix=SENSOR_UNIQUE_INCIDENTS,
        icon="mdi:alert",
        value_fn=lambda data, _options: len(data.incidents_relevant),
        attributes_fn=_incidents_attributes,
    ),
    SaEmergencySensorEntityDescription(
        key="local_incidents",
        translation_key="local_incidents",
        unique_id_suffix=SENSOR_UNIQUE_LOCAL_INCIDENTS,
        icon="mdi:map-marker-alert",
        value_fn=lambda data, _options: len(data.incidents_local),
        attributes_fn=_local_attributes,
    ),
    SaEmergencySensorEntityDescription(
        key="regional_incidents",
        translation_key="regional_incidents",
        unique_id_suffix=SENSOR_UNIQUE_REGIONAL_INCIDENTS,
        icon="mdi:map-marker-radius",
        value_fn=lambda data, _options: len(data.incidents_regional),
        attributes_fn=_regional_attributes,
    ),
    SaEmergencySensorEntityDescription(
        key="cfs_incidents",
        translation_key="cfs_incidents",
        unique_id_suffix=SENSOR_UNIQUE_CFS_INCIDENTS,
        icon="mdi:fire-truck",
        value_fn=lambda data, options: _agency_count_value(
            data,
            options,
            include=options.include_cfs,
            source_key=SOURCE_CFS_CURRENT_INCIDENTS,
            relevant_incidents=lambda item: item.cfs_relevant_incidents,
        ),
        attributes_fn=lambda data, options: _agency_attributes(
            data,
            options,
            include=options.include_cfs,
            source_key=SOURCE_CFS_CURRENT_INCIDENTS,
        ),
    ),
    SaEmergencySensorEntityDescription(
        key="mfs_incidents",
        translation_key="mfs_incidents",
        unique_id_suffix=SENSOR_UNIQUE_MFS_INCIDENTS,
        icon="mdi:fire",
        value_fn=lambda data, options: _agency_count_value(
            data,
            options,
            include=options.include_mfs,
            source_key=SOURCE_MFS_CURRENT_INCIDENTS,
            relevant_incidents=lambda item: item.mfs_relevant_incidents,
        ),
        attributes_fn=lambda data, options: _agency_attributes(
            data,
            options,
            include=options.include_mfs,
            source_key=SOURCE_MFS_CURRENT_INCIDENTS,
        ),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SaEmergencyConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SA Emergency sensor entities."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SensorEntity] = [
        SaEmergencyDescriptionSensor(coordinator, entry, description)
        for description in INCIDENT_SENSOR_DESCRIPTIONS
    ]
    entities.append(SaEmergencyNearestIncidentSensor(coordinator, entry))
    entities.append(SaEmergencyHighestRelevanceSensor(coordinator, entry))
    async_add_entities(entities)


class SaEmergencyDescriptionSensor(
    CoordinatorEntity[SaEmergencyDataUpdateCoordinator], SensorEntity
):
    """Coordinator-backed SA Emergency sensor driven by an entity description."""

    _attr_has_entity_name = True
    entity_description: SaEmergencySensorEntityDescription

    def __init__(
        self,
        coordinator: SaEmergencyDataUpdateCoordinator,
        entry: SaEmergencyConfigEntry,
        description: SaEmergencySensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.unique_id_suffix}"
        self._attr_device_info = _device_info(entry.entry_id)

    @property
    def native_value(self) -> StateType:
        """Return the sensor state."""
        return self.entity_description.value_fn(
            self.coordinator.data,
            self.coordinator.options,
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return optional sensor attributes."""
        if self.entity_description.attributes_fn is None:
            return None
        return self.entity_description.attributes_fn(
            self.coordinator.data,
            self.coordinator.options,
        )


class SaEmergencyNearestIncidentSensor(
    CoordinatorEntity[SaEmergencyDataUpdateCoordinator], SensorEntity
):
    """Expose the nearest relevant incident."""

    _attr_has_entity_name = True
    _attr_translation_key = "nearest_incident"
    _attr_icon = "mdi:map-marker-distance"

    def __init__(
        self,
        coordinator: SaEmergencyDataUpdateCoordinator,
        entry: SaEmergencyConfigEntry,
    ) -> None:
        """Initialize the nearest incident sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_{SENSOR_UNIQUE_NEAREST_INCIDENT}"
        self._attr_device_info = _device_info(entry.entry_id)

    @property
    def native_value(self) -> StateType:
        """Return a human-readable nearest incident label."""
        return nearest_incident_state(self.coordinator.data.nearest_incident)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return the nearest incident public representation."""
        incident = self.coordinator.data.nearest_incident
        if incident is None:
            return None
        return incident_to_public_dict(incident)


class SaEmergencyHighestRelevanceSensor(
    CoordinatorEntity[SaEmergencyDataUpdateCoordinator], SensorEntity
):
    """Expose the highest current relevance classification."""

    _attr_has_entity_name = True
    _attr_translation_key = "highest_relevance"
    _attr_icon = "mdi:alert-circle"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options: tuple[str, ...] = (
        RELEVANCE_NONE,
        RELEVANCE_REGIONAL,
        RELEVANCE_LOCAL,
    )

    def __init__(
        self,
        coordinator: SaEmergencyDataUpdateCoordinator,
        entry: SaEmergencyConfigEntry,
    ) -> None:
        """Initialize the highest relevance sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_{SENSOR_UNIQUE_HIGHEST_RELEVANCE}"
        self._attr_device_info = _device_info(entry.entry_id)

    @property
    def native_value(self) -> StateType:
        """Return the highest relevance state."""
        return self.coordinator.data.highest_relevance
