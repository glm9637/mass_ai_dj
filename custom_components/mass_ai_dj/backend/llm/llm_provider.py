import json
from abc import ABC, abstractmethod
from typing import Any

from homeassistant.util import dt as dt_util

from ..mass import parse_local_datetime
from ..model import Song, VibeSession

# JSON schema for the answer, so models can only reply with these two fields
SONG_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"artist": {"type": "string"}, "title": {"type": "string"}},
    "required": ["artist", "title"],
}


def parse_song_json(response_text: str) -> Song:
    """Parse the model's JSON answer into a Song, raising a readable error if it's unusable."""
    try:
        parsed: Any = json.loads(response_text)
    except json.JSONDecodeError as err:
        raise ValueError(f"The AI didn't answer with valid JSON: {response_text[:200]}") from err
    if isinstance(parsed, list):
        parsed = parsed[0] if parsed else {}
    if not isinstance(parsed, dict):
        raise ValueError(f"The AI answered with unexpected JSON: {response_text[:200]}")
    artist = str(parsed.get("artist") or "").strip()
    title = str(parsed.get("title") or "").strip()
    if not artist or not title:
        raise ValueError(f"The AI returned no artist or title: {response_text[:200]}")
    return Song(title=title, artist=artist)


class LLMProvider(ABC):
    """The base strategy for all AI providers."""

    @abstractmethod
    async def _query_llm(self, prompt: str) -> Song:
        """
        Must return a Song dataclass
        """
        pass

    async def generate_song(
        self, vibe: VibeSession, history: list[Song], rejected: list[Song] | None = None
    ) -> Song:
        timeline_note = ""
        from_dt = parse_local_datetime(vibe.from_date)
        to_dt = parse_local_datetime(vibe.to_date)
        if from_dt and to_dt:
            total_duration = (to_dt - from_dt).total_seconds()
            elapsed = (dt_util.now() - from_dt).total_seconds()

            progress_percentage = 0
            if total_duration > 0:
                progress_percentage = max(int((elapsed / total_duration) * 100), 0)

            if progress_percentage > 100:
                timeline_note = "The party has gone into overtime, keep the vibe going."
            else:
                timeline_note = (
                    f"We are {progress_percentage}% through this part of the party. "
                    "Shape the energy accordingly (warm up early, peak in the middle, wind down at the end)."
                )

        history_str = ", ".join(
            f"{h.title} by {h.artist}" for h in history[-60:]
        )
        if not history_str:
            history_str = "None yet"

        rejected_note = ""
        if rejected:
            rejected_str = ", ".join(f"{s.title} by {s.artist}" for s in rejected)
            rejected_note = (
                f"These picks could not be found on the streaming service, choose something else: {rejected_str}. "
            )

        prompt = (
            f"You are a DJ hosting a party for the following vibe: {vibe.vibe}.\n"
            f"Timeline Context: {timeline_note}\n"
            f"These songs were played or queued recently, do not repeat them: {history_str}.\n"
            f"{rejected_note}"
            "What is your next pick? Only pick real, released songs. "
            "Respond strictly in JSON format: {\"artist\": \"Name\", \"title\": \"Song Title\"}"
        )
        return await self._query_llm(prompt)
