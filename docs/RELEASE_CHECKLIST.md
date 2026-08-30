# Release checklist

Use this checklist before tagging a release of SA Emergency.

## Automated validation

- [ ] `ruff check custom_components tests`
- [ ] `ruff format --check custom_components tests`
- [ ] `pytest -q`
- [ ] GitHub Actions **Lint and test** workflow passes
- [ ] GitHub Actions **Validate** workflow passes (Hassfest + HACS)

## Manual Home Assistant validation

- [ ] Manual install from `custom_components/sa_emergency/` succeeds
- [ ] Config Flow completes using Home Assistant configured location
- [ ] Options Flow saves and reloads radii, polling interval, and agency toggles
- [ ] All seven V1 sensors appear under the SA Emergency device
- [ ] Primary Incidents sensor exposes structured `incidents` attributes
- [ ] CFS live source returns normalized incidents
- [ ] MFS live source returns normalized incidents
- [ ] Partial source failure retains data from the successful enabled source
- [ ] Disabled agency sensors remain present with `disabled` source status
- [ ] Diagnostics download succeeds and contains no home latitude/longitude

## Privacy and documentation

- [ ] Diagnostics contain aggregated counts only, not raw source payloads
- [ ] README disclaimer and privacy sections are current
- [ ] `CHANGELOG.md` updated for the release version
- [ ] Version synchronized in `manifest.json` and `pyproject.toml`

## GitHub repository metadata

- [ ] Repository description set to: `Home Assistant integration for location-aware South Australian CFS and MFS incident information.`
- [ ] Issues enabled
- [ ] Topics include: `home-assistant`, `homeassistant`, `hacs`, `south-australia`, `cfs`, `mfs`, `emergency-services`

## Release steps

1. Ensure `main` is green in GitHub Actions.
2. Commit and push release-prep changes.
3. Create and push an annotated tag, for example:
   ```bash
   git tag -a v0.6.0 -m "SA Emergency 0.6.0"
   git push origin v0.6.0
   ```
4. Create a **GitHub Release** from the tag (required for reliable HACS custom-repository installs).
5. Install through HACS custom repository and repeat the manual validation steps above.

## HACS custom repository trial

- [ ] Add `https://github.com/Bobson854/homeassistant-sa-emergency` as a HACS custom repository (Integration)
- [ ] Install **SA Emergency** from HACS
- [ ] Restart Home Assistant if prompted
- [ ] Complete UI setup and options configuration

## Default HACS catalogue (future, not required for first trial)

- [ ] Passing HACS action without ignores
- [ ] Passing Hassfest
- [ ] Real GitHub Release published
- [ ] Repository description and topics configured
- [ ] Brand assets registered in the [Home Assistant Brands](https://github.com/home-assistant/brands) repository
- [ ] Submit inclusion PR to `hacs/default` from an editable personal fork

## Post-release

- [ ] Monitor GitHub Issues for installation or source-degradation reports
- [ ] Capture any live-source quirks discovered during trial use
