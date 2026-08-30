"""Data update coordinator for the SA Emergency integration."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import SaEmergencyApi, SaEmergencyApiError
from .const import (
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    SOURCE_CFS_CURRENT_INCIDENTS,
    SOURCE_MFS_CURRENT_INCIDENTS,
    SOURCE_STATUS_ERROR,
    SOURCE_STATUS_OK,
)
from .models import Incident, SaEmergencyData, SourceStatus
from .normalizer import normalize_cfs_incident, normalize_mfs_incident

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
        """Fetch and normalize CFS and MFS incidents."""
        cfs_incidents, cfs_status = await self._async_fetch_source(
            SOURCE_CFS_CURRENT_INCIDENTS,
            self.api.async_get_cfs_incidents,
            normalize_cfs_incident,
        )
        mfs_incidents, mfs_status = await self._async_fetch_source(
            SOURCE_MFS_CURRENT_INCIDENTS,
            self.api.async_get_mfs_incidents,
            normalize_mfs_incident,
        )

        if (
            cfs_status.status == SOURCE_STATUS_ERROR
            and mfs_status.status == SOURCE_STATUS_ERROR
        ):
            raise UpdateFailed(
                "No current incident data available from CFS or MFS sources"
            )

        incidents = cfs_incidents + mfs_incidents
        last_successful_update = None
        if (
            cfs_status.status == SOURCE_STATUS_OK
            or mfs_status.status == SOURCE_STATUS_OK
        ):
            last_successful_update = dt_util.utcnow()

        return SaEmergencyData(
            incidents=incidents,
            source_status={
                SOURCE_CFS_CURRENT_INCIDENTS: cfs_status,
                SOURCE_MFS_CURRENT_INCIDENTS: mfs_status,
            },
            last_successful_update=last_successful_update,
        )

    async def _async_fetch_source(
        self,
        source_key: str,
        fetch_method: Callable[[], Any],
        normalize_method: Callable[[dict[str, Any]], Incident | None],
    ) -> tuple[list[Incident], SourceStatus]:
        """Fetch and normalize one incident source."""
        try:
            raw_records = await fetch_method()
        except SaEmergencyApiError as err:
            _LOGGER.warning("%s unavailable: %s", source_key, err)
            return [], SourceStatus(
                status=SOURCE_STATUS_ERROR,
                error=str(err),
            )

        incidents: list[Incident] = []
        skipped_count = 0
        for record in raw_records:
            incident = normalize_method(record)
            if incident is None:
                skipped_count += 1
                continue
            incidents.append(incident)

        _LOGGER.debug(
            "%s records fetched: %s, incidents normalized: %s, records skipped: %s",
            source_key,
            len(raw_records),
            len(incidents),
            skipped_count,
        )

        return incidents, SourceStatus(
            status=SOURCE_STATUS_OK,
            raw_count=len(raw_records),
            normalized_count=len(incidents),
            skipped_count=skipped_count,
        )
