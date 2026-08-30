"""Relevance classification for normalized incidents."""

from __future__ import annotations

from .const import RELEVANCE_LOCAL, RELEVANCE_NONE, RELEVANCE_REGIONAL


def classify_relevance(
    distance_km: float,
    local_radius_km: float,
    regional_radius_km: float,
) -> str:
    """Classify incident relevance from full-precision distance in kilometres."""
    _validate_radius_configuration(local_radius_km, regional_radius_km)

    if distance_km <= local_radius_km:
        return RELEVANCE_LOCAL
    if distance_km <= regional_radius_km:
        return RELEVANCE_REGIONAL
    return RELEVANCE_NONE


def _validate_radius_configuration(
    local_radius_km: float,
    regional_radius_km: float,
) -> None:
    """Reject nonsensical radius configuration."""
    if local_radius_km <= 0:
        msg = "Local radius must be greater than zero"
        raise ValueError(msg)
    if regional_radius_km <= local_radius_km:
        msg = "Regional radius must be greater than the local radius"
        raise ValueError(msg)
