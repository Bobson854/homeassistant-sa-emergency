"""Normalization of source incident records."""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from .const import (
    AGENCY_CFS,
    AGENCY_MFS,
    SA_TIMEZONE,
    SOURCE_CFS_CURRENT_INCIDENTS,
    SOURCE_MFS_CURRENT_INCIDENTS,
)
from .models import Incident

_LOGGER = logging.getLogger(__name__)

_CFS_DATETIME_FORMATS = (
    "%d/%m/%Y %H:%M",
    "%d/%m/%Y %H:%M:%S",
)

_MFS_DATETIME_FORMATS = (
    "%A, %d %b %Y %H:%M:%S",
    "%A, %d %b %Y %H:%M",
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
        source=SOURCE_CFS_CURRENT_INCIDENTS,
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
    )


def normalize_mfs_incident(record: dict[str, Any]) -> Incident | None:
    """Normalize one MFS ArcGIS incident attributes record.

    Returns None only when the record cannot produce a stable incident identity.
    """
    incident_id_value = record.get("id")
    if incident_id_value is None or incident_id_value == "":
        _LOGGER.debug("Skipping MFS record without id: %r", record)
        return None

    incident_no = str(incident_id_value).strip()
    if not incident_no:
        _LOGGER.debug("Skipping MFS record with blank id: %r", record)
        return None

    latitude, longitude = parse_mfs_coordinates(record)
    location_name, message = _mfs_location_fields(record)

    return Incident(
        incident_id=f"{AGENCY_MFS}:{incident_no}",
        agency=AGENCY_MFS,
        source=SOURCE_MFS_CURRENT_INCIDENTS,
        incident_type=_optional_str(record.get("event")),
        status=_optional_str(record.get("status")),
        level=None,
        first_reported=parse_mfs_first_report(record.get("first_report")),
        location_name=location_name,
        latitude=latitude,
        longitude=longitude,
        region=_optional_str(record.get("region")),
        fire_ban_district=None,
        resources=None,
        aircraft_count=parse_optional_count(record.get("aircraft")),
        message=message,
        message_url=None,
    )


def _mfs_location_fields(record: dict[str, Any]) -> tuple[str | None, str | None]:
    """Map MFS name/incident_name fields to location and descriptive text.

    Live MFS records use `name` for the street address and `incident_name` for a
    shorter area label. Prefer the street address as location_name.
    """
    street_name = _optional_str(record.get("name"))
    incident_name = _optional_str(record.get("incident_name"))
    location_name = street_name or incident_name
    message = None
    if street_name and incident_name and street_name != incident_name:
        message = incident_name
    return location_name, message


def parse_mfs_coordinates(record: dict[str, Any]) -> tuple[float | None, float | None]:
    """Parse separate MFS lat/long attribute fields."""
    latitude = parse_coordinate(record.get("lat"))
    longitude = parse_coordinate(record.get("long"))

    if latitude is not None and not _valid_latitude(latitude):
        latitude = None
    if longitude is not None and not _valid_longitude(longitude):
        longitude = None

    return latitude, longitude


def parse_coordinate(value: Any) -> float | None:
    """Parse a single latitude or longitude value."""
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return float(value)
    if isinstance(value, float):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        try:
            return float(stripped)
        except ValueError:
            return None
    return None


def parse_mfs_first_report(value: Any) -> datetime | None:
    """Parse MFS first_report values into a timezone-aware datetime."""
    if value is None:
        return None

    if isinstance(value, (int, float)):
        from datetime import UTC

        return datetime.fromtimestamp(value / 1000, tz=UTC)

    if not isinstance(value, str):
        return None

    stripped = value.strip()
    if not stripped:
        return None

    tzinfo = ZoneInfo(SA_TIMEZONE)
    for fmt in _MFS_DATETIME_FORMATS:
        try:
            parsed = datetime.strptime(stripped, fmt)
        except ValueError:
            continue
        return parsed.replace(tzinfo=tzinfo)

    _LOGGER.debug("Unable to parse MFS first_report: %r", value)
    return None


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
    tzinfo = ZoneInfo(SA_TIMEZONE)

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
