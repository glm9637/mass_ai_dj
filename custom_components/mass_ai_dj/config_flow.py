"""Config flow for AI DJ integration."""
from __future__ import annotations

import logging
import json
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession


from .const import DOMAIN, CONF_GEMINI_API_KEY

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_GEMINI_API_KEY): str,
    }
)

async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""
    
    # 1. Validate Gemini via REST API
    gemini_key = data[CONF_GEMINI_API_KEY]
    session = async_get_clientsession(hass)
    gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={gemini_key}"
    
    try:
        async with session.get(gemini_url) as response:
            if response.status != 200:
                error_data = await response.text()
                _LOGGER.error("Gemini API rejected key: %s", error_data)
                raise InvalidGeminiKey
    except Exception as err:
        _LOGGER.error("Gemini Connection failed: %s", err)
        raise InvalidGeminiKey from err


    return {"title": "AI DJ"}

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for AI DJ."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            await self.async_set_unique_id("ai_dj_integration")
            self._abort_if_unique_id_configured()

            try:
                info = await validate_input(self.hass, user_input)
            except InvalidGeminiKey:
                errors["base"] = "invalid_gemini_key"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

class InvalidGeminiKey(HomeAssistantError):
    """Error to indicate there is an invalid Gemini API key."""