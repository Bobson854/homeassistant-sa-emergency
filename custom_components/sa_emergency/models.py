"""Normalized incident models for the SA Emergency integration."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any

from .const import SOURCE_CFS_CURRENT_INCIDENTS


@dataclass(slots=True)
class Incident:
    """Normalized emergency incident shared across agencies."""

    incident_id: str
    agency: str
    incident_type: str | None
    status: str | None
    level: str | None
    first_reported: datetime | None
    location_name: str | None
    latitude: float | None
    longitude: float | None
    region: str | None
    fire_ban_district: str | None
    resources: int | None
    aircraft_count: int | None
    message: str | None
    message_url: str | None
    distance_km: float | None = None
    bearing_degrees: float | None = None
    bearing_cardinal: str | None = None
    relevance: str | None = None
    source: str = SOURCE_CFS_CURRENT_INCIDENTS

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation for sensor attributes."""
        data = asdict(self)
        if self.first_reported is not None:
            data["first_reported"] = self.first_reported.isoformat()
        return data


@dataclass(slots=True)
class SourceStatus:
    """Runtime status for an incident source feed."""

    status: str
    raw_count: int = 0
    normalized_count: int = 0
    skipped_count: int = 0
    error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation."""
        return asdict(self)


@dataclass(slots=True)
class SaEmergencyData:
    """Coordinator runtime data."""

    incidents: list[Incident] = field(default_factory=list)
    source_status: dict[str, SourceStatus] = field(default_factory=dict)
    last_successful_update: datetime | None = None

    @property
    def cfs_incidents(self) -> list[Incident]:
        """Return normalized CFS incidents."""
        return self.incidents
