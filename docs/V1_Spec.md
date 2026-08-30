# SA Emergency Home Assistant Integration — V1 Specification

Repository: `homeassistant-sa-emergency`
Integration domain: `sa_emergency`
Display name: `SA Emergency`

## 1. Purpose

`SA Emergency` is a Home Assistant custom integration providing location-aware South Australian emergency incident information from authoritative public CFS and MFS data sources.

The integration will:

* poll current CFS and MFS incidents;
* normalize the different source formats into a common internal model;
* use the Home Assistant configured latitude and longitude as the user's reference point;
* calculate incident distance and bearing;
* determine incident relevance;
* expose stable Home Assistant sensors and useful structured attributes;
* provide a clean foundation for dashboards, automations, notifications and later spatial enrichment.

V1 will not maintain a historical incident database.

The authoritative government services remain the source of truth.

---

# 2. V1 Scope

V1 includes:

1. CFS current incident polling.
2. MFS current incident polling.
3. Common normalized incident model.
4. Distance from Home Assistant location.
5. Bearing from Home Assistant location.
6. Local and regional relevance filtering.
7. Stable Home Assistant sensors.
8. Structured incident data exposed as sensor attributes.
9. Config Flow setup.
10. Options Flow for user-adjustable settings.
11. Sensible failure handling.
12. Diagnostics suitable for a public HACS integration.

V1 should be designed so warning support can be added next without restructuring the core integration.

---

# 3. Authoritative V1 Sources

## CFS

Primary feed:

`https://data.eso.sa.gov.au/prod/cfs/criimson/cfs_current_incidents.json`

Useful source fields include:

* `IncidentNo`
* `Date`
* `Time`
* `Message`
* `Message_link`
* `Location_name`
* `Region`
* `Type`
* `Status`
* `Level`
* `FBD`
* `Resources`
* `Aircraft`
* `Location`

The CFS JSON feed is preferred over the CFS ArcGIS incident layer for normal polling because it currently exposes useful operational fields including resources and FBD.

## MFS

Primary feed:

`https://cfs.geohub.sa.gov.au/server/rest/services/CFS_Incident_Read/MFS_Incidents/FeatureServer/0/query`

Expected fields include:

* `id`
* `incident_name`
* `name`
* `first_report`
* `status`
* `region`
* `aircraft`
* `icon`
* `long`
* `lat`
* `event`

MFS incidents should be converted into the same internal incident model as CFS incidents.

---

# 4. Architecture

The integration should separate source acquisition, emergency-domain logic and Home Assistant entity presentation.

Suggested structure:

```text
custom_components/
└── sa_emergency/
    ├── __init__.py
    ├── api.py
    ├── binary_sensor.py
    ├── config_flow.py
    ├── const.py
    ├── coordinator.py
    ├── diagnostics.py
    ├── geo.py
    ├── manifest.json
    ├── models.py
    ├── normalizer.py
    ├── relevance.py
    ├── sensor.py
    ├── strings.json
    └── translations/
        └── en.json
```

Repository root should ultimately include:

```text
.github/
custom_components/
tests/
.gitignore
hacs.json
LICENSE
README.md
pyproject.toml
```

A `DataUpdateCoordinator` should own polling and current runtime state.

Home Assistant sensors must contain minimal emergency-services business logic.

The intended flow is:

```text
Government APIs
      ↓
    api.py
      ↓
 normalizer.py
      ↓
 Normalized Incident objects
      ↓
     geo.py
      ↓
 relevance.py
      ↓
 coordinator.py
      ↓
Home Assistant sensors / attributes
```

---

# 5. Normalized Incident Model

All CFS and MFS records must be converted into one common model before relevance processing.

Suggested model:

```python
Incident:
    incident_id: str
    agency: str

    incident_type: str | None
    status: str | None
    level: str | None

    first_reported: datetime | None

    location_name: str | None
    latitude: float
    longitude: float

    region: str | None
    fire_ban_district: str | None

    resources: int | None
    aircraft_count: int | None

    message: str | None
    message_url: str | None

    distance_km: float | None
    bearing_degrees: float | None
    bearing_cardinal: str | None

    relevance: str

    source: str
```

