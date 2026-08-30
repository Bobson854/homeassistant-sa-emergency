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

Milestone 2 — **CFS incident ingestion implemented**.

The integration polls the official CFS current incidents JSON feed, normalizes records into an internal `Incident` model, and exposes a temporary development sensor (`sensor.sa_emergency_status`) showing the normalized CFS incident count and source health.

**Not yet implemented:** MFS ingestion, distance/bearing calculations, local/regional relevance, Options Flow, and the final stable V1 sensor suite. Current sensor(s) are development interfaces and may change before V1.

Current version: `0.2.0`

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
| CFS incidents | `https://data.eso.sa.gov.au/prod/cfs/criimson/cfs_current_incidents.json` | Implemented (Milestone 2) |
| MFS incidents | `https://cfs.geohub.sa.gov.au/server/rest/services/CFS_Incident_Read/MFS_Incidents/FeatureServer/0/query` | Planned |

These are public endpoints and do not require API credentials for V1.

## Privacy

The integration uses your Home Assistant configured latitude and longitude as the reference location for distance and relevance calculations. No coordinates are sent to third parties beyond requests required to retrieve public government incident feeds (once implemented).

## Disclaimer

This integration is an **independent community project**. It is **not** affiliated with or endorsed by the South Australian Country Fire Service (CFS), Metropolitan Fire Service (MFS), SAFECOM, the South Australian Government, or Home Assistant.

**It must not be relied upon as the sole source of emergency warnings or information affecting personal safety.** Always use official emergency-service channels and advice.

## License

MIT — see [LICENSE](LICENSE).
