"""Pure geographic calculations for the SA Emergency integration."""

from __future__ import annotations

import math

from .const import EARTH_RADIUS_KM, SAME_LOCATION_TOLERANCE_KM

_CARDINAL_SECTORS: tuple[tuple[float, float, str], ...] = (
    (337.5, 360.0, "N"),
    (0.0, 22.5, "N"),
    (22.5, 67.5, "NE"),
    (67.5, 112.5, "E"),
    (112.5, 157.5, "SE"),
    (157.5, 202.5, "S"),
    (202.5, 247.5, "SW"),
    (247.5, 292.5, "W"),
    (292.5, 337.5, "NW"),
)


def calculate_distance_km(
    origin_lat: float,
    origin_lon: float,
    target_lat: float,
    target_lon: float,
) -> float:
    """Return great-circle distance in kilometres using the Haversine formula."""
    origin_lat_rad = math.radians(origin_lat)
    origin_lon_rad = math.radians(origin_lon)
    target_lat_rad = math.radians(target_lat)
    target_lon_rad = math.radians(target_lon)

    delta_lat = target_lat_rad - origin_lat_rad
    delta_lon = target_lon_rad - origin_lon_rad

    haversine = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(origin_lat_rad)
        * math.cos(target_lat_rad)
        * math.sin(delta_lon / 2) ** 2
    )
    central_angle = 2 * math.atan2(math.sqrt(haversine), math.sqrt(1 - haversine))
    return EARTH_RADIUS_KM * central_angle


def calculate_initial_bearing(
    origin_lat: float,
    origin_lon: float,
    target_lat: float,
    target_lon: float,
) -> float:
    """Return the initial great-circle bearing in degrees normalized to [0, 360)."""
    origin_lat_rad = math.radians(origin_lat)
    origin_lon_rad = math.radians(origin_lon)
    target_lat_rad = math.radians(target_lat)
    target_lon_rad = math.radians(target_lon)

    delta_lon = target_lon_rad - origin_lon_rad
    y = math.sin(delta_lon) * math.cos(target_lat_rad)
    x = math.cos(origin_lat_rad) * math.sin(target_lat_rad) - math.sin(
        origin_lat_rad
    ) * math.cos(target_lat_rad) * math.cos(delta_lon)
    bearing = math.degrees(math.atan2(y, x))
    return bearing % 360


def bearing_to_cardinal(bearing: float) -> str:
    """Map a bearing in degrees to an eight-point compass direction."""
    normalized = bearing % 360
    for lower, upper, cardinal in _CARDINAL_SECTORS:
        if lower <= normalized < upper:
            return cardinal
    return "N"


def is_same_location(
    origin_lat: float,
    origin_lon: float,
    target_lat: float,
    target_lon: float,
) -> bool:
    """Return True when two coordinates are effectively identical."""
    return (
        calculate_distance_km(origin_lat, origin_lon, target_lat, target_lon)
        < SAME_LOCATION_TOLERANCE_KM
    )


def round_distance_km(distance_km: float) -> float:
    """Round a distance to one decimal place for storage and display."""
    return round(distance_km, 1)
