"""Ollama API integration for AI DJ."""
from __future__ import annotations

import json
import logging
import time
from typing import Any, override

import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from ..model import Song
from .llm_provider import SONG_JSON_SCHEMA, LLMProvider, parse_song_json

_LOGGER = logging.getLogger(__name__)

# Local models can be slow, and the first request has to load the model into memory
REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=120)
# Keep the model loaded between songs instead of reloading it every few minutes
KEEP_ALIVE = "30m"


class OllamaProvider(LLMProvider):
    """LLM Provider implementation for local Ollama instances."""

    def __init__(self, hass: HomeAssistant, url: str, model: str) -> None:
        """Initialize the Ollama provider."""
        self.hass = hass
        self.url = url.rstrip("/")
        self.model = model
        # Newer Ollama features, switched off when the server or model rejects them:
        # a JSON schema as format (Ollama 0.5+) and disabling thinking (thinking models only)
        self._use_schema = True
        self._disable_thinking = True

    async def _generate(self, prompt: str) -> str:
        """Send the prompt and return the raw answer text."""
        session = async_get_clientsession(self.hass)
        payload: dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": SONG_JSON_SCHEMA if self._use_schema else "json",
            "keep_alive": KEEP_ALIVE,
        }
        if self._disable_thinking:
            payload["think"] = False

        async with session.post(f"{self.url}/api/generate", json=payload, timeout=REQUEST_TIMEOUT) as response:
            if response.status == 200:
                data: dict[str, Any] = await response.json()
                _LOGGER.debug(
                    "Ollama (%s) answered, load %.1fs, total %.1fs",
                    self.model, data.get("load_duration", 0) / 1e9, data.get("total_duration", 0) / 1e9,
                )
                return data.get("response", "")
            body = await response.text()

        try:
            body = json.loads(body)["error"]
        except (ValueError, KeyError, TypeError):
            pass
        error = str(body).lower()
        if response.status == 400 and self._disable_thinking and "think" in error:
            _LOGGER.info("Ollama model %s rejected 'think' (%s), retrying without it", self.model, body)
            self._disable_thinking = False
            return await self._generate(prompt)
        if response.status in (400, 500) and self._use_schema and ("format" in error or "unmarshal" in error):
            _LOGGER.info("Ollama rejected the JSON schema format (%s), falling back to plain JSON", body)
            self._use_schema = False
            return await self._generate(prompt)
        if response.status == 404:
            raise ValueError(f"Ollama model '{self.model}' not found on {self.url}. Did you pull it? ({body})")
        raise ValueError(f"Ollama error {response.status} for model '{self.model}': {body}")

    @override
    async def _query_llm(self, prompt: str) -> Song:
        """Query the Ollama instance and return a parsed Song."""
        started = time.monotonic()
        try:
            response_text = await self._generate(prompt)
            song = parse_song_json(response_text)
            _LOGGER.info(
                "[Ollama - %s] Selected: %s by %s (%.1fs)",
                self.model, song.title, song.artist, time.monotonic() - started,
            )
            return song
        except TimeoutError as err:
            raise ValueError(
                f"Ollama model '{self.model}' did not answer within {REQUEST_TIMEOUT.total:.0f}s. "
                "Try a smaller model (Configure on the integration)."
            ) from err
        except aiohttp.ClientConnectionError as err:
            raise ValueError(f"Can't reach Ollama at {self.url}: {err}") from err
        except Exception as err:
            _LOGGER.error("Failed to query Ollama (%s): %s: %s", self.model, type(err).__name__, err)
            raise
