"""Normalized incident models for the SA Emergency integration."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any

from .const import AGENCY_CFS, AGENCY_MFS, RELEVANCE_NONE


@dataclass(slots=True)
class Incident:
    """Normalized emergency incident shared across agencies."""

    incident_id: str
    agency: str
    source: str
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
    enabled: bool = True

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation."""
        return asdict(self)


@dataclass(slots=True)
class SaEmergencyData:
    """Coordinator runtime data."""

    incidents_all: list[Incident] = field(default_factory=list)
    incidents_relevant: list[Incident] = field(default_factory=list)
    incidents_local: list[Incident] = field(default_factory=list)
    incidents_regional: list[Incident] = field(default_factory=list)
    source_status: dict[str, SourceStatus] = field(default_factory=dict)
    last_successful_update: datetime | None = None
    nearest_incident: Incident | None = None
    highest_relevance: str = RELEVANCE_NONE

    @property
    def incidents(self) -> list[Incident]:
        """Compatibility alias for the complete normalized incident collection."""
        return self.incidents_all

    @property
    def cfs_incidents(self) -> list[Incident]:
        """Return normalized CFS incidents."""
        return [
            incident for incident in self.incidents_all if incident.agency == AGENCY_CFS
        ]

    @property
    def mfs_incidents(self) -> list[Incident]:
        """Return normalized MFS incidents."""
        return [
            incident for incident in self.incidents_all if incident.agency == AGENCY_MFS
        ]

    @property
    def cfs_relevant_incidents(self) -> list[Incident]:
        """Return relevant CFS incidents only."""
        return [
            incident
            for incident in self.incidents_relevant
            if incident.agency == AGENCY_CFS
        ]

    @property
    def mfs_relevant_incidents(self) -> list[Incident]:
        """Return relevant MFS incidents only."""
        return [
            incident
            for incident in self.incidents_relevant
            if incident.agency == AGENCY_MFS
        ]

    @property
    def non_relevant_incident_count(self) -> int:
        """Return incidents outside the regional radius or without coordinates."""
        return len(self.incidents_all) - len(self.incidents_relevant)

    @property
    def non_spatial_incident_count(self) -> int:
        """Return incidents without usable coordinates."""
        return sum(
            1
            for incident in self.incidents_all
            if incident.latitude is None or incident.longitude is None
        )
