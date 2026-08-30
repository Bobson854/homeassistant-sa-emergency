"""Normalization of source incident records."""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from .const import AGENCY_CFS, CFS_TIMEZONE, SOURCE_CFS_CURRENT_INCIDENTS
from .models import Incident

_LOGGER = logging.getLogger(__name__)

_CFS_DATETIME_FORMATS = (
    "%d/%m/%Y %H:%M",
    "%d/%m/%Y %H:%M:%S",
)


def normalize_cfs_incident(record: dict[str, Any]) -> Incident | None:
    """Normalize one CFS current incident record.

    Returns None only when the record cannot produce a stable incident identity.
    Incidents with missing or invalid coordinates are retained with latitude and
    longitude set to None so later geography processing can treat them as non-spatial.
    """
    incident_no = _optional_str(record.get("IncidentNo"))
    if not incident_no:
        _LOGGER.debug("Skipping CFS record without IncidentNo: %r", record)
        return None

    latitude, longitude = parse_cfs_location(record.get("Location"))
    first_reported = parse_cfs_datetime(record.get("Date"), record.get("Time"))

    return Incident(
        incident_id=f"{AGENCY_CFS}:{incident_no}",
        agency=AGENCY_CFS,
        incident_type=_optional_str(record.get("Type")),
        status=_optional_str(record.get("Status")),
        level=_optional_str(record.get("Level")),
        first_reported=first_reported,
        location_name=_optional_str(record.get("Location_name")),
        latitude=latitude,
        longitude=longitude,
        region=_optional_str(record.get("Region")),
        fire_ban_district=_optional_str(record.get("FBD")),
        resources=parse_optional_count(record.get("Resources")),
        aircraft_count=parse_optional_count(record.get("Aircraft")),
        message=_optional_str(record.get("Message")),
        message_url=_optional_str(record.get("Message_link")),
        source=SOURCE_CFS_CURRENT_INCIDENTS,
    )


def parse_optional_count(value: Any) -> int | None:
    """Parse Resources/Aircraft-style count fields defensively."""
    if value is None:
        return None

    if isinstance(value, bool):
        return None

    if isinstance(value, int):
        return value

    if isinstance(value, float):
        if value.is_integer():
            return int(value)
        return None

    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        if re.fullmatch(r"-?\d+", stripped):
            return int(stripped)
        return None

    return None


def parse_cfs_location(value: Any) -> tuple[float | None, float | None]:
    """Parse CFS Location strings such as '-34.02,137.81'."""
    if value is None:
        return None, None

    if not isinstance(value, str):
        return None, None

    stripped = value.strip()
    if not stripped:
        return None, None

    parts = [part.strip() for part in stripped.split(",")]
    if len(parts) != 2:
        return None, None

    try:
        latitude = float(parts[0])
        longitude = float(parts[1])
    except ValueError:
        return None, None

    if not _valid_latitude(latitude) or not _valid_longitude(longitude):
        return None, None

    return latitude, longitude


def parse_cfs_datetime(date_value: Any, time_value: Any) -> datetime | None:
    """Combine CFS Date and Time into a timezone-aware datetime."""
    date_str = _optional_str(date_value)
    time_str = _optional_str(time_value)
    if not date_str or not time_str:
        return None

    combined = f"{date_str} {time_str}"
    tzinfo = ZoneInfo(CFS_TIMEZONE)

    for fmt in _CFS_DATETIME_FORMATS:
        try:
            parsed = datetime.strptime(combined, fmt)
        except ValueError:
            continue
        return parsed.replace(tzinfo=tzinfo)

    _LOGGER.debug("Unable to parse CFS Date/Time: %r %r", date_value, time_value)
    return None


def _optional_str(value: Any) -> str | None:
    """Return a stripped string or None."""
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return str(value).strip() or None


def _valid_latitude(value: float) -> bool:
    return -90.0 <= value <= 90.0


def _valid_longitude(value: float) -> bool:
    return -180.0 <= value <= 180.0
