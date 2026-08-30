"""Diagnostics support for the SA Emergency integration."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.redact import async_redact_data
from homeassistant.loader import async_get_integration

from .const import (
    CFS_INCIDENTS_URL,
    CONF_INCLUDE_CFS,
    CONF_INCLUDE_MFS,
    CONF_LOCAL_RADIUS_KM,
    CONF_REGIONAL_RADIUS_KM,
    DOMAIN,
    MFS_INCIDENTS_URL,
    SOURCE_CFS_CURRENT_INCIDENTS,
    SOURCE_MFS_CURRENT_INCIDENTS,
)
from .coordinator import SaEmergencyDataUpdateCoordinator
from .presentation import format_last_successful_update, source_status_to_public_dict

TO_REDACT = {
    "latitude",
    "longitude",
    "lat",
    "long",
    "location",
    "home_latitude",
    "home_longitude",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator: SaEmergencyDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    integration = await async_get_integration(hass, DOMAIN)
    return async_redact_data(
        _build_diagnostics_payload(
            integration_version=integration.version,
            coordinator=coordinator,
        ),
        TO_REDACT,
    )


def _build_diagnostics_payload(
    *,
    integration_version: str,
    coordinator: SaEmergencyDataUpdateCoordinator,
) -> dict[str, Any]:
    """Build support-oriented diagnostics without private home coordinates."""
    options = coordinator.options
    data = coordinator.data

    cfs_status = data.source_status.get(SOURCE_CFS_CURRENT_INCIDENTS)
    mfs_status = data.source_status.get(SOURCE_MFS_CURRENT_INCIDENTS)

    payload: dict[str, Any] = {
        "integration": {
            "version": integration_version,
            "domain": DOMAIN,
        },
        "options": {
            CONF_LOCAL_RADIUS_KM: options.local_radius_km,
            CONF_REGIONAL_RADIUS_KM: options.regional_radius_km,
            "scan_interval_seconds": int(options.scan_interval.total_seconds()),
            CONF_INCLUDE_CFS: options.include_cfs,
            CONF_INCLUDE_MFS: options.include_mfs,
        },
        "sources": {
            "cfs": {
                **source_status_to_public_dict(cfs_status),
                "url": CFS_INCIDENTS_URL,
            },
            "mfs": {
                **source_status_to_public_dict(mfs_status),
                "url": MFS_INCIDENTS_URL,
            },
        },
        "incidents": {
            "total_source": len(data.incidents_all),
            "relevant": len(data.incidents_relevant),
            "local": len(data.incidents_local),
            "regional": len(data.incidents_regional),
            "non_relevant": data.non_relevant_incident_count,
            "non_spatial": data.non_spatial_incident_count,
            "highest_relevance": data.highest_relevance,
            "nearest_incident_id": (
                data.nearest_incident.incident_id
                if data.nearest_incident is not None
                else None
            ),
        },
    }

    last_update = format_last_successful_update(data.last_successful_update)
    if last_update is not None:
        payload["last_successful_update"] = last_update

    return payload


def assert_no_home_coordinates(payload: dict[str, Any]) -> None:
    """Raise if serialized diagnostics appear to contain home coordinates."""
    serialized = str(payload).lower()
    for marker in (
        "home_latitude",
        "home_longitude",
        "hass.config.latitude",
        "hass.config.longitude",
    ):
        if marker in serialized:
            msg = f"Diagnostics must not expose home coordinates ({marker})"
            raise AssertionError(msg)