V1 relevance values:

```text
none
regional
local
```

The model should deliberately allow future extension to:

```text
significant
warning
```

without breaking existing consumers.

---

# 6. Incident Identity

The source incident identifier should be preserved.

Suggested normalized identifier:

```text
CFS:<IncidentNo>
MFS:<id>
```

Examples:

```text
CFS:123456
MFS:654321
```

This prevents accidental collisions between agency numbering schemes.

Incident IDs should be treated as strings.

---

# 7. Home Location

V1 should use Home Assistant's configured location:

```text
hass.config.latitude
hass.config.longitude
```

Do not hard-code Murray Bridge or any other location.

The configured HA location is the centre point for:

* distance;
* bearing;
* local radius;
* regional radius.

V1 does not require a separate coordinate entry during setup.

Future versions may optionally support additional monitored locations.

---

# 8. Distance

Distance should be calculated locally from the incident coordinate and HA coordinate.

Output:

```text
distance_km
```

Suggested precision:

```text
1 decimal place
```

Example:

```text
27.4 km
```

Use a standard great-circle/Haversine calculation.

Do not depend on an external mapping service for distance calculations.

---

# 9. Bearing

Calculate initial bearing from the HA location to the incident.

Expose:

```text
bearing_degrees
bearing_cardinal
```

Example:

```text
bearing_degrees: 314
bearing_cardinal: NW
```

Use standard eight-point cardinal directions for V1:

```text
N
NE
E
SE
S
SW
W
NW
```

---

# 10. Relevance Model

V1 uses two configurable distance bands.

Default values:

```text
Local radius:    25 km
Regional radius: 100 km
```

Classification:

```text
distance <= local radius
    relevance = local

distance > local radius
AND distance <= regional radius
    relevance = regional

distance > regional radius
    relevance = none
```

Incidents with `none` relevance remain available internally during processing but are not exposed through the primary relevant-incident collection.

This logic must be isolated in `relevance.py`.

Do not embed these rules directly in sensors.

This allows later relevance rules to include:

* incident type;
* incident status;
* warning level;
* resource count;
* aircraft involvement;
* polygon intersection;
* fire behaviour;
* exceptional major incidents.

---

# 11. Configuration

Initial setup should require no user-entered values.

Config Flow:

```text
Add Integration
    ↓
SA Emergency
    ↓
Confirm use of Home Assistant location
    ↓
Create entry
```

Only one integration instance should normally be necessary.

V1 Options Flow:

```text
Local radius
Regional radius
Polling interval
Include CFS
Include MFS
```

Defaults:

```text
Local radius:       25 km
Regional radius:    100 km
Polling interval:   180 seconds
Include CFS:        Yes
Include MFS:        Yes
```

Validation:

```text
Local radius > 0
Regional radius > local radius
Polling interval >= 60 seconds
At least one agency enabled
```

Avoid exposing API URLs as normal configuration options.

Endpoints should remain implementation constants unless a development/debug reason later emerges.

---

# 12. Polling

Default polling interval:

```text
180 seconds
```

Recommended allowed range:

```text
60–900 seconds
```

One coordinator refresh should fetch all enabled V1 incident sources.

A failure of one source should not necessarily destroy useful information from the other source.

Example:

```text
CFS successful
MFS failed
```

Result:

* retain/display valid CFS data;
* mark MFS source as unavailable/stale internally;
* log the MFS problem;
* avoid marking the entire integration unavailable unless no useful current data can be obtained.

The coordinator should avoid overlapping refreshes.

---

# 13. Stale Data

The integration should track:

```text
last_update
last_successful_update
source status
```

Do not silently present indefinitely cached emergency data as current.

A future stale threshold can be configurable if required.

For V1, a reasonable internal rule is:

```text
stale after 3 failed expected refresh intervals
```

The integration should make stale state visible through attributes and diagnostics.

---

# 14. Primary Home Assistant Entities

V1 should use stable entities.

