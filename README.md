# SA Emergency

**V1 preview — early public testing** (version `0.6.1`)

SA Emergency is a [Home Assistant](https://www.home-assistant.io/) custom integration for location-aware **CFS** and **MFS** incident information across South Australia. It periodically refreshes current incidents from public feeds, compares them with your Home Assistant home location, and exposes counts and structured details as sensors for dashboards, templates, notifications, and automations.

This is an **independent community project**. It is **not** an official CFS or MFS product and **not** a substitute for official emergency warnings. Use official emergency-service channels for safety decisions.

## At a glance

- Monitors **current** CFS and MFS incidents (one combined public feed; see [Source behaviour](#source--data-behaviour)).
- Uses your **Home Assistant configured latitude/longitude** locally for distance, bearing, and relevance — coordinates are **not** sent to the upstream feed.
- Classifies incidents as **local**, **regional**, or outside your configured radii.
- Exposes **seven stable sensors** plus normalized incident attributes on the primary Incidents sensor.
- Runs entirely inside Home Assistant — **no** external database or companion service required.

**Not in V1:** CFS public warnings, warning polygons, paging/scanner feeds, incident history, or dedicated aircraft tracking.

Technical details: [docs/V1_SPEC.md](docs/V1_SPEC.md)

## Who is this for?

This integration may be useful if you:

- run Home Assistant in **South Australia**;
- want **current** CFS/MFS incidents as Home Assistant entities;
- prefer **distance and relevance filtering** over a statewide raw list;
- want incident data for **dashboards, notifications, templates, or automations**.

It is **not**:

- a paging or scanner feed;
- a replacement for **official CFS warnings** or emergency alerts;
- a **historical** incident archive;
- an aircraft or aviation enrichment service (those fields appear only when the upstream feed supplies them).

## Installation

A **GitHub Release** tag helps HACS custom-repository installs resolve the correct version. See [docs/RELEASE_CHECKLIST.md](docs/RELEASE_CHECKLIST.md) for maintainers.

### HACS custom repository

This integration is **not** in the default HACS catalogue. Add it as a custom repository:

1. Open **HACS** → **Integrations**.
2. Open the menu (⋮) → **Custom repositories**.
3. Repository URL: `https://github.com/Bobson854/homeassistant-sa-emergency`
4. Category: **Integration** → **Add**.
5. Find **SA Emergency** in HACS → **Download**.
6. Restart Home Assistant if prompted.
7. **Settings → Devices & services → Add integration → SA Emergency**.
8. Optional: **Configure** to adjust radii, refresh interval, and CFS/MFS inclusion.

### Manual installation

1. Copy `custom_components/sa_emergency/` to `<config>/custom_components/sa_emergency/`.
2. Restart Home Assistant.
3. Add the integration via **Settings → Devices & services → Add integration → SA Emergency**.

## Configuration

All setup is through the Home Assistant UI.

| Option | Default | Notes |
| --- | --- | --- |
| Local radius | 25 km | Incidents within this distance are **local** |
| Regional radius | 100 km | Beyond local, up to this distance is **regional** |
| Update interval | 180 s | Supported range **60–900** seconds |
| Include CFS | On | Filter after fetch; both agencies share one upstream request |
| Include MFS | On | At least one agency must remain enabled |

**Home location:** **Settings → System → General → Home location** must be set. The integration reads Home Assistant’s configured latitude and longitude **locally** only. It does not store home coordinates in the config entry or send them to the GeoHub incident feed.

## Entities

| Entity | What it shows |
| --- | --- |
| `sensor.sa_emergency_incidents` | Count of **relevant** incidents (local + regional); structured `incidents` attributes |
| `sensor.sa_emergency_local_incidents` | Count within the **local** radius |
| `sensor.sa_emergency_regional_incidents` | Count **regional** only (outside local, within regional radius) |
| `sensor.sa_emergency_nearest_incident` | Short label (type or location when available); full details in attributes |
| `sensor.sa_emergency_highest_relevance` | `none`, `regional`, or `local` |
| `sensor.sa_emergency_cfs_incidents` | Count of **relevant** CFS incidents |
| `sensor.sa_emergency_mfs_incidents` | Count of **relevant** MFS incidents |

Count sensors reflect **geographically relevant** incidents, not every incident statewide.

When more than **50** relevant incidents exist, the primary sensor state still shows the full count, but the `incidents` attribute list is capped at 50 (sorted) and `incidents_truncated` is `true`.

## Incident attributes

The primary Incidents sensor exposes a list of normalized incidents. Unavailable fields are **omitted** (not shown as zero or empty placeholders).

**Example only** — not live data:

```yaml
incidents:
  - incident_id: CFS:F2610030053
    agency: CFS
    type: Burn Off
    status: Controlled
    level: "1"
    location: KELLYS, ONKAPARINGA HILLS
    distance_km: 40.9
    bearing_degrees: 270
    bearing: W
    relevance: regional
    fire_ban_district: MOUNT LOFTY RANGES
    message: F-261003-0053 Onkaparinga Hills, Kellys Rd (Rubbish Or Waste)
    message_url: https://www.cfs.sa.gov.au/incidents
```

When present, public attributes can include: `incident_id`, `agency`, `type`, `status`, `level`, `first_reported`, `location`, `latitude`, `longitude`, `distance_km`, `bearing_degrees`, `bearing`, `relevance`, `region`, `fire_ban_district`, `resources`, `aircraft`, `message`, `message_url`.

## Relevance model

- **Local** — distance ≤ configured local radius (default 25 km).
- **Regional** — beyond local radius but ≤ regional radius (default 100 km).
- **Outside regional radius** — kept in internal totals where applicable but **not** counted as relevant on the main sensors.
- **No valid coordinates** — incident may still be ingested but cannot be geographically relevant.

## Source / data behaviour

SA Emergency currently uses the **public IMS incident feed** used by the [official CFS map](https://apps.geohub.sa.gov.au/CFSMap/index.html):

`https://cfs-feeds.geohub.sa.gov.au/FL/IMS_Read/SACFS_and_SAMFS_Incidents_and_Incident_Updates/FeatureServer/1/query`

- **One combined upstream feed** carries both CFS and MFS current incidents.
- **Agency** is determined from each record’s authority (Country Fire Service vs Metropolitan Fire Service).
- Data is **periodically refreshed** on your configured interval; availability depends on SA emergency-services systems.
- This feed is **not** a formally guaranteed public API contract — fields and availability may change.

No API credentials are required. Migration from older per-feed architecture is documented in [docs/V1_SPEC.md](docs/V1_SPEC.md).

## Troubleshooting

If sensors are **unavailable** or counts look wrong:

- Confirm Home Assistant has **internet access** and a configured **home location**.
- Open **Settings → Devices & services → SA Emergency → Download diagnostics** — check source status, counts, and last successful update (diagnostics do **not** include your home coordinates).
- Verify **Include CFS / Include MFS** and your **local/regional** radii — distant incidents do not appear in relevant counts.
- Remember upstream incident data can be **temporarily unavailable**; the integration will not silently pretend a failed refresh succeeded.

| Symptom | Things to check |
| --- | --- |
| Integration will not set up | Home location must be configured; initial refresh needs a working upstream feed |
| Zero relevant incidents | Incidents may be outside regional radius, or coordinates missing upstream |
| Stale `last_successful_update` | Network or upstream outage; check diagnostics source status |

Do **not** rely on Home Assistant for emergency decision-making.

## Limitations

- **Current incidents only** — no historical database in Home Assistant.
- **Warnings and map polygons** are not integrated in V1.
- **`resources`**, **`aircraft`**, and **`region`** may be absent when the current IMS feed does not supply mapped equivalents.
- Upstream **field shapes and availability** can change over time.
- **Early public testing** — usable in live setups, but not production-grade emergency reliability.

## Diagnostics

**Settings → Devices & services → SA Emergency → Download diagnostics**

Includes integration version, options, IMS source URL and status, aggregate incident counts, and last successful update. Does **not** include home coordinates or raw upstream payloads.

Issues: [GitHub Issues](https://github.com/Bobson854/homeassistant-sa-emergency/issues) — attach diagnostics when helpful.

## Development

Python 3.12+. See `pyproject.toml`.

```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -e ".[dev]"
ruff check custom_components tests
ruff format --check custom_components tests
pytest
```

CI runs lint, tests, Hassfest, and HACS validation.

## Disclaimer

SA Emergency is an independent Home Assistant integration and is **not** affiliated with or endorsed by the South Australian Country Fire Service, Metropolitan Fire Service, SAFECOM, or the Government of South Australia. **Do not rely on Home Assistant or this integration as your sole source of emergency warnings or safety information.** Always use official emergency-service channels.

## License

MIT — Copyright (c) Mark Jones. See [LICENSE](LICENSE).
