"""The global play queue: order, shuffle and repeat."""

import logging
import random

from ..state import STATE, lock, save_state, update_queue
from .library import get_all_filenames

logger = logging.getLogger(__name__)

REPEAT_MODES = ("off", "all", "one")


def set_queue(tracks, start_index=0):
    update_queue(tracks=list(tracks), index=start_index, original_order=list(tracks))
    logger.info(f"Queue set: {len(tracks)} tracks, starting at {start_index}")


def add_to_queue(filename):
    """Append a track. Returns False when it's already queued (the queue holds each track once)."""
    with lock:
        queue = STATE["queue"]
        if filename in queue["tracks"]:
            return False
        queue["tracks"].append(filename)
        queue["original_order"].append(filename)
        save_state()
    logger.info(f"Added to queue: {filename}")
    return True


def remove_from_queue(index):
    with lock:
        queue = STATE["queue"]
        if not 0 <= index < len(queue["tracks"]):
            return False

        removed = queue["tracks"].pop(index)
        # Also drop it from the unshuffled order, or turning shuffle off brings it back.
        if removed in queue["original_order"]:
            queue["original_order"].remove(removed)

        if index < queue["index"]:
            queue["index"] -= 1
        elif index == queue["index"] and queue["index"] >= len(queue["tracks"]):
            queue["index"] = max(0, len(queue["tracks"]) - 1)

        save_state()
    logger.info(f"Removed from queue: {removed}")
    return True


def clear_queue():
    update_queue(tracks=[], index=0, original_order=[], shuffle=False)
    logger.info("Queue cleared")


def toggle_shuffle():
    """Toggle shuffle. Turning it on keeps the current track first and shuffles the rest."""
    with lock:
        queue = STATE["queue"]
        current = queue["tracks"][queue["index"]] if queue["tracks"] else None

        if queue["shuffle"]:
            queue["tracks"] = queue["original_order"].copy()
            if current in queue["tracks"]:
                queue["index"] = queue["tracks"].index(current)
            queue["shuffle"] = False
        else:
            others = [t for t in queue["tracks"] if t != current]
            random.shuffle(others)
            if current:
                queue["tracks"] = [current] + others
                queue["index"] = 0
            else:
                queue["tracks"] = others
            queue["shuffle"] = True

        save_state()
        shuffle = queue["shuffle"]
    logger.info(f"Shuffle: {'on' if shuffle else 'off'}")
    return shuffle


def set_repeat_mode(mode):
    if mode not in REPEAT_MODES:
        return False
    update_queue(repeat_mode=mode)
    logger.info(f"Repeat mode: {mode}")
    return True


def cycle_repeat_mode():
    """off -> all -> one -> off."""
    with lock:
        current = STATE["queue"]["repeat_mode"]
        new_mode = REPEAT_MODES[(REPEAT_MODES.index(current) + 1) % len(REPEAT_MODES)]
        set_repeat_mode(new_mode)
    return new_mode


def get_upcoming_tracks(count=10):
    with lock:
        queue = STATE["queue"]
        tracks = queue["tracks"]
        upcoming = []
        for i in range(count):
            idx = queue["index"] + 1 + i
            if idx >= len(tracks):
                if queue["repeat_mode"] != "all":
                    break
                idx %= len(tracks)
            upcoming.append(tracks[idx])
        return upcoming


def play_all(shuffle=False):
    """Queue the whole library."""
    tracks = get_all_filenames()
    if shuffle:
        random.shuffle(tracks)
    with lock:
        set_queue(tracks, 0)
        if shuffle:
            update_queue(shuffle=True)
    return tracks
