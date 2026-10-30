"""Config flow for AI DJ integration."""
from __future__ import annotations

import logging
from typing import Any, override

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from collections.abc import Mapping

from homeassistant.core import HomeAssistant, callback
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .backend.const import (
    DOMAIN,
    CONF_PROVIDER,
    CONF_GEMINI_API_KEY,
    CONF_GEMINI_MODEL,
    DEFAULT_GEMINI_MODEL,
    CONF_OLLAMA_URL,
    CONF_OLLAMA_MODEL,
    PROVIDER_GEMINI,
    PROVIDER_OLLAMA,
    DEFAULT_OLLAMA_URL,
    DEFAULT_OLLAMA_MODEL,
)

_LOGGER = logging.getLogger(__name__)

async def validate_gemini(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, str]:
    """Validate the Gemini API key and model via REST API."""
    gemini_key = data[CONF_GEMINI_API_KEY]
    model = data[CONF_GEMINI_MODEL]
    session = async_get_clientsession(hass)
    gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}?key={gemini_key}"
    
    try:
        async with session.get(gemini_url) as response:
            if response.status == 404:
                _LOGGER.error("Gemini model '%s' not found", model)
                raise InvalidModel
            if response.status != 200:
                error_data = await response.text()
                _LOGGER.error("Gemini API rejected key: %s", error_data)
                raise InvalidAuth
    except (InvalidAuth, InvalidModel):
        raise
    except Exception as err:
        _LOGGER.error("Gemini connection failed: %s", err)
        raise CannotConnect from err

    return {"title": "AI DJ (Gemini)"}

async def validate_ollama(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, str]:
    """Validate the Ollama URL and verify the model is downloaded."""
    url = data[CONF_OLLAMA_URL].rstrip("/")
    model = data[CONF_OLLAMA_MODEL]
    session = async_get_clientsession(hass)
    tags_url = f"{url}/api/tags"
    
    try:
        async with session.get(tags_url, timeout=aiohttp.ClientTimeout(total=10)) as response:
            if response.status != 200:
                raise CannotConnect
            
            result = await response.json()
            models = [m.get("name") for m in result.get("models", [])]
            
            # Ollama often appends ':latest' to model names if not specified
            if model not in models and f"{model}:latest" not in models:
                _LOGGER.error("Ollama model '%s' not found. Available: %s", model, models)
                raise InvalidModel
                
    except InvalidModel:
        raise
    except Exception as err:
        _LOGGER.error("Ollama connection failed: %s", err)
        raise CannotConnect from err

    return {"title": f"AI DJ ({model})"}


def _current_config(entry: config_entries.ConfigEntry) -> dict[str, Any]:
    """Entry data with the options (set through Configure) applied on top."""
    return {**entry.data, **entry.options}


def _gemini_schema(defaults: Mapping[str, Any], with_key: bool = True) -> vol.Schema:
    fields: dict[Any, Any] = {}
    if with_key:
        fields[vol.Required(CONF_GEMINI_API_KEY, default=defaults.get(CONF_GEMINI_API_KEY, vol.UNDEFINED))] = str
    fields[vol.Required(CONF_GEMINI_MODEL, default=defaults.get(CONF_GEMINI_MODEL, DEFAULT_GEMINI_MODEL))] = str
    return vol.Schema(fields)


def _ollama_schema(defaults: Mapping[str, Any]) -> vol.Schema:
    return vol.Schema({
        vol.Required(CONF_OLLAMA_URL, default=defaults.get(CONF_OLLAMA_URL, DEFAULT_OLLAMA_URL)): str,
        vol.Required(CONF_OLLAMA_MODEL, default=defaults.get(CONF_OLLAMA_MODEL, DEFAULT_OLLAMA_MODEL)): str,
    })


