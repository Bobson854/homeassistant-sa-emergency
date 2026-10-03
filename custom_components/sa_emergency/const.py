"""Constants for the SA Emergency integration."""

from datetime import timedelta

DOMAIN = "sa_emergency"
NAME = "SA Emergency"

# Options keys.
CONF_LOCAL_RADIUS_KM = "local_radius_km"
CONF_REGIONAL_RADIUS_KM = "regional_radius_km"
CONF_INCLUDE_CFS = "include_cfs"
CONF_INCLUDE_MFS = "include_mfs"

# Agencies.
AGENCY_CFS = "CFS"
AGENCY_MFS = "MFS"

# Current combined IMS incident feed (official CFS map public source).
SOURCE_IMS_CURRENT_INCIDENTS = "ims_current_incidents"
IMS_INCIDENTS_URL = (
    "https://cfs-feeds.geohub.sa.gov.au/FL/"
    "IMS_Read/SACFS_and_SAMFS_Incidents_and_Incident_Updates/FeatureServer/1/query"
)
IMS_QUERY_PARAMS = {
    "where": "1=1",
    "outFields": "*",
    "returnGeometry": "false",
    "f": "json",
}

# Per-agency runtime status keys retained for existing sensors and diagnostics.
SOURCE_CFS_CURRENT_INCIDENTS = "cfs_current_incidents"
SOURCE_MFS_CURRENT_INCIDENTS = "mfs_current_incidents"

# IMS authority values (case-insensitive match).
IMS_AUTHORITY_CFS = "South Australian Country Fire Service"
IMS_AUTHORITY_MFS = "South Australian Metropolitan Fire Service"

# Legacy source identifiers retained for legacy normalizer tests only.
LEGACY_SOURCE_CFS_CURRENT_INCIDENTS = "cfs_current_incidents"
LEGACY_SOURCE_MFS_CURRENT_INCIDENTS = "mfs_current_incidents"

REQUEST_TIMEOUT_SECONDS = 30

# Timezone for legacy CFS Date/Time and MFS first_report string parsers.
SA_TIMEZONE = "Australia/Adelaide"
CFS_TIMEZONE = SA_TIMEZONE

DEFAULT_LOCAL_RADIUS_KM = 25.0
DEFAULT_REGIONAL_RADIUS_KM = 100.0
DEFAULT_UPDATE_INTERVAL_SECONDS = 180

MIN_LOCAL_RADIUS_KM = 1
MAX_LOCAL_RADIUS_KM = 200
MIN_REGIONAL_RADIUS_KM = 2
MAX_REGIONAL_RADIUS_KM = 500
MIN_SCAN_INTERVAL_SECONDS = 60
MAX_SCAN_INTERVAL_SECONDS = 900

EARTH_RADIUS_KM = 6371.0088
SAME_LOCATION_TOLERANCE_KM = 1e-6

MAX_RELEVANT_INCIDENTS = 50

DEFAULT_SCAN_INTERVAL = timedelta(seconds=DEFAULT_UPDATE_INTERVAL_SECONDS)

RELEVANCE_NONE = "none"
RELEVANCE_REGIONAL = "regional"
RELEVANCE_LOCAL = "local"

SOURCE_STATUS_OK = "ok"
SOURCE_STATUS_ERROR = "error"
SOURCE_STATUS_DISABLED = "disabled"

SENSOR_UNIQUE_INCIDENTS = "sa_emergency_incidents"
SENSOR_UNIQUE_LOCAL_INCIDENTS = "sa_emergency_local_incidents"
SENSOR_UNIQUE_REGIONAL_INCIDENTS = "sa_emergency_regional_incidents"
SENSOR_UNIQUE_NEAREST_INCIDENT = "sa_emergency_nearest_incident"
SENSOR_UNIQUE_HIGHEST_RELEVANCE = "sa_emergency_highest_relevance"
SENSOR_UNIQUE_CFS_INCIDENTS = "sa_emergency_cfs_incidents"
SENSOR_UNIQUE_MFS_INCIDENTS = "sa_emergency_mfs_incidents"
