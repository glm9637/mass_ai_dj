

import json
import logging
from typing import override

from ..model import Song
from .llm_provider import LLMProvider

from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

class GeminiProvider(LLMProvider):
    def __init__(self, hass: HomeAssistant, api_key: str, model: str):
        self.hass = hass
        self.api_key = api_key
        self.model = model

    @override
    async def _query_llm(self, prompt: str) -> Song:
        
        session = async_get_clientsession(self.hass)
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"responseMimeType": "application/json"}} # type: ignore

        try:
            async with session.post(url, json=payload) as response:
                if response.status != 200:
                    _LOGGER.error("Gemini API error: %s", await response.text())
                    raise ValueError("Gemini API error")
                response_data = await response.json()
                response_text = response_data["candidates"][0]["content"]["parts"][0]["text"]
                
            parsed_data = json.loads(response_text)
            if isinstance(parsed_data, list):
                parsed_data = parsed_data[0] if parsed_data else {}
            artist = str(parsed_data.get("artist", "")).strip()
            title = str(parsed_data.get("title", "")).strip()
            if not artist or not title:
                raise ValueError(f"Gemini returned no artist or title: {response_text}")
            _LOGGER.info("AI DJ Selected: %s by %s", title, artist)
            return Song(title=title, artist=artist)
        except Exception as err:
            _LOGGER.error("Failed to query Gemini: %s", err)
            raise err
