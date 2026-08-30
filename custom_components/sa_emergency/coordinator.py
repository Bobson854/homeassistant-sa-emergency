"""Data update coordinator for the SA Emergency integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import SaEmergencyApi, SaEmergencyApiError
from .const import (
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    SOURCE_CFS_CURRENT_INCIDENTS,
    SOURCE_STATUS_OK,
)
from .models import Incident, SaEmergencyData, SourceStatus
from .normalizer import normalize_cfs_incident

_LOGGER = logging.getLogger(__name__)

type SaEmergencyConfigEntry = ConfigEntry[None]


class SaEmergencyDataUpdateCoordinator(DataUpdateCoordinator[SaEmergencyData]):
    """Coordinate SA Emergency data updates."""

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
        self.api = SaEmergencyApi(hass)

    async def _async_update_data(self) -> SaEmergencyData:
        """Fetch and normalize CFS incidents."""
        try:
            raw_records = await self.api.async_get_cfs_incidents()
        except SaEmergencyApiError as err:
            raise UpdateFailed(f"CFS feed unavailable: {err}") from err

        incidents: list[Incident] = []
        skipped_count = 0

        for record in raw_records:
            incident = normalize_cfs_incident(record)
            if incident is None:
                skipped_count += 1
                continue
            incidents.append(incident)

        _LOGGER.debug(
            "CFS records fetched: %s, incidents normalized: %s, records skipped: %s",
            len(raw_records),
            len(incidents),
            skipped_count,
        )

        now = dt_util.utcnow()
        source_status = {
            SOURCE_CFS_CURRENT_INCIDENTS: SourceStatus(
                status=SOURCE_STATUS_OK,
                raw_count=len(raw_records),
                normalized_count=len(incidents),
                skipped_count=skipped_count,
            )
        }

        return SaEmergencyData(
            incidents=incidents,
            source_status=source_status,
            last_successful_update=now,
        )
