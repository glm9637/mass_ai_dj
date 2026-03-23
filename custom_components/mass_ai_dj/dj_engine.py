"""Background DJ Engine to drive active AI DJ parties."""
from __future__ import annotations

import datetime
import json
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .store import PartyStore

_LOGGER = logging.getLogger(__name__)

POLL_INTERVAL = datetime.timedelta(seconds=30)
MIN_DURATION_SEC = 120
MAX_DURATION_SEC = 420


class DJEngine:
    """The central engine that monitors parties and interacts with APIs."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the DJ Engine."""
        self.hass = hass
        self._unsub_interval = None
        self._playlist_ids: dict[str, str] = {}
        
        self._last_history_ids: dict[str, str] = {}

    def start(self) -> None:
        """Start the background monitoring loop."""
        if self._unsub_interval is None:
            self._unsub_interval = async_track_time_interval(
                self.hass, self._async_poll, POLL_INTERVAL
            )
            _LOGGER.info("AI DJ Engine started.")

    def stop(self) -> None:
        """Stop the background monitoring loop."""
        if self._unsub_interval is not None:
            self._unsub_interval()
            self._unsub_interval = None
            _LOGGER.info("AI DJ Engine stopped.")

    async def _async_poll(self, now: datetime.datetime) -> None:
        """The 30-second polling loop."""
        store: PartyStore | None = self.hass.data[DOMAIN].get("store")
        services = self.hass.data[DOMAIN]
        
        gemini_key: str | None = None

        for key, value in services.items():
            if isinstance(value, dict) and "gemini_key" in value:
                gemini_key = value.get("gemini_key") 
                break
                
        if not store or not gemini_key:
            return

        active_parties = [p for p in store.get_parties() if p.get("active")]
        
        for party in active_parties:
            try:
                await self._process_party(party, store, gemini_key)
            except Exception as err:
                _LOGGER.error("Error processing party %s: %s", party.get("name"), err)

    async def _process_party(self, party: dict[str, Any], store: PartyStore, gemini_key: str) -> None:
        """Process an individual active party (Local Queue Only)."""
        party_id = party["id"]
        
        if not hasattr(self, "_local_queued_counts"):
            self._local_queued_counts = {}

        # 1. Sync History & Manage Local Queue
        target_player = party.get("media_player_id")
        player_state = self.hass.states.get(target_player) if target_player else None

        if player_state and player_state.state in ["idle", "standby", "off"]:
            if self._local_queued_counts.get(party_id, 0) > 0:
                _LOGGER.info("Player is idle. Resetting AI DJ queue counter.")
            self._local_queued_counts[party_id] = 0
            
        elif player_state and player_state.state in ["playing", "paused"]:
            current_title = player_state.attributes.get("media_title")
            current_artist = player_state.attributes.get("media_artist")
            
            if current_title and current_artist:
                current_song_id = f"{current_artist} - {current_title}"
                last_seen = self._last_history_ids.get(party_id)
                
                if current_song_id != last_seen:
                    self._last_history_ids[party_id] = current_song_id
                    
                    # Deduct from our mental queue
                    current_q = self._local_queued_counts.get(party_id, 0)
                    if current_q > 0:
                        self._local_queued_counts[party_id] = current_q - 1
                    
                    # Add to UI History
                    song_already_in_party_history = any(
                        current_title.lower() == h.get("title", "").lower() and 
                        current_artist.lower() == h.get("artist", "").lower()
                        for h in party.get("history", [])
                    )
                    if not song_already_in_party_history:
                        await store.add_to_history(party_id, current_artist, current_title)
                        _LOGGER.info("Now Playing: %s by %s", current_title, current_artist)

        # 2. Check Queue and Trigger LLM
        queued_count = self._local_queued_counts.get(party_id, 0)
        
        if queued_count < 2:
            _LOGGER.debug("Queue low (%s). Triggering LLM...", queued_count)
            await self._generate_and_add_song(party, store, gemini_key)

    async def _generate_and_add_song(
        self, party: dict[str, Any], store: PartyStore, gemini_key: str
    ) -> None:
        """Trigger Gemini via REST API to get a recommendation and add to MASS playlist."""

        start_time_str = party.get("start_time")
        end_time_str = party.get("end_time")
        now = dt_util.utcnow()
        
        start_time = dt_util.parse_datetime(start_time_str) if start_time_str else now
        if not start_time.tzinfo:
            start_time = start_time.replace(tzinfo=dt_util.UTC)
            
        end_time = dt_util.parse_datetime(end_time_str) if end_time_str else (start_time + datetime.timedelta(hours=4))
        if not end_time.tzinfo:
            end_time = end_time.replace(tzinfo=dt_util.UTC)
            
        total_duration = (end_time - start_time).total_seconds()
        elapsed = (now - start_time).total_seconds()
        
        progress_percentage = 0
        if total_duration > 0:
            progress_percentage = int((elapsed / total_duration) * 100)
            
        overtime_note = ""
        if progress_percentage > 100:
            overtime_note = "The party has gone into overtime, keep the vibe going."
            
        history_str = ", ".join(
            f"{h['title']} by {h['artist']}" for h in party.get("history", [])[-10:]
        )
        if not history_str:
            history_str = "None yet."

        prompt = (
            f"You are a DJ hosting a party for the following vibe: {party.get('vibe')}. "
            f"Timeline Context:\n"
            f"Start Time: {start_time_str}\n"
            f"Expected End Time: {end_time_str}\n"
            f"Current Time: {now.isoformat()}\n"
            f"We are currently {progress_percentage}% through the planned duration. Use this percentage to map the energy curve "
            f"(e.g., 0-20% warm-up, 40-70% peak energy, 95-100% cooldown).\n"
            f"These songs were played recently: {history_str}. What is your next pick? {overtime_note} "
            f"Respond strictly in JSON format: {{\"artist\": \"Name\", \"title\": \"Song Title\"}}"
        )

        session = async_get_clientsession(self.hass)
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_key}"
        payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"responseMimeType": "application/json"}}

        try:
            async with session.post(url, json=payload) as response:
                if response.status != 200:
                    _LOGGER.error("Gemini API error: %s", await response.text())
                    return
                response_data = await response.json()
                response_text = response_data["candidates"][0]["content"]["parts"][0]["text"]
                
            parsed_data = json.loads(response_text)
            artist = parsed_data.get("artist", "")
            title = parsed_data.get("title", "")
            _LOGGER.info("AI DJ Selected: %s by %s", title, artist)
        except Exception as err:
            _LOGGER.error("Failed to query Gemini: %s", err)
            return

        target_player = party.get("media_player_id")
        if target_player:
            # Wir übergeben einfach "Künstler - Titel". Music Assistant sucht dann selbst!
            search_string = f"{artist} - {title}"
            
            try:
                await self.hass.services.async_call(
                    domain="music_assistant",
                    service="play_media",
                    service_data={
                        "media_id": search_string, 
                        "media_type": "track", 
                        "enqueue": "add"
                    },
                    target={"entity_id": target_player}
                )
                
                # Update internal queue
                if not hasattr(self, "_local_queued_counts"):
                    self._local_queued_counts = {}
                self._local_queued_counts[party["id"]] = self._local_queued_counts.get(party["id"], 0) + 1
                
                _LOGGER.info("Erfolgreich an MASS gesendet zur universellen Suche: %s", search_string)
                
            except Exception as e:
                _LOGGER.error("Fehler beim Senden an Music Assistant: %s", e)