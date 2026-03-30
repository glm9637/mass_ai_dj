"""Background DJ Engine to drive active AI DJ parties."""
from __future__ import annotations

import datetime
import logging
from typing import TYPE_CHECKING, Any

from homeassistant.core import Event, HomeAssistant
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util import dt as dt_util

from .const import DOMAIN

if TYPE_CHECKING:
    from custom_components.mass_ai_dj.backend.llm.llm_provider import LLMProvider
    from custom_components.mass_ai_dj.backend.model import Party, VibeSession
    from .store import PartyStore

_LOGGER = logging.getLogger(__name__)

POLL_INTERVAL = datetime.timedelta(seconds=30)


class DJEngine:
    """The central engine that monitors parties and interacts with APIs."""

    def __init__(self, hass: HomeAssistant, llm_provider: LLMProvider) -> None:
        """Initialize the DJ Engine."""
        self.hass = hass
        self.llm_provider = llm_provider
        
        self._unsub_interval = None
        self._unsub_force_poll = None
        
        self._last_history_ids: dict[str, str] = {}
        self._local_queued_counts: dict[str, int] = {}

    def _get_mass_client(self) -> Any | None:
        """Helper to safely retrieve the Music Assistant client instance."""
        mass_data = self.hass.data.get("music_assistant")
        if not mass_data:
            return None
            
        if isinstance(mass_data, dict):
            client = next(iter(mass_data.values()), None) # type: ignore
            if client is not None and hasattr(client, "client"): # type: ignore
                return client.client # type: ignore
            return client # type: ignore
        return mass_data

    def start(self) -> None:
        """Start the background monitoring loop."""
        if self._unsub_interval is None:
            # 1. Standard polling interval
            self._unsub_interval = async_track_time_interval(
                self.hass, self._async_poll, POLL_INTERVAL
            )
            
            # 2. Listener for manual triggers (from the UI)
            self._unsub_force_poll = self.hass.bus.async_listen(
                "mass_ai_dj_force_poll", self._handle_force_poll_event
            )

            # 3. Trigger initial run immediately
            self.hass.async_create_task(self._process_loop())
            _LOGGER.info("AI DJ Engine started.")

    def stop(self) -> None:
        """Stop the background monitoring loop and listeners."""
        if self._unsub_interval is not None:
            self._unsub_interval()
            self._unsub_interval = None
            
        if self._unsub_force_poll is not None:
            self._unsub_force_poll()
            self._unsub_force_poll = None
            
        _LOGGER.info("AI DJ Engine stopped.")

    async def _handle_force_poll_event(self, event: Event) -> None:
        """Handle an immediate poll request from the bus."""
        _LOGGER.debug("Force poll event received. Running DJ loop.")
        await self._process_loop()

    async def _async_poll(self, now: datetime.datetime) -> None:
        """The recurring 30-second polling loop."""
        await self._process_loop()

    async def _process_loop(self) -> None:
        """Core processing logic for each active party."""
        store: PartyStore = self.hass.data[DOMAIN].get("store")
        if not store:
            _LOGGER.error("PartyStore not found in DJ Engine.")
            return

        active_parties = [p for p in store.get_parties() if p.active]
        
        for party in active_parties:
            try:
                await self._process_party(party, store, self.llm_provider)
            except Exception as err:
                _LOGGER.error("Error processing party %s: %s", party.name, err)

    async def _process_party(self, party: Party, store: PartyStore, llm_provider: LLMProvider) -> None:
        """Process an individual active party."""
        target_player = party.media_player_id
        mass_client = self._get_mass_client()
        if not target_player or not mass_client:
            return

        # Fetch the player's queue state directly from Music Assistant
        try:
            queue = mass_client.player_queues.get(target_player)
        except Exception:
            queue = None
            
        if not queue:
            return

        state = str(getattr(queue, "state", "idle")).lower()
        if "." in state:
            state = state.split(".")[-1]

        # Handle Idle Player: Reset internal tracking
        if state in ["idle", "standby", "off"]:
            if self._local_queued_counts.get(party.id, 0) > 0:
                _LOGGER.info("[%s] Player idle. Resetting AI queue counter.", party.name)
            self._local_queued_counts[party.id] = 0
            return

        # Handle Active Player: Track song changes
        if state in ["playing", "paused"]:
            await self._handle_active_player(store, queue, party)

        # Trigger generation if queue is low
        queued_count = self._local_queued_counts.get(party.id, 0)
        if queued_count < 2:
            _LOGGER.debug("[%s] Queue low (%s/2). Requesting new track.", party.name, queued_count)
            await self._generate_and_add_song(party, llm_provider, mass_client)

    async def _handle_active_player(self, store: PartyStore, queue: Any, party: Party) -> None:
        """Detect song changes and manage history."""
        current_item = getattr(queue, "current_item", None)
        if not current_item:
            return
            
        # Extract metadata directly from Music Assistant queue item
        title = getattr(current_item, "name", None) or getattr(current_item, "title", None)
        
        media_item = getattr(current_item, "media_item", current_item)
        artists = getattr(media_item, "artists", [])
        
        if artists and isinstance(artists, list):
            artist = getattr(artists[0], "name", getattr(artists[0], "title", "Unknown Artist")) # type: ignore
        else:
            artist = getattr(current_item, "artist", "Unknown Artist")
            
        if title is None or artist is None or artist == "Unknown Artist":
            return
            
        current_song_id = f"{artist} - {title}"
        last_seen = self._last_history_ids.get(party.id)
                
        if current_song_id == last_seen:
            return
        
        self._last_history_ids[party.id] = current_song_id

        current_q = self._local_queued_counts.get(party.id, 0)
        if current_q > 0:
            self._local_queued_counts[party.id] = current_q - 1
                    
        in_history = any(
            title.lower() == h.title.lower() and artist.lower() == h.artist.lower()
            for h in party.history
        )
        if not in_history:
            await store.add_to_history(party.id, str(artist), str(title))
            _LOGGER.info("[%s] Now Playing: %s by %s", party.name, title, artist)

    async def _generate_and_add_song(self, party: Party, llm_provider: LLMProvider, mass_client: Any) -> None:
        """Trigger LLM and add to Music Assistant queue."""
        target_player = party.media_player_id
        if not target_player:
            return
        
        current_session = self._get_current_session(party)
        if not current_session:
            _LOGGER.warning("[%s] No active session (vibe) found.", party.name)
            return
        
        try:
            song = await llm_provider.generate_song(current_session, party.history)
            search_string = f"{song.artist} - {song.title}"
            
            # Use raw websocket command to bypass Enum import requirements
            await mass_client.connection.send_command(
                "player_queues/play_media", 
                queue_id=target_player, 
                media=search_string,
                enqueue="add" # enqueue option ADD is mapped directly
            )
            
            # Update internal queue tracking
            self._local_queued_counts[party.id] = self._local_queued_counts.get(party.id, 0) + 1
            _LOGGER.info("[%s] Added to MASS queue: %s", party.name, search_string)
                
        except Exception as e:
            _LOGGER.error("[%s] Song generation or service call failed: %s", party.name, e)

    def _get_current_session(self, party: Party) -> VibeSession | None:
        """Find the appropriate vibe session based on the current time."""
        now = dt_util.utcnow()
        earliest_session: VibeSession | None = None
        latest_session: VibeSession | None = None
        not_timed_candidate: VibeSession | None = None
        
        for session in party.sessions:
            from_dt = dt_util.parse_datetime(session.from_date) if session.from_date else None
            to_dt = dt_util.parse_datetime(session.to_date) if session.to_date else None
            
            if from_dt is None or to_dt is None:
                not_timed_candidate = not_timed_candidate or session
                continue

            if from_dt <= now <= to_dt:
                return session

            earliest_dt = dt_util.parse_datetime(earliest_session.from_date) if earliest_session and earliest_session.from_date else None
            if earliest_session is None or (earliest_dt and from_dt < earliest_dt):
                earliest_session = session

            latest_dt = dt_util.parse_datetime(latest_session.to_date) if latest_session and latest_session.to_date else None
            if latest_session is None or (latest_dt and to_dt > latest_dt):
                latest_session = session

        earliest_dt = dt_util.parse_datetime(earliest_session.from_date) if earliest_session and earliest_session.from_date else None
        if earliest_session and earliest_dt and earliest_dt <= now:
            return earliest_session
        if latest_session:
            return latest_session
        return not_timed_candidate