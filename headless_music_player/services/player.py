"""Audio playback through the pygame mixer.

pygame can't report the playback position, so it is estimated from when playback
last started (_play_start_time) and where it started (_play_start_position).
"""

import logging
import os
import time

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
from pygame import mixer  # noqa: E402

from ..config import MIXER_SETTINGS, MUSIC_DIR  # noqa: E402
from ..state import (  # noqa: E402
    STATE,
    advance_queue,
    get_current_track,
    go_previous,
    lock,
    update_playback,
)
from .library import get_track_info  # noqa: E402

logger = logging.getLogger(__name__)

_play_start_time = 0
_play_start_position = 0
_is_initialized = False


def init_player():
    global _is_initialized
    with lock:
        if not _is_initialized:
            mixer.init(**MIXER_SETTINGS)
            _is_initialized = True
            logger.info(f"Player initialized ({MIXER_SETTINGS})")


def _get_filepath(filename):
    return os.path.join(MUSIC_DIR, filename)


def play(filename, start_position_ms=0):
    """Start playing a track."""
    global _play_start_time, _play_start_position

    with lock:
        filepath = _get_filepath(filename)
        if not os.path.exists(filepath):
            logger.error(f"File not found: {filepath}")
            return False

        try:
            track_info = get_track_info(filename)
            duration_ms = track_info.get("duration_ms", 0) if track_info else 0

            mixer.music.load(filepath)
            mixer.music.play()
            if start_position_ms > 0:
                mixer.music.set_pos(start_position_ms / 1000.0)

            _play_start_time = time.time()
            _play_start_position = start_position_ms

            update_playback(
                is_paused=False,
                current_file=filename,
                position_ms=start_position_ms,
                duration_ms=duration_ms,
            )
            logger.info(f"Playing: {filename}")
            return True

        except Exception as e:
            logger.error(f"Failed to play {filename}: {e}")
            return False


def pause():
    global _play_start_position

    with lock:
        if STATE["playback"]["is_paused"]:
            return False

        _play_start_position = get_position()
        mixer.music.pause()
        update_playback(is_paused=True, position_ms=_play_start_position)
        logger.info("Paused")
        return True


def resume():
    global _play_start_time

    with lock:
        if not STATE["playback"]["is_paused"]:
            return False

        _play_start_time = time.time()
        mixer.music.unpause()
        update_playback(is_paused=False)
        logger.info("Resumed")
        return True


def stop():
    global _play_start_position

    with lock:
        mixer.music.stop()
        _play_start_position = 0
        update_playback(is_paused=True, current_file="", position_ms=0, duration_ms=0)
        logger.info("Stopped")


def seek(position_ms):
    global _play_start_time, _play_start_position

    with lock:
        if not STATE["playback"]["current_file"]:
            return False

        try:
            mixer.music.set_pos(position_ms / 1000.0)
            _play_start_time = time.time()
            _play_start_position = position_ms
            update_playback(position_ms=position_ms)
            logger.debug(f"Seeked to {position_ms}ms")
            return True
        except Exception as e:
            logger.error(f"Seek failed: {e}")
            return False


def get_position():
    """Current playback position in milliseconds."""
    with lock:
        playback = STATE["playback"]
        if playback["is_paused"] or not mixer.music.get_busy():
            return playback["position_ms"]

        position = _play_start_position + (time.time() - _play_start_time) * 1000
        duration = playback["duration_ms"]
        if duration > 0 and position > duration:
            position = duration
        return int(position)


def sync_position():
    """Copy the estimated position into the state so the next save includes it."""
    with lock:
        if not STATE["playback"]["is_paused"] and STATE["playback"]["current_file"]:
            STATE["playback"]["position_ms"] = get_position()


def set_volume(volume):
    """Set volume, 0.0 to 1.0."""
    volume = max(0.0, min(1.0, volume))
    with lock:
        mixer.music.set_volume(volume)
        update_playback(volume=volume)
    logger.debug(f"Volume set to {volume}")


def is_playing():
    with lock:
        return mixer.music.get_busy() and not STATE["playback"]["is_paused"]


def next_track():
    with lock:
        track = advance_queue()
        if track:
            play(track)
            return track
        stop()
        return None


def prev_track():
    with lock:
        # More than 3 seconds in: restart the current track instead.
        if get_position() > 3000:
            current = get_current_track()
            if current:
                play(current)
                return current

        track = go_previous()
        if track:
            play(track)
            return track
        return None


def check_track_ended():
    """Called every second: move on when the current track finished."""
    with lock:
        if STATE["playback"]["current_file"] and not STATE["playback"]["is_paused"]:
            if not mixer.music.get_busy():
                logger.info("Track ended")
                next_track()
                return True
        return False


def restore_state():
    """Restore volume and the current track after a restart."""
    global _play_start_time, _play_start_position

    init_player()
    with lock:
        playback = STATE["playback"]
        mixer.music.set_volume(playback["volume"])
        logger.info(f"Volume restored to {playback['volume']}")

        if not playback["current_file"]:
            return

        filepath = _get_filepath(playback["current_file"])
        if not os.path.exists(filepath):
            logger.warning(f"Saved track not found: {filepath}")
            update_playback(current_file="", position_ms=0, is_paused=True)
            return

        try:
            mixer.music.load(filepath)
            mixer.music.play()
            if playback["position_ms"] > 0:
                mixer.music.set_pos(playback["position_ms"] / 1000.0)

            if playback["is_paused"]:
                mixer.music.pause()
            else:
                _play_start_time = time.time()
                _play_start_position = playback["position_ms"]

            logger.info(f"Restored playback: {playback['current_file']}")
        except Exception as e:
            logger.error(f"Failed to restore playback: {e}")
