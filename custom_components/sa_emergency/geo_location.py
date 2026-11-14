"""Geolocation platform for SA Emergency incident map markers."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.geo_location import GeolocationEvent
from homeassistant.const import UnitOfLength
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import SaEmergencyConfigEntry, SaEmergencyDataUpdateCoordinator
from .models import Incident
from .presentation import (
    incident_geolocation_name,
    incident_to_geolocation_attributes,
)

_LOGGER = logging.getLogger(__name__)


def _marker_incidents(coordinator: SaEmergencyDataUpdateCoordinator) -> list[Incident]:
    """Return relevant incidents that qualify for map markers."""
    if coordinator.data is None:
        return []
    return [
        incident
        for incident in coordinator.data.incidents_relevant
        if incident.latitude is not None and incident.longitude is not None
    ]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SaEmergencyConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up geolocation entities from the shared incident coordinator."""
    coordinator: SaEmergencyDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    manager = SaEmergencyGeolocationManager(
        coordinator,
        entry.entry_id,
        async_add_entities,
    )
    coordinator._geo_location_manager = manager

    @callback
    def _handle_coordinator_update() -> None:
        hass.async_create_task(manager.async_sync_from_coordinator())

    entry.async_on_unload(coordinator.async_add_listener(_handle_coordinator_update))
    await manager.async_sync_from_coordinator()


class SaEmergencyGeolocationManager:
    """Create, update, and remove incident geolocation entities."""

    def __init__(
        self,
        coordinator: SaEmergencyDataUpdateCoordinator,
        entry_id: str,
        async_add_entities: AddEntitiesCallback,
    ) -> None:
        self._coordinator = coordinator
        self._entry_id = entry_id
        self._async_add_entities = async_add_entities
        self._entities: dict[str, SaEmergencyIncidentGeolocation] = {}

    async def async_sync_from_coordinator(self) -> None:
        """Align geolocation entities with current coordinator data."""
        current = {
            incident.incident_id: incident
            for incident in _marker_incidents(self._coordinator)
        }
        current_ids = set(current)

        for incident_id in list(self._entities):
            if incident_id not in current_ids:
                entity = self._entities.pop(incident_id)
                await self._async_remove_entity(entity)

        new_entities: list[SaEmergencyIncidentGeolocation] = []
        for incident_id, incident in current.items():
            entity = self._entities.get(incident_id)
            if entity is None:
                entity = SaEmergencyIncidentGeolocation(
                    self._coordinator,
                    self._entry_id,
                    incident_id,
                )
                self._entities[incident_id] = entity
                new_entities.append(entity)
            else:
                entity.update_from_incident(incident)
                entity.async_write_ha_state()

        if new_entities:
            for entity in new_entities:
                entity.update_from_incident(current[entity._incident_id])
            self._async_add_entities(new_entities, update_before_add=True)

    async def _async_remove_entity(
        self, entity: SaEmergencyIncidentGeolocation
    ) -> None:
        """Remove a marker from Home Assistant state and the entity registry."""
        entity_id = entity.entity_id
        await entity.async_remove(force_remove=True)
        if not entity_id:
            return
        registry = er.async_get(self._coordinator.hass)
        if registry.async_get(entity_id):
            registry.async_remove(entity_id)


class SaEmergencyIncidentGeolocation(GeolocationEvent):
    """Map marker for one relevant SA Emergency incident."""

    _attr_should_poll = False
    _attr_source = DOMAIN
    _attr_unit_of_measurement = UnitOfLength.KILOMETERS

    def __init__(
        self,
        coordinator: SaEmergencyDataUpdateCoordinator,
        entry_id: str,
        incident_id: str,
    ) -> None:
        """Initialize a geolocation entity for one incident id."""
        self._coordinator = coordinator
        self._incident_id = incident_id
        self._attr_unique_id = f"{entry_id}_{incident_id}"
        self._attr_name = incident_id
        self._extra_attrs: dict[str, Any] = {}
        self.update_from_incident(None)

    def update_from_incident(self, incident: Incident | None) -> None:
        """Apply normalized incident fields to this entity."""
        if incident is None:
            incident = self._find_incident()
        if incident is None:
            return
        self._attr_name = incident_geolocation_name(incident)
        self._attr_distance = incident.distance_km
        self._attr_latitude = incident.latitude
        self._attr_longitude = incident.longitude
        self._extra_attrs = incident_to_geolocation_attributes(incident)

    def _find_incident(self) -> Incident | None:
        if self._coordinator.data is None:
            return None
        for incident in self._coordinator.data.incidents_relevant:
            if incident.incident_id != self._incident_id:
                continue
            if incident.latitude is None or incident.longitude is None:
                return None
            return incident
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return incident details for map pop-ups."""
        return self._extra_attrs
