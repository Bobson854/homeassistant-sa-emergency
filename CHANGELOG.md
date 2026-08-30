# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.6.0] - Unreleased

### Added

- Config-entry diagnostics for troubleshooting without exposing Home Assistant home coordinates.
- HACS and Hassfest CI validation workflows.
- Release checklist and V1 preview documentation for trial installation.
- Australia (`AU`) country metadata in `hacs.json` for geographically scoped discovery.

### Changed

- README updated for V1 preview / initial testing through HACS custom repository installation.
- Localization consolidated into `translations/en.json` for custom-integration compliance.
- Integration version bumped to `0.6.0` for release hardening.

## [0.5.0]

### Added

- Options Flow for local/regional radius, polling interval, and CFS/MFS source toggles.
- Stable V1 sensor suite: Incidents, Local, Regional, Nearest, Highest Relevance, CFS, and MFS sensors.
- Structured public incident attributes on the primary Incidents sensor with a 50-item exposure cap.
- Relevant agency helpers (`cfs_relevant_incidents`, `mfs_relevant_incidents`).

### Changed

- Removed temporary development status sensor in favour of the stable entity contract.

## [0.4.0]

### Added

- Great-circle distance, bearing, and eight-point compass direction from Home Assistant home location.
- Local, regional, and none relevance classification with configurable default radii.
- Coordinator collections for all, relevant, local, and regional incidents, plus nearest incident and highest relevance.

## [0.3.0]

### Added

- Official MFS ArcGIS current incident ingestion.
- Multi-source coordinator with per-source status and partial failure tolerance.
- Merged CFS + MFS normalized incident runtime state.

## [0.2.0]

### Added

- Official CFS current incident JSON ingestion and normalization.
- Shared `Incident` model and initial coordinator runtime data.

## [0.1.0]

### Added

- Initial Home Assistant integration scaffold, config flow, coordinator skeleton, and test/CI foundation.

[0.6.0]: https://github.com/Bobson854/homeassistant-sa-emergency/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/Bobson854/homeassistant-sa-emergency/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/Bobson854/homeassistant-sa-emergency/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/Bobson854/homeassistant-sa-emergency/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/Bobson854/homeassistant-sa-emergency/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/Bobson854/homeassistant-sa-emergency/releases/tag/v0.1.0
