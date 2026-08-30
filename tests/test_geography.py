"""Tests for geographic enrichment and collection building."""

import pytest
from tests.conftest import TEST_HOME_LAT, TEST_HOME_LON

from custom_components.sa_emergency.const import (
    AGENCY_CFS,
    RELEVANCE_LOCAL,
    RELEVANCE_NONE,
    RELEVANCE_REGIONAL,
    SOURCE_CFS_CURRENT_INCIDENTS,
)
from custom_components.sa_emergency.geography import (
    apply_geographic_context,
    build_geographic_data,
)
from custom_components.sa_emergency.models import Incident


def _incident(
    incident_id: str,
    *,
    latitude: float | None,
    longitude: float | None,
) -> Incident:
    return Incident(
        incident_id=incident_id,
        agency=AGENCY_CFS,
        source=SOURCE_CFS_CURRENT_INCIDENTS,
        incident_type="Grass Fire",
        status="GOING",
        level=None,
        first_reported=None,
        location_name="Test Location",
        latitude=latitude,
        longitude=longitude,
        region=None,
        fire_ban_district=None,
        resources=None,
        aircraft_count=None,
        message=None,
        message_url=None,
    )


def test_non_spatial_incident_retained_as_non_relevant() -> None:
    """Test non-spatial incidents remain in all incidents but not relevant sets."""
    data = build_geographic_data(
        [_incident("CFS:1", latitude=None, longitude=None)],
        TEST_HOME_LAT,
        TEST_HOME_LON,
    )

    assert len(data.incidents_all) == 1
    assert data.incidents_relevant == []
    assert data.incidents_local == []
    assert data.incidents_regional == []
    assert data.incidents_all[0].relevance == RELEVANCE_NONE
    assert data.incidents_all[0].distance_km is None
    assert data.non_spatial_incident_count == 1


def test_same_location_has_zero_distance_and_no_bearing() -> None:
    """Test incidents at the HA location have zero distance and no bearing."""
    enriched, precise = apply_geographic_context(
        _incident("CFS:HOME", latitude=TEST_HOME_LAT, longitude=TEST_HOME_LON),
        TEST_HOME_LAT,
        TEST_HOME_LON,
        25.0,
        100.0,
    )

    assert precise == pytest.approx(0.0, abs=1e-9)
    assert enriched.distance_km == 0.0
    assert enriched.bearing_degrees is None
    assert enriched.bearing_cardinal is None
    assert enriched.relevance == RELEVANCE_LOCAL


def test_outside_radius_retained_in_all_incidents() -> None:
    """Test distant incidents remain in incidents_all but not relevant sets."""
    distant = _incident("CFS:FAR", latitude=-37.831, longitude=140.779)
    data = build_geographic_data([distant], TEST_HOME_LAT, TEST_HOME_LON)

    assert len(data.incidents_all) == 1
    assert data.incidents_relevant == []
    assert data.incidents_all[0].relevance == RELEVANCE_NONE


def test_relevant_collections_sorted_local_before_regional() -> None:
    """Test relevant incidents sort local before regional then by distance."""
    local = _incident("CFS:LOCAL", latitude=-34.95, longitude=138.60)
    regional = _incident("CFS:REGIONAL", latitude=-35.12, longitude=139.57)
    data = build_geographic_data([regional, local], TEST_HOME_LAT, TEST_HOME_LON)

    assert [incident.incident_id for incident in data.incidents_relevant] == [
        "CFS:LOCAL",
        "CFS:REGIONAL",
    ]
    assert data.highest_relevance == RELEVANCE_LOCAL


def test_nearest_incident_uses_full_precision_distance() -> None:
    """Test nearest incident ignores rounded-distance ties when possible."""
    nearer = _incident("CFS:NEAR", latitude=-34.95, longitude=138.60)
    farther = _incident("CFS:FAR", latitude=-35.05, longitude=138.75)
    data = build_geographic_data([farther, nearer], TEST_HOME_LAT, TEST_HOME_LON)

    assert data.nearest_incident is not None
    assert data.nearest_incident.incident_id == "CFS:NEAR"


def test_highest_relevance_regional_when_no_local() -> None:
    """Test highest relevance is regional when only regional incidents exist."""
    regional = _incident("CFS:REGIONAL", latitude=-35.12, longitude=139.57)
    data = build_geographic_data([regional], TEST_HOME_LAT, TEST_HOME_LON)

    assert data.highest_relevance == RELEVANCE_REGIONAL


def test_highest_relevance_none_for_only_non_relevant() -> None:
    """Test highest relevance is none when no local or regional incidents exist."""
    distant = _incident("CFS:FAR", latitude=-37.831, longitude=140.779)
    data = build_geographic_data([distant], TEST_HOME_LAT, TEST_HOME_LON)

    assert data.highest_relevance == RELEVANCE_NONE
    assert data.nearest_incident is None
