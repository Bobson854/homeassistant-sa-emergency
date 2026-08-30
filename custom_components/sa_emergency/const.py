"""Constants for the SA Emergency integration."""

from datetime import timedelta

DOMAIN = "sa_emergency"
NAME = "SA Emergency"

# Planned V1 defaults (used when options flow is implemented).
DEFAULT_LOCAL_RADIUS_KM = 25
DEFAULT_REGIONAL_RADIUS_KM = 100
DEFAULT_UPDATE_INTERVAL_SECONDS = 180

DEFAULT_SCAN_INTERVAL = timedelta(seconds=DEFAULT_UPDATE_INTERVAL_SECONDS)

# Relevance classification values (planned V1).
RELEVANCE_NONE = "none"
RELEVANCE_REGIONAL = "regional"
RELEVANCE_LOCAL = "local"

# Temporary scaffold sensor — remove when V1 entity set is implemented.
SCAFFOLD_SENSOR_KEY = "status"
