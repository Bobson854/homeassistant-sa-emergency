"""Geographic enrichment and incident collection building."""

from __future__ import annotations

import logging
from dataclasses import replace
from datetime import UTC, datetime

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed

from .const import (
    DEFAULT_LOCAL_RADIUS_KM,
    DEFAULT_REGIONAL_RADIUS_KM,
    RELEVANCE_LOCAL,
    RELEVANCE_NONE,
    RELEVANCE_REGIONAL,
)
from .geo import (
    bearing_to_cardinal,
    calculate_distance_km,
    calculate_initial_bearing,
    is_same_location,
    round_distance_km,
)
from .models import Incident, SaEmergencyData
from .relevance import classify_relevance

_LOGGER = logging.getLogger(__name__)

_RELEVANCE_SORT_ORDER = {
    RELEVANCE_LOCAL: 0,
    RELEVANCE_REGIONAL: 1,
    RELEVANCE_NONE: 2,
}

_HIGHEST_RELEVANCE_ORDER = (
    RELEVANCE_LOCAL,
    RELEVANCE_REGIONAL,
    RELEVANCE_NONE,
)


def get_home_coordinates(hass: HomeAssistant) -> tuple[float, float]:
    """Return validated Home Assistant reference coordinates."""
    latitude = hass.config.latitude
    longitude = hass.config.longitude

    if latitude is None or longitude is None:
        raise UpdateFailed("Home Assistant location is not configured")

    if not (-90.0 <= latitude <= 90.0 and -180.0 <= longitude <= 180.0):
        raise UpdateFailed("Home Assistant location is not configured")

    return latitude, longitude


def apply_geographic_context(
    incident: Incident,
    home_lat: float,
    home_lon: float,
    local_radius_km: float,
    regional_radius_km: float,
) -> tuple[Incident, float | None]:
    """Populate geographic fields on a normalized incident.

    Returns the enriched incident and the full-precision distance used for
    classification and sorting. Non-spatial incidents retain ``None`` distance
    and are classified as non-relevant.
    """
    latitude = incident.latitude
    longitude = incident.longitude
    if latitude is None or longitude is None:
        return (
            replace(
                incident,
                distance_km=None,
                bearing_degrees=None,
                bearing_cardinal=None,
                relevance=RELEVANCE_NONE,
            ),
            None,
        )

    try:
        precise_distance = calculate_distance_km(
            home_lat, home_lon, latitude, longitude
        )
    except (TypeError, ValueError):
        _LOGGER.debug(
            "Skipping geographic enrichment for invalid coordinates on %s",
            incident.incident_id,
        )
        return (
            replace(
                incident,
                distance_km=None,
                bearing_degrees=None,
                bearing_cardinal=None,
                relevance=RELEVANCE_NONE,
            ),
            None,
        )

    relevance = classify_relevance(
        precise_distance, local_radius_km, regional_radius_km
    )

    if is_same_location(home_lat, home_lon, latitude, longitude):
        return (
            replace(
                incident,
                distance_km=round_distance_km(precise_distance),
                bearing_degrees=None,
                bearing_cardinal=None,
                relevance=relevance,
            ),
            precise_distance,
        )

    bearing_raw = calculate_initial_bearing(home_lat, home_lon, latitude, longitude)
    bearing_degrees = round(bearing_raw) % 360
    return (
        replace(
            incident,
            distance_km=round_distance_km(precise_distance),
            bearing_degrees=float(bearing_degrees),
            bearing_cardinal=bearing_to_cardinal(bearing_raw),
            relevance=relevance,
        ),
        precise_distance,
    )


def build_geographic_data(
    incidents: list[Incident],
    home_lat: float,
    home_lon: float,
    *,
    local_radius_km: float = DEFAULT_LOCAL_RADIUS_KM,
    regional_radius_km: float = DEFAULT_REGIONAL_RADIUS_KM,
) -> SaEmergencyData:
    """Apply geographic context and build coordinator runtime collections."""
    enriched: list[Incident] = []
    precise_distances: dict[str, float] = {}

    for incident in incidents:
        enriched_incident, precise_distance = apply_geographic_context(
            incident,
            home_lat,
            home_lon,
            local_radius_km,
            regional_radius_km,
        )
        enriched.append(enriched_incident)
        if precise_distance is not None:
            precise_distances[enriched_incident.incident_id] = precise_distance

    incidents_local = [
        incident for incident in enriched if incident.relevance == RELEVANCE_LOCAL
    ]
    incidents_regional = [
        incident for incident in enriched if incident.relevance == RELEVANCE_REGIONAL
    ]
    incidents_relevant = [
        incident
        for incident in enriched
        if incident.relevance in (RELEVANCE_LOCAL, RELEVANCE_REGIONAL)
    ]

    incidents_local.sort(
        key=lambda incident: _spatial_sort_key(incident, precise_distances)
    )
    incidents_regional.sort(
        key=lambda incident: _spatial_sort_key(incident, precise_distances)
    )
    incidents_relevant.sort(
        key=lambda incident: _relevant_sort_key(incident, precise_distances)
    )

    nearest_incident = _select_nearest_incident(incidents_relevant, precise_distances)
    highest_relevance = _determine_highest_relevance(enriched)

    return SaEmergencyData(
        incidents_all=enriched,
        incidents_relevant=incidents_relevant,
        incidents_local=incidents_local,
        incidents_regional=incidents_regional,
        nearest_incident=nearest_incident,
        highest_relevance=highest_relevance,
    )


def _spatial_sort_key(
    incident: Incident,
    precise_distances: dict[str, float],
) -> tuple[float, datetime, str]:
    distance = precise_distances.get(incident.incident_id, float("inf"))
    reported = incident.first_reported or datetime.min.replace(tzinfo=UTC)
    return (distance, reported, incident.incident_id)


def _relevant_sort_key(
    incident: Incident,
    precise_distances: dict[str, float],
) -> tuple[int, float, datetime, str]:
    relevance = incident.relevance or RELEVANCE_NONE
    distance = precise_distances.get(incident.incident_id, float("inf"))
    reported = incident.first_reported or datetime.min.replace(tzinfo=UTC)
    return (
        _RELEVANCE_SORT_ORDER[relevance],
        distance,
        reported,
        incident.incident_id,
    )


def _select_nearest_incident(
    incidents_relevant: list[Incident],
    precise_distances: dict[str, float],
) -> Incident | None:
    if not incidents_relevant:
        return None

    return min(
        incidents_relevant,
        key=lambda incident: _spatial_sort_key(incident, precise_distances),
    )


def _determine_highest_relevance(incidents: list[Incident]) -> str:
    present = {incident.relevance for incident in incidents}
    for relevance in _HIGHEST_RELEVANCE_ORDER:
        if relevance in present:
            return relevance
    return RELEVANCE_NONE
