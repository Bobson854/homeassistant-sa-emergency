"""Tests for relevance classification."""

import pytest

from custom_components.sa_emergency.const import (
    RELEVANCE_LOCAL,
    RELEVANCE_NONE,
    RELEVANCE_REGIONAL,
)
from custom_components.sa_emergency.relevance import classify_relevance

LOCAL_RADIUS = 25.0
REGIONAL_RADIUS = 100.0


@pytest.mark.parametrize(
    ("distance", "expected"),
    [
        (0.0, RELEVANCE_LOCAL),
        (10.0, RELEVANCE_LOCAL),
        (24.99, RELEVANCE_LOCAL),
        (25.0, RELEVANCE_LOCAL),
        (25.04, RELEVANCE_REGIONAL),
        (50.0, RELEVANCE_REGIONAL),
        (100.0, RELEVANCE_REGIONAL),
        (100.01, RELEVANCE_NONE),
        (250.0, RELEVANCE_NONE),
    ],
)
def test_classify_relevance_boundaries(distance: float, expected: str) -> None:
    """Test relevance classification uses full-precision distance boundaries."""
    assert classify_relevance(distance, LOCAL_RADIUS, REGIONAL_RADIUS) == expected


def test_rounded_distance_does_not_change_boundary_classification() -> None:
    """Test 25.04 km remains regional even though rounded distance is 25.0."""
    assert (
        classify_relevance(25.04, LOCAL_RADIUS, REGIONAL_RADIUS) == RELEVANCE_REGIONAL
    )


def test_invalid_local_radius_raises() -> None:
    """Test zero local radius is rejected."""
    with pytest.raises(ValueError, match="Local radius"):
        classify_relevance(10.0, 0.0, REGIONAL_RADIUS)


def test_invalid_regional_radius_raises() -> None:
    """Test regional radius must exceed local radius."""
    with pytest.raises(ValueError, match="Regional radius"):
        classify_relevance(10.0, LOCAL_RADIUS, LOCAL_RADIUS)
