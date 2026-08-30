"""Public Home Assistant presentation helpers."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .const import (
    SOURCE_CFS_CURRENT_INCIDENTS,
    SOURCE_MFS_CURRENT_INCIDENTS,
    SOURCE_STATUS_DISABLED,
    SOURCE_STATUS_ERROR,
)
from .models import Incident, SaEmergencyData, SourceStatus


def incident_to_public_dict(incident: Incident) -> dict[str, Any]:
    """Return the stable public attribute schema for one incident."""
    data: dict[str, Any] = {
        "incident_id": incident.incident_id,
        "agency": incident.agency,
    }

    _set_if_present(data, "type", incident.incident_type)
    _set_if_present(data, "status", incident.status)
    _set_if_present(data, "level", incident.level)
    _set_if_present(data, "location", incident.location_name)
    _set_if_present(data, "latitude", incident.latitude)
    _set_if_present(data, "longitude", incident.longitude)
    _set_if_present(data, "distance_km", incident.distance_km)
    _set_if_present(data, "bearing_degrees", incident.bearing_degrees)
    _set_if_present(data, "bearing", incident.bearing_cardinal)
    _set_if_present(data, "relevance", incident.relevance)
    _set_if_present(data, "region", incident.region)
    _set_if_present(data, "fire_ban_district", incident.fire_ban_district)
    _set_if_present(data, "resources", incident.resources)
    _set_if_present(data, "aircraft", incident.aircraft_count)
    _set_if_present(data, "message", incident.message)
    _set_if_present(data, "message_url", incident.message_url)

    if incident.first_reported is not None:
        data["first_reported"] = incident.first_reported.isoformat()

    return data


def nearest_incident_state(incident: Incident | None) -> str | None:
    """Return a concise human-facing state for the nearest incident sensor."""
    if incident is None:
        return None
    if incident.incident_type:
        return incident.incident_type
    if incident.location_name:
        return incident.location_name
    return incident.incident_id


def source_status_to_public_dict(status: SourceStatus | None) -> dict[str, Any]:
    """Return a sensor-safe public representation of one source status."""
    if status is None:
        return {"status": SOURCE_STATUS_ERROR, "enabled": True}

    data: dict[str, Any] = {
        "status": status.status,
        "enabled": status.enabled,
    }
    if status.status != SOURCE_STATUS_DISABLED:
        data["raw_count"] = status.raw_count
        data["normalized_count"] = status.normalized_count
        data["skipped_count"] = status.skipped_count
    if status.error is not None:
        data["error"] = status.error
    return data


def build_source_status_attributes(data: SaEmergencyData) -> dict[str, Any]:
    """Return public source status for all incident sources."""
    return {
        SOURCE_CFS_CURRENT_INCIDENTS: source_status_to_public_dict(
            data.source_status.get(SOURCE_CFS_CURRENT_INCIDENTS)
        ),
        SOURCE_MFS_CURRENT_INCIDENTS: source_status_to_public_dict(
            data.source_status.get(SOURCE_MFS_CURRENT_INCIDENTS)
        ),
    }


def format_last_successful_update(value: datetime | None) -> str | None:
    """Return an ISO timestamp for sensor attributes."""
    if value is None:
        return None
    return value.isoformat()


def _set_if_present(data: dict[str, Any], key: str, value: Any) -> None:
    if value is not None:
        data[key] = value