async def _validate(hass: HomeAssistant, provider: str, data: dict[str, Any]) -> tuple[dict[str, str], dict[str, str]]:
    """Validate provider settings, return (info, errors)."""
    try:
        if provider == PROVIDER_GEMINI:
            return await validate_gemini(hass, data), {}
        return await validate_ollama(hass, data), {}
    except CannotConnect:
        return {}, {"base": "cannot_connect"}
    except InvalidAuth:
        return {}, {"base": "invalid_auth"}
    except InvalidModel:
        return {}, {"base": "invalid_model"}
    except Exception:
        _LOGGER.exception("Unexpected exception")
        return {}, {"base": "unknown"}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for AI DJ.

    Only one entry is allowed (manifest: single_config_entry), every entry runs its own
    DJ engine over all parties. Switching between Gemini and Ollama goes through Reconfigure.
    """

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> OptionsFlowHandler:
        """Return the options flow to change the model of the current provider."""
        return OptionsFlowHandler()

    def __init__(self) -> None:
        """Initialize the config flow state."""
        self.provider: str | None = None

    def _defaults(self, provider: str) -> Mapping[str, Any]:
        """Prefill forms with the current settings when reconfiguring the same provider."""
        if self.source != config_entries.SOURCE_RECONFIGURE:
            return {}
        current = _current_config(self._get_reconfigure_entry())
        return current if current.get(CONF_PROVIDER, PROVIDER_GEMINI) == provider else {}

    async def _async_finish(self, title: str, user_input: dict[str, Any]) -> ConfigFlowResult:
        data = {CONF_PROVIDER: self.provider, **user_input}
        if self.source == config_entries.SOURCE_RECONFIGURE:
            # Options belong to the previous settings, start clean
            return self.async_update_reload_and_abort(
                self._get_reconfigure_entry(), title=title, data=data, options={}
            )
        return self.async_create_entry(title=title, data=data)

    @override
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 1: Ask the user to select their AI Provider."""
        if user_input is not None:
            self.provider = user_input[CONF_PROVIDER]
            if self.provider == PROVIDER_GEMINI:
                return await self.async_step_gemini()
            return await self.async_step_ollama()

        default = PROVIDER_GEMINI
        if self.source == config_entries.SOURCE_RECONFIGURE:
            default = self._get_reconfigure_entry().data.get(CONF_PROVIDER, PROVIDER_GEMINI)
        schema = vol.Schema({
            vol.Required(CONF_PROVIDER, default=default): vol.In([PROVIDER_GEMINI, PROVIDER_OLLAMA])
        })
        return self.async_show_form(step_id="user", data_schema=schema)

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Reconfigure: same steps as the initial setup, then update the existing entry."""
        return await self.async_step_user(user_input)

    async def async_step_gemini(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 2A: Collect and validate Gemini credentials."""
        errors: dict[str, str] = {}
        if user_input is not None:
            info, errors = await _validate(self.hass, PROVIDER_GEMINI, user_input)
            if not errors:
                return await self._async_finish(info["title"], user_input)

        return self.async_show_form(
            step_id="gemini",
            data_schema=_gemini_schema(user_input or self._defaults(PROVIDER_GEMINI)),
            errors=errors,
        )

    async def async_step_ollama(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 2B: Collect and validate Ollama credentials."""
        errors: dict[str, str] = {}
        if user_input is not None:
            info, errors = await _validate(self.hass, PROVIDER_OLLAMA, user_input)
            if not errors:
                return await self._async_finish(info["title"], user_input)

        return self.async_show_form(
            step_id="ollama",
            data_schema=_ollama_schema(user_input or self._defaults(PROVIDER_OLLAMA)),
            errors=errors,
        )


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Change the model (and for Ollama the server) of the current provider."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        current = _current_config(self.config_entry)
        provider = current.get(CONF_PROVIDER, PROVIDER_GEMINI)

        errors: dict[str, str] = {}
        if user_input is not None:
            _, errors = await _validate(self.hass, provider, {**current, **user_input})
            if not errors:
                return self.async_create_entry(data=user_input)

        defaults = {**current, **(user_input or {})}
        schema = (
            _gemini_schema(defaults, with_key=False)
            if provider == PROVIDER_GEMINI
            else _ollama_schema(defaults)
        )
        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""

class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""

class InvalidModel(HomeAssistantError):
    """Error to indicate the requested model is not available."""