"""Config flow for the SA Emergency integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .const import DOMAIN, NAME


class SaEmergencyConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SA Emergency."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
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
