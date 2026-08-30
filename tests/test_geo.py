"""Tests for geographic calculations."""

import math

import pytest

from custom_components.sa_emergency.geo import (
    bearing_to_cardinal,
    calculate_distance_km,
    calculate_initial_bearing,
    is_same_location,
    round_distance_km,
)

# Public South Australian reference coordinates.
ADELAIDE_LAT = -34.9285
ADELAIDE_LON = 138.6007
MOUNT_GAMBIER_LAT = -37.831
MOUNT_GAMBIER_LON = 140.779
PORT_AUGUSTA_LAT = -32.492
PORT_AUGUSTA_LON = 137.765


def test_identical_locations_have_zero_distance() -> None:
    """Test identical coordinates produce zero distance."""
    distance = calculate_distance_km(
        ADELAIDE_LAT, ADELAIDE_LON, ADELAIDE_LAT, ADELAIDE_LON
    )
    assert distance == pytest.approx(0.0, abs=1e-9)
    assert is_same_location(ADELAIDE_LAT, ADELAIDE_LON, ADELAIDE_LAT, ADELAIDE_LON)


def test_identical_locations_have_no_bearing() -> None:
    """Test same-location incidents should not receive a manufactured bearing."""
    assert is_same_location(ADELAIDE_LAT, ADELAIDE_LON, ADELAIDE_LAT, ADELAIDE_LON)


def test_known_northward_bearing() -> None:
    """Test a target directly north returns a northerly bearing."""
    target_lat = ADELAIDE_LAT + 0.5
    bearing = calculate_initial_bearing(
        ADELAIDE_LAT, ADELAIDE_LON, target_lat, ADELAIDE_LON
    )
    assert bearing == pytest.approx(0.0, abs=0.5)
    assert bearing_to_cardinal(bearing) == "N"


def test_known_eastward_bearing() -> None:
    """Test a target directly east returns an easterly bearing."""
    target_lon = ADELAIDE_LON + 0.5
    bearing = calculate_initial_bearing(
        ADELAIDE_LAT, ADELAIDE_LON, ADELAIDE_LAT, target_lon
    )
    assert bearing == pytest.approx(90.0, abs=0.5)
    assert bearing_to_cardinal(bearing) == "E"


def test_known_southward_bearing() -> None:
    """Test a target directly south returns a southerly bearing."""
    target_lat = ADELAIDE_LAT - 0.5
    bearing = calculate_initial_bearing(
        ADELAIDE_LAT, ADELAIDE_LON, target_lat, ADELAIDE_LON
    )
    assert bearing == pytest.approx(180.0, abs=0.5)
    assert bearing_to_cardinal(bearing) == "S"


def test_known_westward_bearing() -> None:
    """Test a target directly west returns a westerly bearing."""
    target_lon = ADELAIDE_LON - 0.5
    bearing = calculate_initial_bearing(
        ADELAIDE_LAT, ADELAIDE_LON, ADELAIDE_LAT, target_lon
    )
    assert bearing == pytest.approx(270.0, abs=0.5)
    assert bearing_to_cardinal(bearing) == "W"


@pytest.mark.parametrize(
    ("bearing", "expected"),
    [
        (45.0, "NE"),
        (135.0, "SE"),
        (225.0, "SW"),
        (315.0, "NW"),
    ],
)
def test_intercardinal_bearings(bearing: float, expected: str) -> None:
    """Test diagonal bearings map to intercardinal directions."""
    assert bearing_to_cardinal(bearing) == expected


def test_southern_hemisphere_adelaide_to_mount_gambier_distance() -> None:
    """Test a real-ish South Australian distance against an independent estimate."""
    distance = calculate_distance_km(
        ADELAIDE_LAT, ADELAIDE_LON, MOUNT_GAMBIER_LAT, MOUNT_GAMBIER_LON
    )
    assert distance == pytest.approx(377.0, abs=5.0)


def test_bearing_normalization_wraps_to_zero_three_sixty() -> None:
    """Test bearing normalization stays within [0, 360)."""
    bearing = calculate_initial_bearing(
        ADELAIDE_LAT, ADELAIDE_LON, ADELAIDE_LAT, ADELAIDE_LON - 0.01
    )
    assert 0.0 <= bearing < 360.0


def test_cardinal_boundary_n_sector() -> None:
    """Test northerly sector boundaries including wraparound near zero."""
    assert bearing_to_cardinal(0.0) == "N"
    assert bearing_to_cardinal(22.499) == "N"
    assert bearing_to_cardinal(359.999) == "N"
    assert bearing_to_cardinal(337.5) == "N"


@pytest.mark.parametrize(
    ("bearing", "expected"),
    [
        (22.5, "NE"),
        (67.499, "NE"),
        (67.5, "E"),
        (112.5, "SE"),
        (157.5, "S"),
        (202.5, "SW"),
        (247.5, "W"),
        (292.5, "NW"),
        (337.499, "NW"),
    ],
)
def test_cardinal_sector_boundaries(bearing: float, expected: str) -> None:
    """Test explicit eight-point compass sector boundaries."""
    assert bearing_to_cardinal(bearing) == expected


def test_adelaide_to_port_augusta_bearing_is_north_westerly() -> None:
    """Test a public SA reference bearing is north-westerly from Adelaide."""
    bearing = calculate_initial_bearing(
        ADELAIDE_LAT, ADELAIDE_LON, PORT_AUGUSTA_LAT, PORT_AUGUSTA_LON
    )
    assert bearing == pytest.approx(345.0, abs=3.0)
    assert bearing_to_cardinal(bearing) == "N"


def test_round_distance_km_uses_one_decimal_place() -> None:
    """Test stored distance rounding policy."""
    assert round_distance_km(27.44) == 27.4
    assert round_distance_km(25.04) == 25.0


def test_bearing_output_is_normalized() -> None:
    """Test atan2 output is normalized even near quadrant boundaries."""
    bearing = calculate_initial_bearing(
        ADELAIDE_LAT, ADELAIDE_LON, ADELAIDE_LAT + 0.01, ADELAIDE_LON + 0.01
    )
    assert 0.0 <= bearing < 360.0
    assert not math.isnan(bearing)