Do not create and remove entities dynamically for individual incidents.

## 14.1 `sensor.sa_emergency_incidents`

Primary integration entity.

State:

```text
number of relevant incidents
```

Example:

```text
3
```

Attributes:

```yaml
local_count: 1
regional_count: 2
cfs_count: 2
mfs_count: 1
nearest_incident_id: "CFS:123456"
last_update: "..."
incidents:
  - ...
  - ...
```

The `incidents` attribute contains the normalized relevant incident collection.

---

## 14.2 `sensor.sa_emergency_local_incidents`

State:

```text
number of incidents inside local radius
```

Attributes should contain basic summary information only.

It does not need to duplicate the complete incident collection if that data already exists on the primary sensor.

---

## 14.3 `sensor.sa_emergency_regional_incidents`

State:

```text
number of incidents classified regional
```

This excludes incidents already classified as local.

---

## 14.4 `sensor.sa_emergency_nearest_incident`

State:

Prefer a human-readable incident type or location.

Example:

```text
Grass Fire
```

Attributes:

```yaml
incident_id: "CFS:123456"
agency: "CFS"
type: "Grass Fire"
status: "GOING"
location: "MONARTO"
distance_km: 27.4
bearing_degrees: 314
bearing: "NW"
resources: 4
aircraft: 0
first_reported: "..."
relevance: "regional"
latitude: -35.x
longitude: 139.x
```

If there are no relevant incidents:

```text
state: unknown
```

or an equivalent appropriate HA sensor state.

Avoid using a fake string such as `"None"` as a data value.

---

## 14.5 `sensor.sa_emergency_highest_relevance`

V1 possible states:

```text
none
regional
local
```

Priority:

```text
local > regional > none
```

This entity is intended to be particularly useful for dashboards and automations.

Later versions can extend the states:

```text
significant
warning
```

---

## 14.6 `sensor.sa_emergency_cfs_incidents`

State:

```text
number of relevant CFS incidents
```

---

## 14.7 `sensor.sa_emergency_mfs_incidents`

State:

```text
number of relevant MFS incidents
```

---

# 15. Incident Collection Attribute

The primary sensor should expose a structured relevant incident collection.

Example:

```yaml
incidents:
  - incident_id: "CFS:123456"
    agency: "CFS"
    type: "GRASS FIRE"
    status: "GOING"
    level: null
    first_reported: "2026-08-30T15:32:00+09:30"
    location: "MONARTO"
    latitude: -35.1234
    longitude: 139.1234
    distance_km: 27.4
    bearing_degrees: 314
    bearing: "NW"
    relevance: "regional"
    region: "3"
    fire_ban_district: "Murraylands"
    resources: 4
    aircraft: 0
    message: "..."
    message_url: "..."

  - incident_id: "MFS:654321"
    agency: "MFS"
    type: "STRUCTURE FIRE"
    status: "RESPONDING"
    first_reported: "..."
    location: "MURRAY BRIDGE"
    latitude: -35.12
    longitude: 139.26
    distance_km: 3.2
    bearing_degrees: 95
    bearing: "E"
    relevance: "local"
```

Only normalized fields should be exposed here.

Do not simply copy entire raw API records into HA attributes.

---

# 16. Attribute Size

Home Assistant state attributes are not intended to become an unlimited incident datastore.

Therefore V1 should expose only relevant incidents inside the regional radius.

If unexpectedly large incident volumes occur, apply a safety limit.

Suggested initial maximum:

```text
50 relevant incidents
```

Sort order:

1. relevance priority;
2. distance ascending;
3. first reported descending where necessary.

This limit should be an internal safeguard rather than a normal user-facing option.

---

# 17. Sorting

The main incident collection should sort:

```text
local first
then regional
```

Within each relevance class:

```text
nearest first
```

This makes the attribute immediately useful to dashboards without requiring every card to rebuild the sorting logic.

---

# 18. Source-Specific Normalization

## CFS

Map source values into common fields.

Examples:

