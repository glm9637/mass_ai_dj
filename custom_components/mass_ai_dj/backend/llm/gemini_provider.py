

import json
import logging
import time
from typing import Any, override

import aiohttp

from ..model import Song
from .llm_provider import LLMProvider

from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=90)

SONG_SCHEMA = {
    "type": "OBJECT",
    "properties": {"artist": {"type": "STRING"}, "title": {"type": "STRING"}},
    "required": ["artist", "title"],
}

class GeminiProvider(LLMProvider):
    def __init__(self, hass: HomeAssistant, api_key: str, model: str):
        self.hass = hass
        self.api_key = api_key
        self.model = model
        # Picking a song needs no deep reasoning; thinking made requests take over 90s.
        # Cleared if the model rejects the setting.
        self._thinking_config: dict[str, Any] | None = {"thinkingLevel": "minimal"}

    async def _generate(self, prompt: str) -> dict[str, Any]:
        """Send the prompt, return the raw response data or raise with Google's error message."""
        session = async_get_clientsession(self.hass)
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        headers = {"x-goog-api-key": self.api_key}
        generation_config: dict[str, Any] = {
            "responseMimeType": "application/json",
            "responseSchema": SONG_SCHEMA,
        }
        if self._thinking_config:
            generation_config["thinkingConfig"] = self._thinking_config
        payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": generation_config}

        async with session.post(url, json=payload, headers=headers, timeout=REQUEST_TIMEOUT) as response:
            if response.status == 200:
                return await response.json()
            body = await response.text()
        try:
            body = json.loads(body)["error"]["message"]
        except (ValueError, KeyError, TypeError):
            pass
        if response.status == 400 and self._thinking_config and "think" in str(body).lower():
            _LOGGER.info("Model %s rejected thinkingConfig (%s), retrying without it", self.model, body)
            self._thinking_config = None
            return await self._generate(prompt)
        raise ValueError(f"Gemini API error {response.status} for model '{self.model}': {body}")

    @override
    async def _query_llm(self, prompt: str) -> Song:
        try:
            started = time.monotonic()
            response_data = await self._generate(prompt)
            _LOGGER.debug(
                "Gemini (%s) answered in %.1fs, usage: %s",
                self.model, time.monotonic() - started, response_data.get("usageMetadata"),
            )

            response_text = _extract_text(response_data)
            parsed_data = json.loads(response_text)
            if isinstance(parsed_data, list):
                parsed_data = parsed_data[0] if parsed_data else {}
            artist = str(parsed_data.get("artist", "")).strip()
            title = str(parsed_data.get("title", "")).strip()
            if not artist or not title:
                raise ValueError(f"Gemini returned no artist or title: {response_text}")
            _LOGGER.info("AI DJ Selected: %s by %s", title, artist)
            return Song(title=title, artist=artist)
        except TimeoutError as err:
            _LOGGER.error("Gemini (%s) did not answer within %ss", self.model, REQUEST_TIMEOUT.total)
            raise ValueError("Gemini request timed out") from err
        except Exception as err:
            _LOGGER.error("Failed to query Gemini (%s): %s: %s", self.model, type(err).__name__, err)
            raise


def _extract_text(response_data: dict[str, Any]) -> str:
    """Return the answer text, skipping thought parts, or raise with the reason there is none."""
    candidates = response_data.get("candidates") or []
    if not candidates:
        feedback = response_data.get("promptFeedback", {})
        raise ValueError(f"Gemini returned no answer (blocked?): {feedback or response_data}")
    candidate = candidates[0]
    parts = (candidate.get("content") or {}).get("parts") or []
    text = "".join(p.get("text", "") for p in parts if not p.get("thought"))
    if not text:
        raise ValueError(f"Gemini returned an empty answer (finishReason: {candidate.get('finishReason')})")
    return text
