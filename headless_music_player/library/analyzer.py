"""Background loudness analysis: measures every song once and caches it in the library index.

Runs on its own low-priority thread so playback is never starved on a Raspberry Pi. The
songs about to play (current and next, from `priority`) are measured first; the rest of
the library follows in order. Results are written to the index every few songs.
"""

import logging
import os
import sys
import threading
import time
from collections.abc import Callable

from .library import Library, Track
from .loudness import LoudnessError, measure

logger = logging.getLogger(__name__)

SAVE_EVERY = 10  # songs
SAVE_INTERVAL_S = 30.0


class LoudnessAnalyzer:
    def __init__(
        self,
        library: Library,
        priority: Callable[[], list[str]] = list,
        on_measured: Callable[[str], None] = lambda track_id: None,
    ):
        self.library = library
        self.priority = priority  # track ids to measure first
        self.on_measured = on_measured
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.current: str | None = None  # track id being measured

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, name="loudness", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._wake.set()
        if self._thread:
            self._thread.join(timeout=5)

    def wake(self) -> None:
        """Call after the library changed (scan, upload) or the queue moved on."""
        self._wake.set()

    @property
    def running(self) -> bool:
        return self.current is not None

    def _run(self) -> None:
        _lower_priority()
        unsaved, last_save = 0, time.monotonic()
        while not self._stop.is_set():
            track = self._next_track()
            if track is None:
                if unsaved:
                    self.library.save_index()
                    unsaved = 0
                self._wake.wait()
                self._wake.clear()
                continue

            self.measure_one(track)
            unsaved += 1
            if unsaved >= SAVE_EVERY or time.monotonic() - last_save > SAVE_INTERVAL_S:
                self.library.save_index()
                unsaved, last_save = 0, time.monotonic()
        if unsaved:
            self.library.save_index()

    def _next_track(self) -> Track | None:
        pending = {t.id: t for t in self.library.unanalyzed()}
        if not pending:
            return None
        for track_id in self.priority():
            if track_id in pending:
                return pending[track_id]
        return min(pending.values(), key=lambda t: t.id)

    def measure_one(self, track: Track) -> float | None:
        path = self.library.path_for(track.id)
        loudness = None
        self.current = track.id
        try:
            if path is not None:
                loudness = measure(path, should_stop=self._stop.is_set)
        except LoudnessError as e:
            if self._stop.is_set():
                return None
            logger.warning(f"Can't measure loudness of {track.id}: {e}")
        except Exception:
            logger.exception(f"Loudness analysis of {track.id} failed")
        finally:
            self.current = None
        if self.library.set_loudness(track, loudness):
            try:
                self.on_measured(track.id)
            except Exception as e:  # e.g. the engine is shutting down
                logger.debug(f"Loudness callback failed: {e}")
        return loudness


def _lower_priority() -> None:
    """Lower this thread's CPU priority so audio playback always wins.

    Only on Linux, where a thread id can be passed to setpriority; elsewhere it's a no-op.
    """
    if not sys.platform.startswith("linux"):
        return
    try:
        os.setpriority(os.PRIO_PROCESS, threading.get_native_id(), 10)
    except (AttributeError, OSError):
        pass
