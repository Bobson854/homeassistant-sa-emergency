"""Tests for CFS normalization."""

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from tests.fixtures import load_json_fixture

from custom_components.sa_emergency.const import (
    AGENCY_CFS,
    CFS_TIMEZONE,
    SOURCE_CFS_CURRENT_INCIDENTS,
)
from custom_components.sa_emergency.normalizer import (
    normalize_cfs_incident,
    parse_cfs_datetime,
    parse_cfs_location,
    parse_optional_count,
)


def test_normalize_valid_cfs_incident() -> None:
    """Test a representative valid CFS record normalizes correctly."""
    record = load_json_fixture("cfs_valid_single.json")[0]
    incident = normalize_cfs_incident(record)

    assert incident is not None
    assert incident.incident_id == "CFS:123456"
    assert incident.agency == AGENCY_CFS
    assert incident.source == SOURCE_CFS_CURRENT_INCIDENTS
    assert incident.incident_type == "Grass Fire"
    assert incident.status == "GOING"
    assert incident.level == "2"
    assert incident.location_name == "MONARTO, OLD PRINCES HIGHWAY"
    assert incident.region == "2"
    assert incident.fire_ban_district == "MURRAYlands"
    assert incident.resources == 4
    assert incident.aircraft_count == 1
    assert incident.message == "Smoke visible in area"
    assert incident.message_url == "https://example.test/incident/123456"
    assert incident.latitude == pytest.approx(-35.1234)
    assert incident.longitude == pytest.approx(139.5678)
    assert incident.first_reported == datetime(
        2026, 8, 30, 14, 30, tzinfo=ZoneInfo(CFS_TIMEZONE)
    )
    assert incident.distance_km is None
    assert incident.bearing_degrees is None
    assert incident.bearing_cardinal is None
    assert incident.relevance is None


def test_normalize_multiple_valid_incidents() -> None:
    """Test several valid records normalize independently."""
    records = load_json_fixture("cfs_valid_multiple.json")
    incidents = [normalize_cfs_incident(record) for record in records]

    assert len(incidents) == 2
    assert all(incident is not None for incident in incidents)
    assert {incident.incident_id for incident in incidents if incident} == {
        "CFS:111111",
        "CFS:222222",
    }


def test_normalize_missing_optional_fields() -> None:
    """Test missing optional fields become None without rejecting the incident."""
    record = load_json_fixture("cfs_missing_optional_fields.json")[0]
    incident = normalize_cfs_incident(record)

    assert incident is not None
    assert incident.incident_id == "CFS:333333"
    assert incident.message is None
    assert incident.location_name is None
    assert incident.resources is None


def test_normalize_blank_optional_fields() -> None:
    """Test blank optional fields become None."""
    record = load_json_fixture("cfs_blank_optional_fields.json")[0]
    incident = normalize_cfs_incident(record)

    assert incident is not None
    assert incident.message is None
    assert incident.location_name is None
    assert incident.region is None
    assert incident.level is None
    assert incident.resources is None
    assert incident.aircraft_count is None
    assert incident.latitude is None
    assert incident.longitude is None


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0, 0),
        (4, 4),
        ("4", 4),
        (" 4 ", 4),
        ("", None),
        (None, None),
        ("bad", None),
        (True, None),
    ],
)
def test_parse_optional_count(value: object, expected: int | None) -> None:
    """Test defensive count parsing."""
    assert parse_optional_count(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("-35.1234,139.5678", (-35.1234, 139.5678)),
        (" -34.0 , 138.0 ", (-34.0, 138.0)),
        ("", (None, None)),
        (None, (None, None)),
        ("not-a-coordinate", (None, None)),
        ("95.0,138.0", (None, None)),
        ("-35.0,200.0", (None, None)),
    ],
)
def test_parse_cfs_location(
    value: str | None, expected: tuple[float | None, float | None]
) -> None:
    """Test CFS Location parsing."""
    assert parse_cfs_location(value) == expected


def test_normalize_retains_incidents_without_coordinates() -> None:
    """Test incidents without usable coordinates are retained."""
    records = load_json_fixture("cfs_location_variants.json")
    incidents = [normalize_cfs_incident(record) for record in records]

    assert len(incidents) == 5
    assert all(incident is not None for incident in incidents)
    assert incidents[0].latitude == pytest.approx(-35.5)
    assert incidents[1].latitude is None
    assert incidents[2].latitude is None
    assert incidents[3].latitude is None
    assert incidents[4].latitude is None


def test_parse_cfs_datetime_valid() -> None:
    """Test valid CFS Date/Time parsing is timezone-aware."""
    parsed = parse_cfs_datetime("30/08/2026", "14:30")

    assert parsed == datetime(2026, 8, 30, 14, 30, tzinfo=ZoneInfo(CFS_TIMEZONE))


def test_parse_cfs_datetime_malformed() -> None:
    """Test malformed Date/Time returns None."""
    assert parse_cfs_datetime("not-a-date", "99:99") is None


def test_normalize_mixed_valid_invalid_records() -> None:
    """Test one malformed timestamp does not reject the whole batch."""
    records = load_json_fixture("cfs_mixed_valid_invalid_records.json")
    incidents = [normalize_cfs_incident(record) for record in records]

    assert len(incidents) == 2
    assert all(incident is not None for incident in incidents)
    assert incidents[0].first_reported is not None
    assert incidents[1].first_reported is None


def test_normalize_missing_incident_no_returns_none() -> None:
    """Test records without IncidentNo are skipped."""
    assert normalize_cfs_incident({"Type": "Grass Fire"}) is None
