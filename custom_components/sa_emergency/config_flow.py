"""Config flow for the SA Emergency integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import (
    CONF_INCLUDE_CFS,
    CONF_INCLUDE_MFS,
    CONF_LOCAL_RADIUS_KM,
    CONF_REGIONAL_RADIUS_KM,
    DOMAIN,
    MAX_LOCAL_RADIUS_KM,
    MAX_REGIONAL_RADIUS_KM,
    MAX_SCAN_INTERVAL_SECONDS,
    MIN_LOCAL_RADIUS_KM,
    MIN_REGIONAL_RADIUS_KM,
    MIN_SCAN_INTERVAL_SECONDS,
    NAME,
)
from .options import options_schema_defaults, validate_options_input

try:
    from homeassistant.config_entries import OptionsFlowWithReload as _OptionsFlowBase
except ImportError:  # pragma: no cover - older Home Assistant cores
    _OptionsFlowBase = None


if _OptionsFlowBase is not None:

    class _SaEmergencyOptionsFlowBase(_OptionsFlowBase):
        """Options flow base with native reload support."""

else:

    class _SaEmergencyOptionsFlowBase(config_entries.OptionsFlow):
        """Options flow base with explicit reload scheduling."""

        @callback
        def async_create_entry(
            self,
            *,
            title: str | None = None,
            data: dict[str, Any] | None = None,
        ) -> config_entries.ConfigFlowResult:
            """Create an options entry and reload the integration once."""
            result = super().async_create_entry(title=title or "", data=data)
            self.hass.config_entries.async_schedule_reload(self.config_entry.entry_id)
            return result


class SaEmergencyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SA Emergency."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial setup step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            await self.async_set_unique_id(DOMAIN)
            self._abort_if_unique_id_configured()

            return self.async_create_entry(title=NAME, data={})

        if self.hass.config.latitude is None or self.hass.config.longitude is None:
            errors["base"] = "location_not_configured"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({}),
            errors=errors,
            description_placeholders={
                "latitude": str(self.hass.config.latitude),
                "longitude": str(self.hass.config.longitude),
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> SaEmergencyOptionsFlowHandler:
        """Return the options flow handler."""
        return SaEmergencyOptionsFlowHandler()


class SaEmergencyOptionsFlowHandler(_SaEmergencyOptionsFlowBase):
    """Handle SA Emergency integration options."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the integration options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            errors = validate_options_input(user_input)
            if not errors:
                return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=_options_schema(self.config_entry),
            errors=errors,
        )


def _options_schema(config_entry: config_entries.ConfigEntry) -> vol.Schema:
    """Return the Options Flow schema with current values as defaults."""
    defaults = options_schema_defaults(config_entry)
    return vol.Schema(
        {
            vol.Required(
                CONF_LOCAL_RADIUS_KM, default=defaults[CONF_LOCAL_RADIUS_KM]
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=MIN_LOCAL_RADIUS_KM,
                    max=MAX_LOCAL_RADIUS_KM,
                    step=1,
                    unit_of_measurement="km",
                    mode=selector.NumberSelectorMode.BOX,
                ),
            ),
            vol.Required(
                CONF_REGIONAL_RADIUS_KM, default=defaults[CONF_REGIONAL_RADIUS_KM]
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=MIN_REGIONAL_RADIUS_KM,
                    max=MAX_REGIONAL_RADIUS_KM,
                    step=1,
                    unit_of_measurement="km",
                    mode=selector.NumberSelectorMode.BOX,
                ),
            ),
            vol.Required(
                CONF_SCAN_INTERVAL, default=defaults[CONF_SCAN_INTERVAL]
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=MIN_SCAN_INTERVAL_SECONDS,
                    max=MAX_SCAN_INTERVAL_SECONDS,
                    step=30,
                    unit_of_measurement="s",
                    mode=selector.NumberSelectorMode.BOX,
                ),
            ),
            vol.Required(
                CONF_INCLUDE_CFS, default=defaults[CONF_INCLUDE_CFS]
            ): selector.BooleanSelector(),
            vol.Required(
                CONF_INCLUDE_MFS, default=defaults[CONF_INCLUDE_MFS]
            ): selector.BooleanSelector(),
        }
    )
