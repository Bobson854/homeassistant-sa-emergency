"""Constants for the SA Emergency integration."""

from datetime import timedelta

DOMAIN = "sa_emergency"
NAME = "SA Emergency"

# Options keys.
CONF_LOCAL_RADIUS_KM = "local_radius_km"
CONF_REGIONAL_RADIUS_KM = "regional_radius_km"
CONF_INCLUDE_CFS = "include_cfs"
CONF_INCLUDE_MFS = "include_mfs"

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

MIN_LOCAL_RADIUS_KM = 1
MAX_LOCAL_RADIUS_KM = 200
MIN_REGIONAL_RADIUS_KM = 2
MAX_REGIONAL_RADIUS_KM = 500
MIN_SCAN_INTERVAL_SECONDS = 60
MAX_SCAN_INTERVAL_SECONDS = 900

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
SOURCE_STATUS_DISABLED = "disabled"

# Stable V1 sensor unique ID suffixes.
SENSOR_UNIQUE_INCIDENTS = "sa_emergency_incidents"
SENSOR_UNIQUE_LOCAL_INCIDENTS = "sa_emergency_local_incidents"
SENSOR_UNIQUE_REGIONAL_INCIDENTS = "sa_emergency_regional_incidents"
SENSOR_UNIQUE_NEAREST_INCIDENT = "sa_emergency_nearest_incident"
SENSOR_UNIQUE_HIGHEST_RELEVANCE = "sa_emergency_highest_relevance"
SENSOR_UNIQUE_CFS_INCIDENTS = "sa_emergency_cfs_incidents"
SENSOR_UNIQUE_MFS_INCIDENTS = "sa_emergency_mfs_incidents"