```text
IncidentNo      → incident_id
Type            → incident_type
Status          → status
Level           → level
Location_name   → location_name
Region          → region
FBD             → fire_ban_district
Resources       → resources
Aircraft        → aircraft_count
Message         → message
Message_link    → message_url
Location        → latitude / longitude
```

Date and Time should be combined into a timezone-aware `first_reported` value where reliably possible.

Malformed coordinates should cause the specific incident to be rejected or marked non-spatial rather than crashing the coordinator.

## MFS

Map:

```text
id              → incident_id
event           → incident_type
status          → status
name /
incident_name   → location_name / description as appropriate
first_report    → first_reported
region          → region
aircraft        → aircraft_count
lat             → latitude
long            → longitude
```

Fields unavailable from MFS should remain `None`.

Do not fabricate equivalent values.

---

# 19. Error Handling

The integration must tolerate:

* API timeout;
* non-200 HTTP response;
* malformed JSON;
* ArcGIS error response;
* missing expected fields;
* malformed incident coordinates;
* individual malformed incident records;
* temporary empty feeds.

One bad incident record must not prevent the remaining valid records from being processed.

Errors should be logged at an appropriate level without filling Home Assistant logs every polling cycle with repeated identical messages.

---

# 20. API Behaviour

`api.py` should contain source-specific request handling.

Suggested classes:

```text
CFSClient
MFSClient
```

or one client with clearly separated methods:

```python
async def async_get_cfs_incidents()
async def async_get_mfs_incidents()
```

API code should return source records.

It should not perform HA entity creation or relevance decisions.

HTTP should use Home Assistant's shared async session.

No blocking HTTP libraries.

---

# 21. Coordinator Runtime Data

Suggested coordinator data structure:

```python
SAEmergencyData:
    incidents_all
    incidents_relevant
    incidents_local
    incidents_regional

    nearest_incident

    cfs_count
    mfs_count

    highest_relevance

    last_update
    source_status
```

This should become the common data object consumed by all entities.

Future fields can include:

```text
warnings
beats
aircraft
aviation_facilities
fire_footprints
```

without fundamentally altering the entity architecture.

---

# 22. Diagnostics

Provide diagnostics suitable for issue reporting.

Include:

* integration version;
* configured radii;
* polling interval;
* enabled agencies;
* number of source incidents;
* number of relevant incidents;
* source request status;
* last successful update;
* parsing/error summaries.

Redact:

* exact Home Assistant latitude;
* exact Home Assistant longitude;
* any future user-defined private locations.

Incident coordinates originate from public government feeds and are not inherently user-private, but diagnostics should still avoid unnecessary bulk dumping of all raw records.

---

# 23. Logging

Normal operation should be quiet.

Suggested levels:

`DEBUG`

* polling started;
* source record counts;
* normalized counts;
* relevance counts;
* individual skipped malformed records.

`WARNING`

* individual source unavailable;
* malformed source response;
* repeated parsing issue.

`ERROR`

* integration unable to obtain usable information from all configured sources for a sustained period.

---

# 24. Naming

Integration:

```text
SA Emergency
```

Domain:

```text
sa_emergency
```

Suggested entity names:

```text
SA Emergency Incidents
SA Emergency Local Incidents
SA Emergency Regional Incidents
SA Emergency Nearest Incident
SA Emergency Highest Relevance
SA Emergency CFS Incidents
SA Emergency MFS Incidents
```

Exact generated entity IDs may depend on Home Assistant entity naming behaviour and should not be relied upon internally.

Use unique IDs based on stable logical keys such as:

```text
sa_emergency_incidents
sa_emergency_local_incidents
sa_emergency_regional_incidents
sa_emergency_nearest_incident
sa_emergency_highest_relevance
sa_emergency_cfs_incidents
sa_emergency_mfs_incidents
```

---

# 25. V1 Exclusions

Do not implement these in the first V1 milestone:

* warning polygons;
* warning notifications;
* SAFECOM beat lookup;
* CFS communications plans;
* TracPlus aircraft positions;
* recognised airbases;
* recognised helibases;
* Primary Response Zones;
* CFS station capabilities;
* fire-danger ratings;
* Total Fire Bans;
* burnt-area polygons;
* planned burns;
* SES-specific ingestion;
* pager feeds;
* scanner integration;
* incident history database;
* custom Lovelace card;
* custom Home Assistant panel;
* dynamic per-incident entities.

They remain valid future features.

The existing research establishes that warnings, aviation infrastructure, aircraft tracking and response geography are useful enrichment datasets, but they should only be queried when they improve an actual relevant incident view.

---

# 26. V1.1 — Immediate Next Feature

Once V1 incident polling is stable, the first extension should be CFS public warnings.

Sources:

```text
CFS warning points
CFS warning polygons
```

Warning support should add:

```text
binary_sensor.sa_emergency_warning_active
```

and extend relevance to:

```text
none
regional
local
significant
warning
```

The most important future spatial rule will be:

```text
warning polygon contains HA location
```

This should outrank ordinary distance-based relevance.

---

# 27. Future Enrichment Architecture

Enrichment should be incident-driven rather than globally polled.

Conceptually:

```text
Incident becomes relevant
        ↓
Determine whether enrichment is useful
        ↓
Fire?
    ├── beat lookup
    ├── fire footprint
    ├── nearby airbases
    ├── nearby helibases
    └── recent aircraft
```

Do not continuously fetch every discovered government dataset.

The reference research specifically identifies TracPlus and the Aviation Operations datasets as valuable but notes that aircraft must be filtered geographically and by freshness, and proximity must not be treated as proof of incident assignment.

---

# 28. Testing Requirements

Unit tests should cover at minimum:

## Normalization

* valid CFS incident;
* valid MFS incident;
* missing optional fields;
* malformed coordinates;
* invalid resources/aircraft values.

## Geography

* known distance calculation;
* known bearing calculation;
* cardinal conversion.

## Relevance

* inside local radius;
* exact local boundary;
* regional incident;
* exact regional boundary;
* outside regional radius.

## Coordinator

* both sources successful;
* CFS only successful;
* MFS only successful;
* one malformed incident;
* empty feeds;
* total API failure.

## Configuration

* defaults;
* invalid local radius;
* regional radius smaller than local;
* invalid poll interval;
* both agencies disabled.

---

# 29. README Minimum Content

Before public release, README should explain:

* what the integration does;
* that it is not an official CFS/MFS product;
* authoritative source attribution;
* installation via HACS custom repository;
* manual installation;
* configuration;
* provided entities;
* example incident attributes;
* suggested dashboard use;
* known limitations;
* data freshness;
* privacy behaviour;
* issue reporting.

Include a clear disclaimer that emergency-service information in Home Assistant must not be relied upon as the sole source for emergency warnings or personal safety decisions.

---

# 30. Repository Milestones

## Milestone 1 — Scaffold

* integration loads;
* manifest;
* Config Flow;
* coordinator skeleton;
* HACS metadata;
* tests running.

## Milestone 2 — CFS

* fetch CFS feed;
* normalize incidents;
* unit tests.

## Milestone 3 — MFS

* fetch MFS ArcGIS feed;
* normalize incidents;
* combine both sources.

## Milestone 4 — Geography

* HA location;
* distance;
* bearing;
* relevance.

## Milestone 5 — Entities

* all V1 sensors;
* structured incident attribute;
* unavailable/stale handling.

## Milestone 6 — Public-repo quality

* diagnostics;
* README;
* tests;
* HACS validation;
* Hassfest validation;
* first tagged release.

---

# 31. Definition of V1 Complete

V1 is complete when a user can install the integration through HACS, configure it entirely through the Home Assistant UI, and reliably answer:

> What current official CFS or MFS incidents are relevant to my Home Assistant location?

Home Assistant must provide:

* how many relevant incidents exist;
* how many are local;
* how many are regional;
* which agency they belong to;
* which incident is nearest;
* how far away it is;
* in what direction;
* useful available operational details;
* one normalized structured incident collection suitable for dashboards and automations.

No external database, Node-RED workflow or standalone supporting service should be required.
