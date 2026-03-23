"""The AI DJ integration."""
from __future__ import annotations

import logging
import os

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.components import panel_custom
from homeassistant.components.http import StaticPathConfig

from .const import DOMAIN, CONF_GEMINI_API_KEY

_LOGGER = logging.getLogger(__name__)

# For now we won't load any platforms, that will happen in User Story 2.
PLATFORMS: list[str] = []

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up AI DJ from a config entry."""
    
    hass.data.setdefault(DOMAIN, {})

    # Extract credentials
    gemini_key = entry.data[CONF_GEMINI_API_KEY]

    try:
        def init_services():
            return {"gemini_key": gemini_key}
        
        services = await hass.async_add_executor_job(init_services)
        hass.data[DOMAIN][entry.entry_id] = services
        
        if "store" not in hass.data[DOMAIN]:
            from .store import PartyStore
            store = PartyStore(hass)
            await store.async_load()
            hass.data[DOMAIN]["store"] = store
            
            from .websocket_api import async_setup_websocket_api
            async_setup_websocket_api(hass)
            
            from .dj_engine import DJEngine
            engine = DJEngine(hass)
            hass.data[DOMAIN]["engine"] = engine
            engine.start()
            
            frontend_path = hass.config.path("custom_components/mass_ai_dj/frontend")
            if not os.path.exists(frontend_path):
                os.makedirs(frontend_path, exist_ok=True)
                
            await hass.http.async_register_static_paths([
                StaticPathConfig("/mass_ai_dj_frontend", frontend_path, False)
            ])
            
            await panel_custom.async_register_panel(
                hass,
                frontend_url_path="ai-dj",
                webcomponent_name="mass-ai-dj-panel",
                sidebar_title="AI DJ",
                sidebar_icon="mdi:music-box-multiple",
                module_url="/mass_ai_dj_frontend/mass-ai-dj-panel.js?v=2",
                trust_external=False,
            )
            
    except Exception as err:
        _LOGGER.error("Failed to initialize AI DJ services: %s", err)
        return False

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if "engine" in hass.data.get(DOMAIN, {}):
        hass.data[DOMAIN]["engine"].stop()

    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok