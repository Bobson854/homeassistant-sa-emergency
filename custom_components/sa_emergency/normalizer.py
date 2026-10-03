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
    IMS_AUTHORITY_CFS,
    IMS_AUTHORITY_MFS,
    SA_TIMEZONE,
    SOURCE_CFS_CURRENT_INCIDENTS,
    SOURCE_IMS_CURRENT_INCIDENTS,
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


def classify_ims_agency(authority: Any) -> str | None:
    """Map an IMS authority string to a normalized agency code."""
    authority_str = _optional_str(authority)
    if authority_str is None:
        return None

    normalized = authority_str.casefold()
    if normalized == IMS_AUTHORITY_CFS.casefold():
        return AGENCY_CFS
    if normalized == IMS_AUTHORITY_MFS.casefold():
        return AGENCY_MFS

    _LOGGER.debug("Skipping IMS record with unsupported authority: %r", authority)
    return None


def normalize_ims_incident(record: dict[str, Any]) -> Incident | None:
    """Normalize one IMS current incident attributes record."""
    agency = classify_ims_agency(record.get("authority"))
    if agency is None:
        return None

    ident = _optional_str(record.get("ident"))
    if not ident:
        _LOGGER.debug("Skipping IMS record without ident: %r", record)
        return None

    latitude, longitude = parse_mfs_coordinates(record)
    first_reported = parse_ims_first_reported(record)

    return Incident(
        incident_id=f"{agency}:{ident}",
        agency=agency,
        source=SOURCE_IMS_CURRENT_INCIDENTS,
        incident_type=_optional_str(record.get("event")),
        status=_optional_str(record.get("inc_status")),
        level=parse_ims_level(record.get("inc_level")),
        first_reported=first_reported,
        location_name=parse_ims_location_name(record),
        latitude=latitude,
        longitude=longitude,
        region=None,
        fire_ban_district=_optional_str(record.get("fbd")),
        resources=None,
        aircraft_count=None,
        message=parse_ims_message(record),
        message_url=_optional_str(record.get("web")),
    )


def parse_ims_location_name(record: dict[str, Any]) -> str | None:
    """Return the best available IMS location label."""
    return _optional_str(record.get("location")) or _optional_str(
        record.get("inc_name")
    )


def parse_ims_message(record: dict[str, Any]) -> str | None:
    """Return concise operational text from IMS fields."""
    for key in ("incs", "headline", "title", "instruct"):
        value = _optional_str(record.get(key))
        if value is not None:
            return value
    return None


def parse_ims_level(value: Any) -> str | None:
    """Convert IMS inc_level values to a normalized string."""
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return str(value).strip() or None


def parse_ims_first_reported(record: dict[str, Any]) -> datetime | None:
    """Parse IMS effective/sent/updated epoch millisecond timestamps."""
    for key in ("effective", "sent", "updated"):
        parsed = parse_ims_epoch_milliseconds(record.get(key))
        if parsed is not None:
            return parsed
    return None


def parse_ims_epoch_milliseconds(value: Any) -> datetime | None:
    """Parse IMS epoch millisecond values into a timezone-aware datetime."""
    if value is None or isinstance(value, bool):
        return None

    try:
        milliseconds = int(value)
    except (TypeError, ValueError):
        return None

    if milliseconds <= 0:
        return None

    from datetime import UTC

    return datetime.fromtimestamp(milliseconds / 1000, tz=UTC)


def normalize_cfs_incident(record: dict[str, Any]) -> Incident | None:
    """Normalize one legacy CFS JSON incident record.

    Retained for regression tests only; production uses the IMS feed.
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
    """Normalize one legacy MFS ArcGIS incident record.

    Retained for regression tests only; production uses the IMS feed.
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
