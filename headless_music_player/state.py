"""Player state shared by the request threads and the background loop, persisted to disk.

Every read-modify-write of STATE happens under `lock`, which also guards the pygame
mixer calls in services/player.py. It is re-entrant, so services can call each other.
"""

import copy
import json
import logging
import os
import threading

from .config import DEFAULT_VOLUME, STATE_FILE

logger = logging.getLogger(__name__)

lock = threading.RLock()

DEFAULT_STATE = {
    "playback": {
        "is_paused": True,
        "current_file": "",
        "volume": DEFAULT_VOLUME,
        "position_ms": 0,
        "duration_ms": 0,
    },
    "queue": {
        "tracks": [],
        "index": 0,
        "shuffle": False,
        "repeat_mode": "off",  # off, one, all
        "original_order": [],  # queue order before shuffling
    },
}

STATE = copy.deepcopy(DEFAULT_STATE)

_last_saved = None


def load_state():
    """Load saved state. Only known keys are taken, so stale fields never come back."""
    path = STATE_FILE
    if not path.exists():
        logger.info("No saved state found, using defaults")
        return

    try:
        saved = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        # Keep the unreadable file for inspection instead of overwriting it with defaults.
        aside = path.with_name(path.name + ".corrupt")
        logger.error(f"Could not read {path} ({e}); moved it to {aside.name}, using defaults")
        try:
            os.replace(path, aside)
        except OSError:
            pass
        return

    with lock:
        for section, defaults in DEFAULT_STATE.items():
            values = saved.get(section) or {}
            for key in defaults:
                if key in values:
                    STATE[section][key] = values[key]
    logger.info(f"Loaded state from {path}")


def save_state():
    """Write the state atomically: a temp file, fsynced, then renamed over the old one.

    A power cut mid-write then leaves either the old or the new file, never a truncated one.
    Skipped when nothing changed since the last write.
    """
    global _last_saved
    with lock:
        data = json.dumps(STATE, indent=2, ensure_ascii=False)
        if data == _last_saved:
            return
        try:
            STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            tmp = STATE_FILE.with_name(STATE_FILE.name + ".tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, STATE_FILE)
            _fsync_dir(STATE_FILE.parent)
            _last_saved = data
        except OSError as e:
            logger.error(f"Failed to save state: {e}")


def _fsync_dir(path):
    # Makes the rename itself durable. Not possible on Windows, where it isn't needed.
    try:
        fd = os.open(path, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(fd)
    except OSError:
        pass
    finally:
        os.close(fd)


def snapshot():
    """A deep copy of the state, safe to change or serialize without the lock."""
    with lock:
        return copy.deepcopy(STATE)


def update_playback(**kwargs):
    with lock:
        STATE["playback"].update(kwargs)
        save_state()


def update_queue(**kwargs):
    with lock:
        STATE["queue"].update(kwargs)
        save_state()


def get_current_track():
    with lock:
        queue = STATE["queue"]
        if queue["tracks"] and 0 <= queue["index"] < len(queue["tracks"]):
            return queue["tracks"][queue["index"]]
        return None


def advance_queue():
    """Move to the next track in the queue. Returns the new current track or None."""
    with lock:
        queue = STATE["queue"]
        if not queue["tracks"]:
            return None

        if queue["repeat_mode"] == "one":
            return queue["tracks"][queue["index"]]

        next_index = queue["index"] + 1
        if next_index >= len(queue["tracks"]):
            if queue["repeat_mode"] != "all":
                return None
            next_index = 0

        queue["index"] = next_index
        save_state()
        return queue["tracks"][next_index]


def go_previous():
    """Move to the previous track in the queue. Returns the new current track or None."""
    with lock:
        queue = STATE["queue"]
        if not queue["tracks"]:
            return None

        prev_index = queue["index"] - 1
        if prev_index < 0:
            prev_index = len(queue["tracks"]) - 1 if queue["repeat_mode"] == "all" else 0

        queue["index"] = prev_index
        save_state()
        return queue["tracks"][prev_index]
