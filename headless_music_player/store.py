"""The saved player state (state.json): versioned, written atomically, read defensively."""

import json
import logging
import os
import secrets
from pathlib import Path

from .fsutil import atomic_write_text

logger = logging.getLogger(__name__)

STATE_VERSION = 2


class StateStore:
    def __init__(self, path: Path):
        self.path = path
        self._last_written: str | None = None

    def load(self) -> dict | None:
        """The saved state in the current format, or None when there is none or it's unreadable.

        An unreadable file is kept as state.json.corrupt rather than overwritten.
        """
        if not self.path.exists():
            return None
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError("not a JSON object")
        except (OSError, ValueError) as e:
            aside = self.path.with_name(self.path.name + ".corrupt")
            logger.error(f"Could not read {self.path} ({e}); keeping it as {aside.name} and starting fresh")
            try:
                os.replace(self.path, aside)
            except OSError:
                pass
            return None

        if data.get("version") != STATE_VERSION:
            data = migrate_v1(data)
            logger.info(f"Migrated {self.path.name} to version {STATE_VERSION}")
        return data

    def save(self, state: dict) -> bool:
        """Write the state unless it's unchanged since the last write. Returns whether it wrote."""
        text = json.dumps({**state, "version": STATE_VERSION}, indent=2, ensure_ascii=False)
        if text == self._last_written:
            return False
        try:
            atomic_write_text(self.path, text)
        except OSError as e:
            logger.error(f"Failed to save state: {e}")
            return False
        self._last_written = text
        return True


def migrate_v1(old: dict) -> dict:
    """Convert the 0.1 format ({"playback": ..., "queue": ...} with filenames) to version 2."""
    playback = old.get("playback") or {}
    queue = old.get("queue") or {}

    def names(key):
        value = queue.get(key)
        return [t for t in value if isinstance(t, str)] if isinstance(value, list) else []

    played = names("tracks")  # play order (shuffled when shuffle was on)
    original = names("original_order") or played
    ids = {name: secrets.token_hex(6) for name in dict.fromkeys(original + played)}
    entries = [[ids[n], n] for n in dict.fromkeys(original + played)]

    index = queue.get("index")
    current = None
    if isinstance(index, int) and 0 <= index < len(played):
        current = ids[played[index]]

    status = "stopped"
    if playback.get("current_file"):
        status = "paused" if playback.get("is_paused", True) else "playing"

    volume = playback.get("volume")
    position = playback.get("position_ms")
    return {
        "version": STATE_VERSION,
        "volume": volume if isinstance(volume, (int, float)) and not isinstance(volume, bool) else None,
        "status": status,
        "position_ms": position if isinstance(position, int) and status != "stopped" else 0,
        "queue": {
            "entries": entries,
            "shuffled": [ids[n] for n in played] if queue.get("shuffle") else None,
            "current": current,
            "repeat": queue.get("repeat_mode", "off"),
        },
    }
