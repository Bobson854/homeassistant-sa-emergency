# SA Emergency

**V1 Preview / Initial Testing**

SA Emergency is a [Home Assistant](https://www.home-assistant.io/) custom integration that provides location-aware South Australian emergency **current incident** information from official public CFS and MFS feeds.

This release is suitable for **initial trial installation** through HACS custom repository or manual install. It is an independent community project and must not be treated as an official emergency-warning system.

Current version: `0.6.0`

## What it does

- Polls official **CFS** and **MFS** current incident feeds
- Normalizes incidents into a common internal model
- Calculates distance, bearing, and local/regional relevance from your configured **Home Assistant location**
- Exposes seven stable V1 sensors and structured incident attributes for dashboards and automations
- Tolerates partial source failure when multiple agencies are enabled

**Not included in V1:** CFS public warnings, warning polygons, aviation enrichment, notifications, or incident history.

See [docs/V1_SPEC.md](docs/V1_SPEC.md) for the full specification.

## Data sources

This integration consumes public government data only. It is **not affiliated with, sponsored by, or endorsed by** CFS, MFS, SAFECOM, the South Australian Government, or Home Assistant.

| Agency | Authoritative source |
| --- | --- |
| CFS current incidents | `https://data.eso.sa.gov.au/prod/cfs/criimson/cfs_current_incidents.json` |
| MFS current incidents | `https://cfs.geohub.sa.gov.au/server/rest/services/CFS_Incident_Read/MFS_Incidents/FeatureServer/0/query` |

No API credentials are required.

## Entities

| Entity | Description |
| --- | --- |
| `sensor.sa_emergency_incidents` | Count of relevant incidents with structured `incidents` attributes |
| `sensor.sa_emergency_local_incidents` | Count of local incidents |
| `sensor.sa_emergency_regional_incidents` | Count of regional incidents (excluding local) |
| `sensor.sa_emergency_nearest_incident` | Nearest relevant incident |
| `sensor.sa_emergency_highest_relevance` | Highest current relevance (`none`, `regional`, `local`) |
| `sensor.sa_emergency_cfs_incidents` | Count of relevant CFS incidents |
| `sensor.sa_emergency_mfs_incidents` | Count of relevant MFS incidents |

### Relevance defaults

| Setting | Default |
| --- | --- |
| Local radius | 25 km |
| Regional radius | 100 km |
| Polling interval | 180 seconds |
| Include CFS | enabled |
| Include MFS | enabled |

Configure these via **Settings → Devices & services → SA Emergency → Configure**.

### Example `incidents` attribute

```yaml
incidents:
  - incident_id: "CFS:123456"
    agency: "CFS"
    type: "Grass Fire"
    status: "GOING"
    location: "MONARTO, OLD PRINCES HIGHWAY"
    distance_km: 81.2
    bearing_degrees: 94
    bearing: "E"
    relevance: "regional"
    first_reported: "2026-08-30T14:30:00+09:30"
incidents_exposed: 1
incidents_truncated: false
```

The primary sensor state always reflects the **full** relevant count. When more than 50 relevant incidents exist, the `incidents` attribute list is capped at 50 sorted incidents and `incidents_truncated` is set to `true`.

## Installation

A **GitHub Release** is required for reliable HACS custom-repository installation. See [docs/RELEASE_CHECKLIST.md](docs/RELEASE_CHECKLIST.md) for the maintainer release process.

### HACS custom repository

1. Open **HACS**.
2. Open the **Integrations** section menu (top right) and choose **Custom repositories**.
3. Add repository URL: `https://github.com/Bobson854/homeassistant-sa-emergency`
4. Category: **Integration**.
5. Install **SA Emergency**.
6. Restart Home Assistant if prompted.
7. Go to **Settings → Devices & services → Add integration → SA Emergency**.
8. Open **Configure** on the integration to adjust radii, polling interval, and agency toggles.

### Manual installation

1. Copy the folder `custom_components/sa_emergency/` to `<Home Assistant config>/custom_components/sa_emergency/`.
2. Restart Home Assistant.
3. Add the integration via **Settings → Devices & services → Add integration → SA Emergency**.

## Initial setup

1. Ensure Home Assistant has a configured map location (**Settings → System → General → Home location**).
2. Add the SA Emergency integration through the UI.
3. Optionally open **Configure** to adjust local/regional radii, polling interval, or disable an agency feed.

The integration reads `hass.config.latitude` and `hass.config.longitude` locally. It does **not** ask for separate coordinates and does **not** store home coordinates in the config entry.

## Source degradation behaviour

- If **both enabled sources fail**, the coordinator update fails.
- If **one enabled source fails**, data from the other enabled source is retained.
- A **deliberately disabled** source is reported as `disabled`, not as degraded availability.
- Agency count sensors distinguish **source error** (unknown state) from a successful zero-incident result (`0`).

## Data freshness

Incident data is refreshed on the configured polling interval (default 180 seconds). `last_successful_update` on the primary Incidents sensor reflects the latest coordinator refresh where at least one enabled source succeeded.

## Privacy

- Home Assistant's configured latitude and longitude are used **locally** to calculate distance and relevance.
- Home coordinates are **not** sent to CFS or MFS endpoints.
- Home coordinates are **not** stored in integration config entry data.
- Home coordinates are **not** exposed in diagnostics downloads.
- Public incident coordinates come from official public government feeds.

## Diagnostics

Download diagnostics from **Settings → Devices & services → SA Emergency → Download diagnostics**.

Diagnostics include integration version, resolved options, source health, aggregate incident counts, and source URLs. They do **not** include your Home Assistant home coordinates or raw source API payloads.

When reporting issues, attach diagnostics if helpful. Do **not** publish your home coordinates.

## Troubleshooting

| Symptom | Things to check |
| --- | --- |
| Integration will not set up | Home Assistant home location (latitude/longitude) must be configured |
| No incidents shown | Incidents may be outside your regional radius; increase radii in **Configure** |
| CFS/MFS sensor unknown | That agency source may be temporarily unavailable; check `source_status` on the primary Incidents sensor |
| One agency always zero | Confirm the agency is enabled in **Configure** and that incidents are geographically relevant |
| Stale data | Check polling interval and whether an enabled source is in `error` state |
| Agency sensor missing counts but integration works | Relevant count sensors report geographically relevant incidents, not all statewide incidents |

## Issue reporting

Report bugs at: [https://github.com/Bobson854/homeassistant-sa-emergency/issues](https://github.com/Bobson854/homeassistant-sa-emergency/issues)

Include Home Assistant diagnostics where helpful.

## Development

Requirements: Python 3.12+, dependencies from `pyproject.toml`.

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
ruff check custom_components tests
ruff format --check custom_components tests
pytest
```

CI also runs Hassfest and HACS validation via GitHub Actions.

## Disclaimer

SA Emergency is an **independent community integration**. It is **not** affiliated with or endorsed by the South Australian Country Fire Service (CFS), Metropolitan Fire Service (MFS), SAFECOM, the South Australian Government, or Home Assistant.

**Do not rely on this integration as the sole source of emergency warnings or safety information.** Always follow official emergency-service warnings and instructions.

## License

MIT — see [LICENSE](LICENSE).
