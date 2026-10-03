"""Data update coordinator for the SA Emergency integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import SaEmergencyApi, SaEmergencyApiError
from .const import (
    AGENCY_CFS,
    DOMAIN,
    SOURCE_CFS_CURRENT_INCIDENTS,
    SOURCE_IMS_CURRENT_INCIDENTS,
    SOURCE_MFS_CURRENT_INCIDENTS,
    SOURCE_STATUS_DISABLED,
    SOURCE_STATUS_OK,
)
from .geography import build_geographic_data, get_home_coordinates
from .models import Incident, SaEmergencyData, SourceStatus
from .normalizer import classify_ims_agency, normalize_ims_incident
from .options import get_integration_options

_LOGGER = logging.getLogger(__name__)

type SaEmergencyConfigEntry = ConfigEntry[None]


@dataclass(slots=True)
class _ImsProcessingResult:
    """Normalized IMS incidents split by agency with accounting."""

    cfs_incidents: list[Incident]
    mfs_incidents: list[Incident]
    raw_count: int
    cfs_raw_count: int
    mfs_raw_count: int
    unknown_authority_skipped: int
    cfs_skipped: int
    mfs_skipped: int

    @property
    def normalized_count(self) -> int:
        return len(self.cfs_incidents) + len(self.mfs_incidents)

    @property
    def skipped_count(self) -> int:
        return self.unknown_authority_skipped + self.cfs_skipped + self.mfs_skipped


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
        """Fetch, normalize, and enrich current IMS incidents."""
        if not self.options.include_cfs and not self.options.include_mfs:
            raise UpdateFailed("No incident agencies are enabled")

        try:
            raw_records = await self.api.async_get_ims_incidents()
        except SaEmergencyApiError as err:
            raise UpdateFailed(f"IMS incident feed unavailable: {err}") from err

        processed = _process_ims_records(raw_records)

        cfs_incidents = processed.cfs_incidents if self.options.include_cfs else []
        mfs_incidents = processed.mfs_incidents if self.options.include_mfs else []

        home_lat, home_lon = get_home_coordinates(self.hass)
        data = build_geographic_data(
            cfs_incidents + mfs_incidents,
            home_lat,
            home_lon,
            local_radius_km=self.options.local_radius_km,
            regional_radius_km=self.options.regional_radius_km,
        )

        ims_status = SourceStatus(
            status=SOURCE_STATUS_OK,
            raw_count=processed.raw_count,
            normalized_count=processed.normalized_count,
            skipped_count=processed.skipped_count,
        )

        if self.options.include_cfs:
            cfs_status = SourceStatus(
                status=SOURCE_STATUS_OK,
                raw_count=processed.cfs_raw_count,
                normalized_count=len(processed.cfs_incidents),
                skipped_count=processed.cfs_skipped,
            )
        else:
            cfs_status = SourceStatus(status=SOURCE_STATUS_DISABLED, enabled=False)

        if self.options.include_mfs:
            mfs_status = SourceStatus(
                status=SOURCE_STATUS_OK,
                raw_count=processed.mfs_raw_count,
                normalized_count=len(processed.mfs_incidents),
                skipped_count=processed.mfs_skipped,
            )
        else:
            mfs_status = SourceStatus(status=SOURCE_STATUS_DISABLED, enabled=False)

        data.source_status = {
            SOURCE_IMS_CURRENT_INCIDENTS: ims_status,
            SOURCE_CFS_CURRENT_INCIDENTS: cfs_status,
            SOURCE_MFS_CURRENT_INCIDENTS: mfs_status,
        }
        data.last_successful_update = dt_util.utcnow()
        return data


def _process_ims_records(raw_records: list[dict[str, Any]]) -> _ImsProcessingResult:
    """Normalize IMS records and split them by agency."""
    cfs_incidents: list[Incident] = []
    mfs_incidents: list[Incident] = []
    cfs_raw_count = 0
    mfs_raw_count = 0
    unknown_authority_skipped = 0
    cfs_skipped = 0
    mfs_skipped = 0

    for record in raw_records:
        agency = classify_ims_agency(record.get("authority"))
        if agency is None:
            unknown_authority_skipped += 1
            continue

        if agency == AGENCY_CFS:
            cfs_raw_count += 1
        else:
            mfs_raw_count += 1

        incident = normalize_ims_incident(record)
        if incident is None:
            if agency == AGENCY_CFS:
                cfs_skipped += 1
            else:
                mfs_skipped += 1
            continue

        if agency == AGENCY_CFS:
            cfs_incidents.append(incident)
        else:
            mfs_incidents.append(incident)

    return _ImsProcessingResult(
        cfs_incidents=cfs_incidents,
        mfs_incidents=mfs_incidents,
        raw_count=len(raw_records),
        cfs_raw_count=cfs_raw_count,
        mfs_raw_count=mfs_raw_count,
        unknown_authority_skipped=unknown_authority_skipped,
        cfs_skipped=cfs_skipped,
        mfs_skipped=mfs_skipped,
    )
