"""Helpers to access the Music Assistant client owned by the HA music_assistant integration."""
from __future__ import annotations

import datetime
from typing import Any

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

MASS_DOMAIN = "music_assistant"


def get_mass_client(hass: HomeAssistant) -> Any | None:
    """Return the MusicAssistantClient of the first loaded music_assistant entry.

    The music_assistant integration keeps its client in entry.runtime_data.mass,
    it does not put anything into hass.data.
    """
    for entry in hass.config_entries.async_entries(MASS_DOMAIN):
        if entry.state is not ConfigEntryState.LOADED:
            continue
        runtime_data = getattr(entry, "runtime_data", None)
        if mass := getattr(runtime_data, "mass", None):
            return mass
    return None


def describe_mass_problem(hass: HomeAssistant) -> str:
    """Explain why get_mass_client returned None, for error messages."""
    entries = hass.config_entries.async_entries(MASS_DOMAIN)
    if not entries:
        return (
            "The Music Assistant integration is not set up in Home Assistant. "
            "Add it under Settings > Devices & Services > Add Integration > Music Assistant "
            "(the Music Assistant add-on alone is not enough)."
        )
    states = ", ".join(f"'{e.title}': {e.state.value}" for e in entries)
    return f"No loaded Music Assistant integration entry (found {states})."


def enum_value(value: Any) -> str:
    """Return the plain lowercase string of an enum (or string) value."""
    return str(getattr(value, "value", value)).lower()


def parse_local_datetime(value: str | None) -> datetime.datetime | None:
    """Parse an ISO string; naive values (from datetime-local inputs) are treated as HA local time."""
    if not value:
        return None
    parsed = dt_util.parse_datetime(value)
    if parsed is None:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt_util.get_default_time_zone())
    return parsed
