"""Integration option resolution and validation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_SCAN_INTERVAL

from .const import (
    CONF_INCLUDE_CFS,
    CONF_INCLUDE_MFS,
    CONF_LOCAL_RADIUS_KM,
    CONF_REGIONAL_RADIUS_KM,
    DEFAULT_LOCAL_RADIUS_KM,
    DEFAULT_REGIONAL_RADIUS_KM,
    DEFAULT_UPDATE_INTERVAL_SECONDS,
    MAX_LOCAL_RADIUS_KM,
    MAX_REGIONAL_RADIUS_KM,
    MAX_SCAN_INTERVAL_SECONDS,
    MIN_SCAN_INTERVAL_SECONDS,
)


@dataclass(frozen=True, slots=True)
class SaEmergencyOptions:
    """Resolved integration runtime options."""

    local_radius_km: float
    regional_radius_km: float
    scan_interval: timedelta
    include_cfs: bool
    include_mfs: bool


def get_integration_options(config_entry: ConfigEntry) -> SaEmergencyOptions:
    """Return effective options for a config entry, falling back to defaults."""
    options = config_entry.options
    scan_seconds = int(options.get(CONF_SCAN_INTERVAL, DEFAULT_UPDATE_INTERVAL_SECONDS))
    return SaEmergencyOptions(
        local_radius_km=float(
            options.get(CONF_LOCAL_RADIUS_KM, DEFAULT_LOCAL_RADIUS_KM)
        ),
        regional_radius_km=float(
            options.get(CONF_REGIONAL_RADIUS_KM, DEFAULT_REGIONAL_RADIUS_KM)
        ),
        scan_interval=timedelta(seconds=scan_seconds),
        include_cfs=bool(options.get(CONF_INCLUDE_CFS, True)),
        include_mfs=bool(options.get(CONF_INCLUDE_MFS, True)),
    )


def options_schema_defaults(config_entry: ConfigEntry) -> dict[str, Any]:
    """Return current option values for the Options Flow form."""
    options = get_integration_options(config_entry)
    return {
        CONF_LOCAL_RADIUS_KM: options.local_radius_km,
        CONF_REGIONAL_RADIUS_KM: options.regional_radius_km,
        CONF_SCAN_INTERVAL: int(options.scan_interval.total_seconds()),
        CONF_INCLUDE_CFS: options.include_cfs,
        CONF_INCLUDE_MFS: options.include_mfs,
    }


def validate_options_input(user_input: dict[str, Any]) -> dict[str, str]:
    """Validate Options Flow input and return field error keys."""
    errors: dict[str, str] = {}

    local_radius = user_input[CONF_LOCAL_RADIUS_KM]
    regional_radius = user_input[CONF_REGIONAL_RADIUS_KM]
    scan_interval = user_input[CONF_SCAN_INTERVAL]
    include_cfs = user_input[CONF_INCLUDE_CFS]
    include_mfs = user_input[CONF_INCLUDE_MFS]

    if local_radius <= 0 or local_radius > MAX_LOCAL_RADIUS_KM:
        errors[CONF_LOCAL_RADIUS_KM] = "invalid_local_radius"
    if regional_radius <= 0 or regional_radius > MAX_REGIONAL_RADIUS_KM:
        errors[CONF_REGIONAL_RADIUS_KM] = "invalid_regional_radius"
    elif regional_radius <= local_radius:
        errors[CONF_REGIONAL_RADIUS_KM] = "regional_not_greater_than_local"

    if (
        scan_interval < MIN_SCAN_INTERVAL_SECONDS
        or scan_interval > MAX_SCAN_INTERVAL_SECONDS
    ):
        errors[CONF_SCAN_INTERVAL] = "invalid_poll_interval"

    if not include_cfs and not include_mfs:
        errors["base"] = "no_agencies_enabled"

    return errors
