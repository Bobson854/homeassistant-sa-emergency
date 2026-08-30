"""Tests for MFS normalization."""

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from tests.fixtures import load_json_fixture

from custom_components.sa_emergency.const import (
    AGENCY_MFS,
    SA_TIMEZONE,
    SOURCE_MFS_CURRENT_INCIDENTS,
)
from custom_components.sa_emergency.normalizer import (
    normalize_mfs_incident,
    parse_coordinate,
    parse_mfs_coordinates,
    parse_mfs_first_report,
)


def _mfs_attributes(fixture_name: str, index: int = 0) -> dict:
    return load_json_fixture(fixture_name)["features"][index]["attributes"]


def test_normalize_valid_mfs_incident() -> None:
    """Test a representative valid MFS record normalizes correctly."""
    record = _mfs_attributes("mfs_valid_single.json")
    incident = normalize_mfs_incident(record)

    assert incident is not None
    assert incident.incident_id == "MFS:1722254"
    assert incident.agency == AGENCY_MFS
    assert incident.source == SOURCE_MFS_CURRENT_INCIDENTS
    assert incident.incident_type == "Private Alarm"
    assert incident.status == "GOING"
    assert incident.level is None
    assert incident.location_name == "ANGLE VALE ROAD, EVANSTON GARDENS"
    assert incident.message == "EVANSTON GARDENS"
    assert incident.region == "MFS"
    assert incident.fire_ban_district is None
    assert incident.resources is None
    assert incident.aircraft_count == 1
    assert incident.message_url is None
    assert incident.latitude == pytest.approx(-34.62377948)
    assert incident.longitude == pytest.approx(138.7185731)
    assert incident.first_reported == datetime(
        2026, 8, 30, 18, 19, tzinfo=ZoneInfo(SA_TIMEZONE)
    )
    assert incident.distance_km is None
    assert incident.bearing_degrees is None
    assert incident.bearing_cardinal is None
    assert incident.relevance is None


def test_normalize_mfs_uses_incident_name_when_name_missing() -> None:
    """Test incident_name is used as location when street name is absent."""
    record = {
        "id": 999,
        "incident_name": "NORTH HAVEN",
        "status": "GOING",
        "event": "Other",
    }
    incident = normalize_mfs_incident(record)

    assert incident is not None
    assert incident.location_name == "NORTH HAVEN"
    assert incident.message is None


def test_normalize_mfs_variants_fixture() -> None:
    """Test mixed coordinate and count variants normalize without crashing."""
    fixture = load_json_fixture("mfs_normalization_variants.json")
    incidents = [
        normalize_mfs_incident(feature["attributes"]) for feature in fixture["features"]
    ]

    assert len(incidents) == 3
    assert all(incident is not None for incident in incidents)
    assert incidents[0].latitude == pytest.approx(-34.9)
    assert incidents[0].aircraft_count == 2
    assert incidents[1].latitude is None
    assert incidents[1].first_reported is None
    assert incidents[1].aircraft_count is None
    assert incidents[2].latitude is None
    assert incidents[2].longitude is None


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (-34.9, -34.9),
        ("138.6", 138.6),
        ("", None),
        (None, None),
        ("bad", None),
    ],
)
def test_parse_coordinate(value: object, expected: float | None) -> None:
    """Test coordinate parsing."""
    assert parse_coordinate(value) == expected


def test_parse_mfs_first_report_string() -> None:
    """Test live-format MFS first_report strings."""
    parsed = parse_mfs_first_report("Sunday, 30 Aug 2026 18:19:00")
    assert parsed == datetime(2026, 8, 30, 18, 19, tzinfo=ZoneInfo(SA_TIMEZONE))


def test_parse_mfs_first_report_epoch_milliseconds() -> None:
    """Test epoch millisecond timestamps are supported if encountered."""
    parsed = parse_mfs_first_report(1_700_000_000_000)
    assert parsed is not None
    assert parsed.tzinfo is not None


def test_parse_mfs_coordinates_invalid_range() -> None:
    """Test out-of-range coordinates become None."""
    latitude, longitude = parse_mfs_coordinates({"lat": 95.0, "long": 200.0})
    assert latitude is None
    assert longitude is None


def test_normalize_mfs_missing_id_returns_none() -> None:
    """Test records without id are skipped."""
    assert normalize_mfs_incident({"status": "GOING"}) is None
