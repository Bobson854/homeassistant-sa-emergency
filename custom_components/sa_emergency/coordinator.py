"""Data update coordinator for the SA Emergency integration."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)

type SaEmergencyConfigEntry = ConfigEntry[None]


class SaEmergencyDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinate SA Emergency data updates.

    Milestone 1 scaffold only — no external API calls or incident records yet.
    Later milestones will fetch CFS/MFS feeds, normalize incidents, and compute
    geographic relevance before exposing stable Home Assistant entities.
    """

    config_entry: SaEmergencyConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: SaEmergencyConfigEntry,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            logger=_LOGGER,
            name=DOMAIN,
            config_entry=config_entry,
            update_interval=DEFAULT_SCAN_INTERVAL,
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Return scaffold coordinator state.

        Does not perform HTTP requests or fabricate incident data.
        """
        if self.hass.config.latitude is None or self.hass.config.longitude is None:
            raise UpdateFailed(
                "Home Assistant location is not configured; set latitude and "
                "longitude in Settings → System → General."
            )

        return {
            "scaffold": True,
            "status": "scaffold",
            "message": (
                "SA Emergency scaffold is active. Incident polling is not "
                "implemented yet."
            ),
            "reference_latitude": self.hass.config.latitude,
            "reference_longitude": self.hass.config.longitude,
            "last_checked": dt_util.utcnow().isoformat(),
            "incidents": [],
        }
