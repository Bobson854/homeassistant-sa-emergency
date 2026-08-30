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
    DOMAIN,
    SOURCE_CFS_CURRENT_INCIDENTS,
    SOURCE_MFS_CURRENT_INCIDENTS,
    SOURCE_STATUS_DISABLED,
    SOURCE_STATUS_ERROR,
    SOURCE_STATUS_OK,
)
from .geography import build_geographic_data, get_home_coordinates
from .models import Incident, SaEmergencyData, SourceStatus
from .normalizer import normalize_cfs_incident, normalize_mfs_incident
from .options import get_integration_options

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
        self.options = get_integration_options(config_entry)
        super().__init__(
            hass,
            logger=_LOGGER,
            name=DOMAIN,
            config_entry=config_entry,
            update_interval=self.options.scan_interval,
        )
        self.api = SaEmergencyApi(hass)

    async def _async_update_data(self) -> SaEmergencyData:
        """Fetch, normalize, and enrich enabled incident sources."""
        cfs_incidents: list[Incident] = []
        mfs_incidents: list[Incident] = []

        if self.options.include_cfs:
            cfs_incidents, cfs_status = await self._async_fetch_source(
                SOURCE_CFS_CURRENT_INCIDENTS,
                self.api.async_get_cfs_incidents,
                normalize_cfs_incident,
            )
        else:
            cfs_status = SourceStatus(
                status=SOURCE_STATUS_DISABLED,
                enabled=False,
            )

        if self.options.include_mfs:
            mfs_incidents, mfs_status = await self._async_fetch_source(
                SOURCE_MFS_CURRENT_INCIDENTS,
                self.api.async_get_mfs_incidents,
                normalize_mfs_incident,
            )
        else:
            mfs_status = SourceStatus(
                status=SOURCE_STATUS_DISABLED,
                enabled=False,
            )

        enabled_statuses = [
            status
            for status in (cfs_status, mfs_status)
            if status.enabled and status.status != SOURCE_STATUS_DISABLED
        ]
        if enabled_statuses and all(
            status.status == SOURCE_STATUS_ERROR for status in enabled_statuses
        ):
            raise UpdateFailed(
                "No current incident data available from enabled incident sources"
            )

        home_lat, home_lon = get_home_coordinates(self.hass)
        merged_incidents = cfs_incidents + mfs_incidents
        data = build_geographic_data(
            merged_incidents,
            home_lat,
            home_lon,
            local_radius_km=self.options.local_radius_km,
            regional_radius_km=self.options.regional_radius_km,
        )

        successful_enabled_sources = [
            status for status in enabled_statuses if status.status == SOURCE_STATUS_OK
        ]
        last_successful_update = (
            dt_util.utcnow() if successful_enabled_sources else None
        )

        data.source_status = {
            SOURCE_CFS_CURRENT_INCIDENTS: cfs_status,
            SOURCE_MFS_CURRENT_INCIDENTS: mfs_status,
        }
        data.last_successful_update = last_successful_update
        return data

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
