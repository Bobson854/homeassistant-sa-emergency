"""Tests for the SA Emergency options flow."""

from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.sa_emergency.config_flow import _options_schema
from custom_components.sa_emergency.const import (
    CONF_INCLUDE_CFS,
    CONF_INCLUDE_MFS,
    CONF_LOCAL_RADIUS_KM,
    CONF_REGIONAL_RADIUS_KM,
    DEFAULT_LOCAL_RADIUS_KM,
    DEFAULT_REGIONAL_RADIUS_KM,
    DEFAULT_UPDATE_INTERVAL_SECONDS,
    DOMAIN,
    MAX_LOCAL_RADIUS_KM,
)
from custom_components.sa_emergency.options import (
    get_integration_options,
    options_schema_defaults,
    validate_options_input,
)


def _configured_entry(**options) -> MockConfigEntry:
    entry = MockConfigEntry(domain=DOMAIN, data={}, unique_id=DOMAIN, options=options)
    return entry


async def test_options_flow_defaults(hass) -> None:
    """Test options flow opens with default values for a new entry."""
    entry = _configured_entry()
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    defaults = options_schema_defaults(entry)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"
    assert defaults[CONF_LOCAL_RADIUS_KM] == DEFAULT_LOCAL_RADIUS_KM
    assert defaults[CONF_REGIONAL_RADIUS_KM] == DEFAULT_REGIONAL_RADIUS_KM
    assert defaults[CONF_SCAN_INTERVAL] == DEFAULT_UPDATE_INTERVAL_SECONDS
    assert _options_schema(entry) is not None


async def test_options_flow_valid_save(hass) -> None:
    """Test valid options are saved."""
    entry = _configured_entry()
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_LOCAL_RADIUS_KM: 30,
            CONF_REGIONAL_RADIUS_KM: 120,
            CONF_SCAN_INTERVAL: 240,
            CONF_INCLUDE_CFS: True,
            CONF_INCLUDE_MFS: False,
        },
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options[CONF_LOCAL_RADIUS_KM] == 30
    assert entry.options[CONF_INCLUDE_MFS] is False


async def test_options_flow_shows_current_values(hass) -> None:
    """Test reopening options shows previously saved values."""
    entry = _configured_entry(
        **{
            CONF_LOCAL_RADIUS_KM: 40,
            CONF_REGIONAL_RADIUS_KM: 150,
            CONF_SCAN_INTERVAL: 300,
            CONF_INCLUDE_CFS: False,
            CONF_INCLUDE_MFS: True,
        }
    )
    entry.add_to_hass(hass)

    defaults = options_schema_defaults(entry)
    assert defaults[CONF_LOCAL_RADIUS_KM] == 40
    assert defaults[CONF_INCLUDE_CFS] is False


async def test_options_flow_invalid_local_radius(hass) -> None:
    """Test unsupported local radius values are rejected."""
    errors = validate_options_input(
        {
            CONF_LOCAL_RADIUS_KM: MAX_LOCAL_RADIUS_KM + 1,
            CONF_REGIONAL_RADIUS_KM: DEFAULT_REGIONAL_RADIUS_KM,
            CONF_SCAN_INTERVAL: DEFAULT_UPDATE_INTERVAL_SECONDS,
            CONF_INCLUDE_CFS: True,
            CONF_INCLUDE_MFS: True,
        }
    )
    assert errors[CONF_LOCAL_RADIUS_KM] == "invalid_local_radius"


async def test_options_flow_regional_not_greater_than_local(hass) -> None:
    """Test regional radius must exceed local radius."""
    entry = _configured_entry()
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_LOCAL_RADIUS_KM: 100,
            CONF_REGIONAL_RADIUS_KM: 100,
            CONF_SCAN_INTERVAL: DEFAULT_UPDATE_INTERVAL_SECONDS,
            CONF_INCLUDE_CFS: True,
            CONF_INCLUDE_MFS: True,
        },
    )

    assert (
        result["errors"][CONF_REGIONAL_RADIUS_KM] == "regional_not_greater_than_local"
    )


async def test_options_flow_invalid_poll_interval(hass) -> None:
    """Test polling interval bounds are enforced by validation."""
    errors = validate_options_input(
        {
            CONF_LOCAL_RADIUS_KM: DEFAULT_LOCAL_RADIUS_KM,
            CONF_REGIONAL_RADIUS_KM: DEFAULT_REGIONAL_RADIUS_KM,
            CONF_SCAN_INTERVAL: 30,
            CONF_INCLUDE_CFS: True,
            CONF_INCLUDE_MFS: True,
        }
    )
    assert errors[CONF_SCAN_INTERVAL] == "invalid_poll_interval"


def test_validate_options_input_rejects_zero_local_radius() -> None:
    """Test zero local radius is rejected by validation helper."""
    errors = validate_options_input(
        {
            CONF_LOCAL_RADIUS_KM: 0,
            CONF_REGIONAL_RADIUS_KM: DEFAULT_REGIONAL_RADIUS_KM,
            CONF_SCAN_INTERVAL: DEFAULT_UPDATE_INTERVAL_SECONDS,
            CONF_INCLUDE_CFS: True,
            CONF_INCLUDE_MFS: True,
        }
    )
    assert errors[CONF_LOCAL_RADIUS_KM] == "invalid_local_radius"


async def test_options_flow_no_agencies_enabled(hass) -> None:
    """Test at least one agency must remain enabled."""
    entry = _configured_entry()
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_LOCAL_RADIUS_KM: DEFAULT_LOCAL_RADIUS_KM,
            CONF_REGIONAL_RADIUS_KM: DEFAULT_REGIONAL_RADIUS_KM,
            CONF_SCAN_INTERVAL: DEFAULT_UPDATE_INTERVAL_SECONDS,
            CONF_INCLUDE_CFS: False,
            CONF_INCLUDE_MFS: False,
        },
    )

    assert result["errors"]["base"] == "no_agencies_enabled"


def test_existing_entry_uses_defaults_without_options(hass) -> None:
    """Test legacy entries without options continue using defaults."""
    entry = MockConfigEntry(domain=DOMAIN, data={}, unique_id=DOMAIN)
    entry.add_to_hass(hass)

    options = get_integration_options(entry)
    assert options.local_radius_km == DEFAULT_LOCAL_RADIUS_KM
    assert options.include_cfs is True
    assert options.include_mfs is True
