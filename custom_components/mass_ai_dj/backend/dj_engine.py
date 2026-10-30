"""Background DJ Engine to drive active AI DJ parties."""
from __future__ import annotations

import asyncio
import datetime
import logging
from typing import TYPE_CHECKING, Any

from homeassistant.core import Event, HomeAssistant
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .mass import describe_mass_problem, enum_value, get_mass_client, parse_local_datetime
from .model import Song

if TYPE_CHECKING:
    from .llm.llm_provider import LLMProvider
    from .model import Party, VibeSession
    from .store import PartyStore

_LOGGER = logging.getLogger(__name__)

POLL_INTERVAL = datetime.timedelta(seconds=30)
FORCE_POLL_EVENT = "mass_ai_dj_force_poll"

# Keep at least this many upcoming tracks in the MA queue
MIN_UPCOMING_TRACKS = 2
# How often the LLM may pick a song that MA can't find before we give up for this round
MAX_PICK_ATTEMPTS = 3
# How many of the songs we queued (but that haven't played yet) to remember for duplicate avoidance
MAX_PENDING = 10
# Time limits for Music Assistant calls, so a hanging call can't block the party forever
MASS_SEARCH_TIMEOUT = 30
MASS_PLAY_TIMEOUT = 45


class DJEngine:
    """The central engine that monitors parties and interacts with APIs."""

    def __init__(self, hass: HomeAssistant, llm_provider: LLMProvider) -> None:
        """Initialize the DJ Engine."""
        self.hass = hass
        self.llm_provider = llm_provider

        self._unsub_interval = None
        self._unsub_force_poll = None

        self._last_history_ids: dict[str, str] = {}
        # Songs queued by the DJ that did not show up in the history yet
        self._pending: dict[str, list[Song]] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    def start(self) -> None:
        """Start the background monitoring loop."""
        if self._unsub_interval is None:
            # 1. Standard polling interval
            self._unsub_interval = async_track_time_interval(
                self.hass, self._async_poll, POLL_INTERVAL
            )

            # 2. Listener for manual triggers (from the UI)
            self._unsub_force_poll = self.hass.bus.async_listen(
                FORCE_POLL_EVENT, self._handle_force_poll_event
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
        """Handle an immediate poll request from the bus (e.g. a party got started)."""
        _LOGGER.debug("Force poll event received. Running DJ loop.")
        await self._process_loop(kickoff_party_id=event.data.get("party_id"))

    async def _async_poll(self, now: datetime.datetime) -> None:
        """The recurring 30-second polling loop."""
        await self._process_loop()

    async def _process_loop(self, kickoff_party_id: str | None = None) -> None:
        """Core processing logic for each active party."""
        store: PartyStore | None = self.hass.data.get(DOMAIN, {}).get("store")
        if not store:
            _LOGGER.error("PartyStore not found in DJ Engine.")
            return

        active_parties = [p for p in store.get_parties() if p.active]
        mass = get_mass_client(self.hass)
        if mass is None:
            for party in active_parties:
                self._set_status(party, f"Can't reach Music Assistant: {describe_mass_problem(self.hass)}", "error")
            return

        for party in active_parties:
            kickoff = party.id == kickoff_party_id
            lock = self._locks.setdefault(party.id, asyncio.Lock())
            if lock.locked() and not kickoff:
                # A previous run (LLM call / search) for this party is still in progress
                continue
            async with lock:
                try:
                    await self._process_party(party, store, mass, kickoff=kickoff)
                except Exception as err:
                    _LOGGER.exception("Error processing party %s", party.name)
                    self._set_status(party, f"Unexpected error: {type(err).__name__}: {err}", "error")

    def _set_status(self, party: Party, message: str, level: str = "info") -> None:
        """Remember what the DJ is doing for the panel, and log it."""
        statuses: dict[str, dict[str, str]] = self.hass.data[DOMAIN].setdefault("status", {})
        previous = statuses.get(party.id, {})
        statuses[party.id] = {
            "message": message,
            "level": level,
            "updated": dt_util.utcnow().isoformat(),
        }
        if previous.get("message") == message:
            return
        log_level = logging.ERROR if level == "error" else logging.WARNING if level == "warning" else logging.INFO
        _LOGGER.log(log_level, "[%s] %s", party.name, message)

    async def _process_party(
        self, party: Party, store: PartyStore, mass: Any, kickoff: bool
    ) -> None:
        """Process an individual active party."""
        if not party.media_player_id:
            self._set_status(party, "No speaker selected.", "warning")
            return

        queue_id = self._resolve_queue_id(mass, party.media_player_id)
        queue = mass.player_queues.get(queue_id)
        if queue is None:
            self._set_status(party, f"Speaker '{party.media_player_id}' not found in Music Assistant.", "error")
            return

        state = enum_value(queue.state)
        if state in ("playing", "paused"):
            await self._track_current_song(store, queue, party)

        if kickoff:
            # Starting the party takes over the speaker: replace whatever was queued before
            self._set_status(party, f"Starting: picking the first song for {queue.display_name}…")
            await self._generate_and_enqueue(party, mass, queue_id, option="replace")
            return

        if state != "playing":
            # Respect that the user paused / stopped the music.
            self._set_status(party, f"Speaker is {state}. Stop and start the AI DJ to restart the music.", "warning")
            return

        upcoming = self._upcoming_count(queue)
        if upcoming < MIN_UPCOMING_TRACKS:
            self._set_status(party, f"Queue is running low ({upcoming} upcoming), picking a song…")
            await self._generate_and_enqueue(party, mass, queue_id, option="add")
        else:
            self._set_status(party, f"Playing, {upcoming} songs queued. Waiting until fewer than {MIN_UPCOMING_TRACKS} are left.")

    @staticmethod
    def _resolve_queue_id(mass: Any, player_id: str) -> str:
        """Return the queue that is actually active for the player (e.g. when it's grouped)."""
        player = mass.players.get(player_id)
        if player is not None:
            if player.synced_to:
                return player.synced_to
            if player.active_source and mass.player_queues.get(player.active_source):
                return player.active_source
        return player_id

    @staticmethod
    def _upcoming_count(queue: Any) -> int:
        """Number of queue items after the currently playing one."""
        total = queue.items or 0
        if queue.current_index is None:
            return total
        return max(total - queue.current_index - 1, 0)

    async def _track_current_song(self, store: PartyStore, queue: Any, party: Party) -> None:
        """Detect song changes and add them to the party history."""
        current_item = queue.current_item
        if current_item is None:
            return

        media_item = current_item.media_item
        if media_item is not None:
            title = media_item.name
            artists = getattr(media_item, "artists", None) or []
            artist = ", ".join(a.name for a in artists) if artists else None
        else:
            # Fallback: queue items are named "Artist - Title"
            artist, _, title = current_item.name.partition(" - ")
            if not title:
                artist, title = None, current_item.name

        if not title or not artist:
            return

        current_song_id = f"{artist} - {title}"
        if current_song_id == self._last_history_ids.get(party.id):
            return
        self._last_history_ids[party.id] = current_song_id

        pending = self._pending.get(party.id, [])
        self._pending[party.id] = [s for s in pending if not _same_song(s, artist, title)]

        last = party.history[-1] if party.history else None
        if last is None or not _same_song(last, artist, title):
            await store.add_to_history(party.id, artist, title)
            _LOGGER.info("[%s] Now Playing: %s by %s", party.name, title, artist)

    async def _generate_and_enqueue(
        self, party: Party, mass: Any, queue_id: str, option: str
    ) -> None:
        """Ask the LLM for a song, resolve it in Music Assistant and put it on the queue."""
        current_session = self._get_current_session(party)
        if not current_session:
            self._set_status(party, "No vibe defined. Add a vibe slot and save the timeline.", "warning")
            return

        pending = self._pending.setdefault(party.id, [])
        rejected: list[Song] = []
        for _ in range(MAX_PICK_ATTEMPTS):
            self._set_status(party, f"Asking the AI for a song ({current_session.vibe or 'no vibe text'})…")
            try:
                song = await self.llm_provider.generate_song(
                    current_session, party.history + pending, rejected
                )
            except Exception as err:
                self._set_status(party, f"The AI couldn't pick a song: {err}", "error")
                return

            self._set_status(party, f"AI picked '{song.title}' by {song.artist}, searching Music Assistant…")
            try:
                async with asyncio.timeout(MASS_SEARCH_TIMEOUT):
                    uri = await self._find_track_uri(mass, song)
            except TimeoutError:
                self._set_status(party, f"Music Assistant search for '{song.title}' took longer than {MASS_SEARCH_TIMEOUT}s.", "error")
                return
            except Exception as err:
                self._set_status(party, f"Music Assistant search failed: {type(err).__name__}: {err}", "error")
                return
            if uri is None:
                self._set_status(party, f"Music Assistant couldn't find '{song.title}' by {song.artist}, asking the AI again…")
                rejected.append(song)
                continue

            self._set_status(party, f"Sending '{song.title}' by {song.artist} to the speaker ({uri})…")
            try:
                async with asyncio.timeout(MASS_PLAY_TIMEOUT):
                    await mass.player_queues.play_media(queue_id, media=uri, option=option)
            except TimeoutError:
                self._set_status(party, f"The speaker didn't accept '{song.title}' within {MASS_PLAY_TIMEOUT}s. Is it switched on?", "error")
                return
            except Exception as err:
                self._set_status(party, f"Music Assistant couldn't play '{song.title}': {type(err).__name__}: {err}", "error")
                return
            pending.append(song)
            del pending[:-MAX_PENDING]
            verb = "Now playing" if option == "replace" else "Queued"
            self._set_status(party, f"{verb}: '{song.title}' by {song.artist}.")
            return

        self._set_status(party, f"Gave up: none of the AI's last {MAX_PICK_ATTEMPTS} picks were found in Music Assistant.", "error")

    @staticmethod
    async def _find_track_uri(mass: Any, song: Song) -> str | None:
        """Search all MA providers for the song and return the best matching track uri."""
        if not song.title:
            return None
        results = await mass.music.search(
            f"{song.artist} {song.title}", media_types=["track"], limit=10
        )
        tracks = [t for t in results.tracks if getattr(t, "uri", None)]
        if not tracks:
            return None

        wanted_title = song.title.lower()
        wanted_artist = song.artist.lower()

        def score(track: Any) -> int:
            name = (track.name or "").lower()
            artists = " ".join(a.name.lower() for a in getattr(track, "artists", None) or [])
            points = 0
            if name == wanted_title:
                points += 4
            elif wanted_title in name or name in wanted_title:
                points += 2
            if wanted_artist and (wanted_artist in artists or artists in wanted_artist):
                points += 3
            return points

        best = max(tracks, key=score)
        if score(best) < 3:
            # Neither title nor artist really matched; don't play a random song
            return None
        return best.uri

    def _get_current_session(self, party: Party) -> VibeSession | None:
        """Find the appropriate vibe session based on the current time."""
        now = dt_util.now()
        timed: list[tuple[datetime.datetime, datetime.datetime, VibeSession]] = []
        untimed: VibeSession | None = None

        for session in party.sessions:
            from_dt = parse_local_datetime(session.from_date)
            to_dt = parse_local_datetime(session.to_date)
            if from_dt is None or to_dt is None:
                untimed = untimed or session
                continue
            if from_dt <= now <= to_dt:
                return session
            timed.append((from_dt, to_dt, session))

        # An untimed session acts as the default whenever no timed session is running
        if untimed or not timed:
            return untimed

        # Before the first session: use the first one. After / between sessions: the latest that already started.
        started = [t for t in timed if t[0] <= now]
        if not started:
            return min(timed, key=lambda t: t[0])[2]
        return max(started, key=lambda t: t[0])[2]


def _same_song(song: Song, artist: str, title: str) -> bool:
    return song.title.lower() == title.lower() and song.artist.lower() == artist.lower()
