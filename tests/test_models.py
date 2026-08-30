"""Tests for normalized incident models."""

import pytest

from custom_components.sa_emergency.const import (
    AGENCY_CFS,
    AGENCY_MFS,
    SOURCE_CFS_CURRENT_INCIDENTS,
    SOURCE_MFS_CURRENT_INCIDENTS,
)
from custom_components.sa_emergency.models import Incident, SaEmergencyData


def _incident(agency: str, source: str, incident_id: str) -> Incident:
    return Incident(
        incident_id=incident_id,
        agency=agency,
        source=source,
        incident_type=None,
        status=None,
        level=None,
        first_reported=None,
        location_name=None,
        latitude=None,
        longitude=None,
        region=None,
        fire_ban_district=None,
        resources=None,
        aircraft_count=None,
        message=None,
        message_url=None,
    )


def test_sa_emergency_data_filters_agency_incidents() -> None:
    """Test mixed collections return correct agency subsets."""
    data = SaEmergencyData(
        incidents_all=[
            _incident(AGENCY_CFS, SOURCE_CFS_CURRENT_INCIDENTS, "CFS:1"),
            _incident(AGENCY_MFS, SOURCE_MFS_CURRENT_INCIDENTS, "MFS:2"),
            _incident(AGENCY_CFS, SOURCE_CFS_CURRENT_INCIDENTS, "CFS:3"),
        ]
    )

    assert [incident.incident_id for incident in data.cfs_incidents] == [
        "CFS:1",
        "CFS:3",
    ]
    assert [incident.incident_id for incident in data.mfs_incidents] == ["MFS:2"]


def test_sa_emergency_data_filters_relevant_agency_incidents() -> None:
    """Test relevant agency helpers return only relevant subsets."""
    local_cfs = _incident(AGENCY_CFS, SOURCE_CFS_CURRENT_INCIDENTS, "CFS:1")
    local_cfs.relevance = "local"
    regional_mfs = _incident(AGENCY_MFS, SOURCE_MFS_CURRENT_INCIDENTS, "MFS:2")
    regional_mfs.relevance = "regional"
    statewide_cfs = _incident(AGENCY_CFS, SOURCE_CFS_CURRENT_INCIDENTS, "CFS:3")
    statewide_cfs.relevance = "none"

    data = SaEmergencyData(
        incidents_all=[local_cfs, regional_mfs, statewide_cfs],
        incidents_relevant=[local_cfs, regional_mfs],
        incidents_local=[local_cfs],
        incidents_regional=[regional_mfs],
    )

    assert [item.incident_id for item in data.cfs_relevant_incidents] == ["CFS:1"]
    assert [item.incident_id for item in data.mfs_relevant_incidents] == ["MFS:2"]
    assert [item.incident_id for item in data.cfs_incidents] == ["CFS:1", "CFS:3"]


def test_incident_requires_explicit_source() -> None:
    """Test Incident source must be supplied explicitly."""
    with pytest.raises(TypeError):
        Incident(
            incident_id="CFS:1",
            agency=AGENCY_CFS,
            incident_type=None,
            status=None,
            level=None,
            first_reported=None,
            location_name=None,
            latitude=None,
            longitude=None,
            region=None,
            fire_ban_district=None,
            resources=None,
            aircraft_count=None,
            message=None,
            message_url=None,
        )
