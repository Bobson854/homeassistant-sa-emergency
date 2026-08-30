"""Constants for the SA Emergency integration."""

from datetime import timedelta

DOMAIN = "sa_emergency"
NAME = "SA Emergency"

# CFS source configuration.
AGENCY_CFS = "CFS"
SOURCE_CFS_CURRENT_INCIDENTS = "cfs_current_incidents"
CFS_INCIDENTS_URL = (
    "https://data.eso.sa.gov.au/prod/cfs/criimson/cfs_current_incidents.json"
)
CFS_REQUEST_TIMEOUT_SECONDS = 30

# Timezone for CFS Date/Time fields (South Australia).
CFS_TIMEZONE = "Australia/Adelaide"

# Planned V1 defaults (used when options flow is implemented).
DEFAULT_LOCAL_RADIUS_KM = 25
DEFAULT_REGIONAL_RADIUS_KM = 100
DEFAULT_UPDATE_INTERVAL_SECONDS = 180

DEFAULT_SCAN_INTERVAL = timedelta(seconds=DEFAULT_UPDATE_INTERVAL_SECONDS)

# Relevance classification values (planned V1).
RELEVANCE_NONE = "none"
RELEVANCE_REGIONAL = "regional"
RELEVANCE_LOCAL = "local"

SOURCE_STATUS_OK = "ok"
SOURCE_STATUS_ERROR = "error"

# Temporary development sensor — not part of the final V1 entity contract.
SCAFFOLD_SENSOR_KEY = "status"

# Limit normalized incident summary exposed through development sensor attributes.
DEV_SENSOR_INCIDENT_SAMPLE_LIMIT = 5
