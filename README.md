# SA Emergency

**Early Development / Not Yet Ready for Operational Use**

SA Emergency is an in-development [Home Assistant](https://www.home-assistant.io/) custom integration intended to provide location-aware South Australian emergency incident information.

Planned authoritative sources include:

- CFS current incidents
- MFS current incidents
- CFS public warnings (post-V1)

## Intended architecture

- Authoritative government sources remain the source of truth
- No separate incident-history database is required
- Incidents will be normalized into a common model
- Relevance will be calculated from the configured Home Assistant location
- Home Assistant sensors and attributes will expose the data
- Dashboards and automations can consume those entities independently

## Status

Milestone 5 — **V1 sensors and configurable options implemented**.

The integration polls official CFS and MFS incident feeds, normalizes them into a shared model, and calculates distance, bearing, and local/regional relevance from your configured Home Assistant location. Options allow you to configure local and regional radii, polling interval, and whether each agency feed is enabled. Partial source failure is tolerated when multiple sources are enabled.

**Not yet implemented:** CFS public warnings, warning polygons, aviation/context enrichment, or a tagged public release. See Milestone 6 for release-quality validation.

Current version: `0.5.0`

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

Configure radii, polling interval, and agency toggles via **Settings → Devices & services → SA Emergency → Configure**.

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

The primary sensor state always reflects the full relevant count. When more than 50 relevant incidents exist, the `incidents` attribute list is capped at 50 sorted incidents and `incidents_truncated` is set to `true`.

## Planned features

- Poll official CFS and MFS incident feeds
- Normalize incidents into a common model
- Calculate distance and bearing from the Home Assistant location
- Classify incidents as local, regional, or non-relevant
- Expose stable sensors (not dynamic per-incident entities)
- Options for local/regional radius, polling interval, and agency toggles
- HACS distribution and eventual default-repository submission

See [docs/V1_SPEC.md](docs/V1_SPEC.md) for the full V1 specification.

## Installation

This repository is not yet published for HACS default installation. A GitHub release is required before HACS custom-repository installation will work reliably.

### Manual installation (development)

1. Copy `custom_components/sa_emergency/` into your Home Assistant `config/custom_components/` directory.
2. Restart Home Assistant.
3. Add the integration via **Settings → Devices & services → Add integration → SA Emergency**.

### HACS (planned)

After the first tagged release:

1. Add `https://github.com/Bobson854/homeassistant-sa-emergency` as a custom HACS repository (category: Integration).
2. Install **SA Emergency** from HACS.
3. Restart Home Assistant and complete the UI setup.

## Development

Requirements:

- Python 3.12+
- Development dependencies from `pyproject.toml`

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
ruff check .
ruff format --check .
pytest
```

Validation (when Home Assistant core checkout or hassfest is available):

```bash
python -m script.hassfest --action validate --integration-path custom_components/sa_emergency
```

## Data sources

| Agency | Source | Status |
| --- | --- | --- |
| CFS incidents | `https://data.eso.sa.gov.au/prod/cfs/criimson/cfs_current_incidents.json` | Implemented |
| MFS incidents | `https://cfs.geohub.sa.gov.au/server/rest/services/CFS_Incident_Read/MFS_Incidents/FeatureServer/0/query` | Implemented |

These are public endpoints and do not require API credentials for V1.

## Privacy

The integration uses your Home Assistant configured latitude and longitude as the reference location for distance and relevance calculations. No coordinates are sent to third parties beyond requests required to retrieve public government incident feeds (once implemented).

## Disclaimer

This integration is an **independent community project**. It is **not** affiliated with or endorsed by the South Australian Country Fire Service (CFS), Metropolitan Fire Service (MFS), SAFECOM, the South Australian Government, or Home Assistant.

**It must not be relied upon as the sole source of emergency warnings or information affecting personal safety.** Always use official emergency-service channels and advice.

## License

MIT — see [LICENSE](LICENSE).
