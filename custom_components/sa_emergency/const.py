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

# MFS source configuration.
AGENCY_MFS = "MFS"
SOURCE_MFS_CURRENT_INCIDENTS = "mfs_current_incidents"
MFS_INCIDENTS_URL = (
    "https://cfs.geohub.sa.gov.au/server/rest/services/"
    "CFS_Incident_Read/MFS_Incidents/FeatureServer/0/query"
)
MFS_OUT_FIELDS = (
    "id,incident_name,name,first_report,status,region,aircraft,long,lat,event"
)
MFS_QUERY_PARAMS = {
    "where": "1=1",
    "outFields": MFS_OUT_FIELDS,
    "returnGeometry": "false",
    "f": "json",
}

REQUEST_TIMEOUT_SECONDS = 30

# Timezone for CFS Date/Time and MFS first_report strings (South Australia).
SA_TIMEZONE = "Australia/Adelaide"
CFS_TIMEZONE = SA_TIMEZONE

# Planned V1 defaults (used when options flow is implemented).
DEFAULT_LOCAL_RADIUS_KM = 25.0
DEFAULT_REGIONAL_RADIUS_KM = 100.0
DEFAULT_UPDATE_INTERVAL_SECONDS = 180

# Geographic calculation constants.
EARTH_RADIUS_KM = 6371.0088
SAME_LOCATION_TOLERANCE_KM = 1e-6

# Relevant incident exposure safeguard (enforced in Milestone 5 sensors).
MAX_RELEVANT_INCIDENTS = 50

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
