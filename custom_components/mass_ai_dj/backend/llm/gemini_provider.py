

import json
import logging
from typing import Any, override

import aiohttp

from ..model import Song
from .llm_provider import LLMProvider

from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=90)

class GeminiProvider(LLMProvider):
    def __init__(self, hass: HomeAssistant, api_key: str, model: str):
        self.hass = hass
        self.api_key = api_key
        self.model = model

    @override
    async def _query_llm(self, prompt: str) -> Song:

        session = async_get_clientsession(self.hass)
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        headers = {"x-goog-api-key": self.api_key}
        payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"responseMimeType": "application/json"}} # type: ignore

        try:
            async with session.post(url, json=payload, headers=headers, timeout=REQUEST_TIMEOUT) as response:
                if response.status != 200:
                    body = await response.text()
                    try:
                        body = json.loads(body)["error"]["message"]
                    except (ValueError, KeyError, TypeError):
                        pass
                    raise ValueError(f"Gemini API error {response.status} for model '{self.model}': {body}")
                response_data: dict[str, Any] = await response.json()

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
