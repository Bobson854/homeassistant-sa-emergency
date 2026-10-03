"""Tests for IMS incident normalization."""

from datetime import UTC, datetime

from tests.fixtures import load_json_fixture

from custom_components.sa_emergency.const import (
    AGENCY_CFS,
    AGENCY_MFS,
    SOURCE_IMS_CURRENT_INCIDENTS,
)
from custom_components.sa_emergency.normalizer import (
    classify_ims_agency,
    normalize_ims_incident,
    parse_ims_epoch_milliseconds,
    parse_ims_first_reported,
    parse_ims_location_name,
    parse_ims_message,
)


def test_normalize_ims_cfs_onkaparinga_hills() -> None:
    """Test CFS sample from the live IMS feed normalizes as specified."""
    record = load_json_fixture("ims_cfs_onkaparinga_hills.json")
    incident = normalize_ims_incident(record)

    assert incident is not None
    assert incident.incident_id == "CFS:F2610030053"
    assert incident.agency == AGENCY_CFS
    assert incident.incident_type == "Burn Off"
    assert incident.status == "Controlled"
    assert incident.level == "1"
    assert incident.location_name == "KELLYS, ONKAPARINGA HILLS"
    assert incident.fire_ban_district == "MOUNT LOFTY RANGES"
    assert incident.latitude == -35.124724
    assert incident.longitude == 138.558058
    assert incident.first_reported == datetime.fromtimestamp(
        1791006922000 / 1000, tz=UTC
    )
    assert incident.resources is None
    assert incident.aircraft_count is None
    assert incident.region is None
    assert incident.source == SOURCE_IMS_CURRENT_INCIDENTS
    assert incident.message_url == "https://www.cfs.sa.gov.au/incidents"
    assert "Onkaparinga Hills" in (incident.message or "")


def test_normalize_ims_mfs_st_agnes() -> None:
    """Test MFS sample from the live IMS feed normalizes correctly."""
    record = load_json_fixture("ims_mfs_st_agnes.json")
    incident = normalize_ims_incident(record)

    assert incident is not None
    assert incident.incident_id == "MFS:F2608270132"
    assert incident.agency == AGENCY_MFS
    assert incident.incident_type == "Burn Off"
    assert classify_ims_agency(record["authority"]) == AGENCY_MFS


def test_classify_ims_agency_case_insensitive() -> None:
    """Test authority matching tolerates case differences."""
    assert classify_ims_agency("south australian country fire service") == AGENCY_CFS
    assert (
        classify_ims_agency("SOUTH AUSTRALIAN METROPOLITAN FIRE SERVICE") == AGENCY_MFS
    )


def test_unknown_authority_returns_none() -> None:
    """Test unsupported authorities are not classified."""
    assert classify_ims_agency("Unknown Emergency Service") is None
    assert normalize_ims_incident({"ident": "X", "authority": "Other"}) is None


def test_missing_optional_attributes() -> None:
    """Test minimal IMS records still normalize when identity fields exist."""
    incident = normalize_ims_incident(
        {
            "ident": "MIN1",
            "authority": "South Australian Country Fire Service",
            "event": "Grass Fire",
        }
    )
    assert incident is not None
    assert incident.incident_id == "CFS:MIN1"
    assert incident.location_name is None
    assert incident.first_reported is None


def test_location_fallback_to_inc_name() -> None:
    """Test location_name falls back to inc_name when location is absent."""
    assert (
        parse_ims_location_name({"inc_name": "HILLTOP", "location": None}) == "HILLTOP"
    )


def test_message_fallback_order() -> None:
    """Test message preference incs, headline, title, instruct."""
    assert parse_ims_message({"incs": "primary"}) == "primary"
    assert parse_ims_message({"headline": "headline"}) == "headline"
    assert parse_ims_message({"title": "title", "instruct": "instruct"}) == "title"


def test_malformed_coordinates() -> None:
    """Test invalid coordinates are dropped without failing normalization."""
    incident = normalize_ims_incident(
        {
            "ident": "BADCOORD",
            "authority": "South Australian Country Fire Service",
            "lat": "invalid",
            "long": 999,
        }
    )
    assert incident is not None
    assert incident.latitude is None
    assert incident.longitude is None


def test_malformed_epoch_timestamp() -> None:
    """Test invalid epoch values are ignored for first_reported."""
    assert parse_ims_epoch_milliseconds("not-a-number") is None
    assert parse_ims_epoch_milliseconds(0) is None
    assert parse_ims_epoch_milliseconds(-1) is None
    assert parse_ims_first_reported(
        {"effective": "bad", "sent": 1791006922000, "updated": 0}
    ) == datetime.fromtimestamp(1791006922000 / 1000, tz=UTC)
