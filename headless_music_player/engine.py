"""The player engine: the only owner of playback, the queue and the audio device.

Web requests never touch that state directly. Each public method sends a command to the
engine thread, which runs commands one at a time between its periodic ticks (end-of-track
detection, retrying a missing sound card, saving). After every command and tick it
publishes an immutable Snapshot that any thread can read without locking.

With threaded=False, commands run on the caller's thread and ticks are driven by calling
tick(); tests use that together with the fake audio backend and a fake clock.
"""

import logging
import queue as stdlib_queue
import random
import threading
import time
from collections.abc import Callable
from concurrent.futures import Future
from dataclasses import dataclass

from .audio import AudioBackend, AudioUnavailableError, BackendError
from .config import (
    AUDIO_RETRY_S,
    DEFAULT_LOUDNESS_TARGET,
    DEFAULT_VOLUME,
    ENGINE_TICK_S,
    LOUDNESS_TARGETS,
    MAX_BOOST_DB,
    MAX_CUT_DB,
    POSITION_SAVE_INTERVAL_S,
    RESTART_THRESHOLD_MS,
    SAVE_DEBOUNCE_S,
)
from .library import Library
from .playqueue import REPEAT_MODES, Entry, PlayQueue
from .store import StateStore

logger = logging.getLogger(__name__)

STATUSES = ("stopped", "playing", "paused")
COMMAND_TIMEOUT_S = 15


class CommandError(Exception):
    """A command that can't be carried out; the message is shown to the user."""

    def __init__(self, message: str, status: int = 409):
        super().__init__(message)
        self.status = status


@dataclass(frozen=True)
class Snapshot:
    version: int  # bumps on every change
    queue_version: int  # bumps when the queue's entries, order, current entry or modes change
    status: str
    position_ms: int
    position_at: float  # engine clock time when position_ms was taken
    duration_ms: int
    volume: float
    shuffle: bool
    repeat: str
    current_entry_id: str | None
    current_track_id: str | None
    queue: tuple[Entry, ...]  # play order
    audio_available: bool
    audio_error: str | None
    normalize: bool
    loudness_target: str
    gain_db: float | None  # normalization gain for the current track; None if off or not measured yet

    def position_now(self, now: float) -> int:
        if self.status != "playing" or not self.audio_available:
            return self.position_ms
        position = self.position_ms + int((now - self.position_at) * 1000)
        return min(position, self.duration_ms) if self.duration_ms else position


class PlayerEngine:
    def __init__(
        self,
        backend: AudioBackend,
        library: Library,
        store: StateStore | None = None,
        *,
        clock: Callable[[], float] = time.monotonic,
        threaded: bool = True,
        rng: random.Random | None = None,
    ):
        self.backend = backend
        self.library = library
        self.store = store
        self.clock = clock
        self._threaded = threaded
        self._rng = rng

        self._queue = PlayQueue(rng)
        self._status = "stopped"
        self._position_ms = 0  # authoritative unless a file is playing in the backend
        self._duration_ms = 0
        self._volume = DEFAULT_VOLUME
        self._normalize = True
        self._loudness_target = DEFAULT_LOUDNESS_TARGET
        self._loaded: str | None = None  # entry id whose file is loaded in the backend

        self._audio_ok = False
        self._audio_error: str | None = None
        self._next_audio_retry = 0.0

        self._version = 0
        self._queue_version = 0
        self._queue_signature: tuple | None = None
        self._queue_tuple: tuple[Entry, ...] = ()
        self._dirty = False
        self._last_save = float("-inf")

        self._commands: stdlib_queue.Queue = stdlib_queue.Queue()
        self._thread: threading.Thread | None = None
        self._snapshot: Snapshot | None = None
        self._closed = False

    # ================= lifecycle =================

    def start(self) -> None:
        self._restore()
        self._open_audio()
        if self._audio_ok and self._status == "playing":
            self._play_current(self._position_ms)
        self._after_change()
        if self._threaded:
            self._thread = threading.Thread(target=self._run, name="player-engine", daemon=True)
            self._thread.start()

    def shutdown(self) -> None:
        """Stop the engine thread, save the state and close the device."""
        if self._thread and self._thread.is_alive():
            self._commands.put(None)
            self._thread.join(timeout=5)
        else:
            self._close()

    def _close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._save(force=True)
        try:
            self.backend.close()
        except Exception:
            logger.exception("Closing the audio device failed")

    def _run(self) -> None:
        next_tick = self.clock()
        while True:
            try:
                item = self._commands.get(timeout=max(0.0, next_tick - self.clock()))
            except stdlib_queue.Empty:
                item = False
            if item is None:
                break
            if item:
                self._execute(*item)
            if self.clock() >= next_tick:
                self.tick()
                next_tick = self.clock() + ENGINE_TICK_S
        self._close()

    def _execute(self, fn, args, future: Future) -> None:
        if not future.set_running_or_notify_cancel():
            return
        try:
            future.set_result(fn(*args))
        except CommandError as e:
            future.set_exception(e)
        except Exception as e:
            logger.exception(f"Command {fn.__name__} failed")
            future.set_exception(e)
        finally:
            self._after_change()

    def _call(self, fn, *args):
        """Run fn on the engine thread and return its result (or raise its exception)."""
        if not self._threaded or threading.current_thread() is self._thread:
            try:
                return fn(*args)
            finally:
                self._after_change()
        if not (self._thread and self._thread.is_alive()):
            raise CommandError("The player is not running", 503)
        future: Future = Future()
        self._commands.put((fn, args, future))
        return future.result(timeout=COMMAND_TIMEOUT_S)

    # ================= reading =================

    def snapshot(self) -> Snapshot:
        return self._snapshot

    # ================= commands (public, thread-safe) =================

    def toggle(self) -> None:
        self._call(self._toggle)

    def play(self) -> None:
        self._call(self._resume)

    def pause(self) -> None:
        self._call(self._pause)

    def stop(self) -> None:
        self._call(self._stop)

    def next(self) -> None:
        self._call(self._next)

    def previous(self) -> None:
        self._call(self._previous)

    def seek(self, position_ms: int) -> None:
        self._call(self._seek, position_ms)

    def set_volume(self, volume: float) -> None:
        self._call(self._set_volume, volume)

    def set_shuffle(self, enabled: bool | None = None) -> bool:
        return self._call(self._set_shuffle, enabled)

    def set_repeat(self, mode: str | None = None) -> str:
        return self._call(self._set_repeat, mode)

    def play_track(self, track_id: str) -> None:
        self._call(self._play_track, track_id)

    def play_entry(self, entry_id: str) -> None:
        self._call(self._play_entry, entry_id)

    def play_all(self, shuffle: bool = False) -> int:
        return self._call(self._play_all, shuffle)

    def replace_queue(self, track_ids: list[str], start_index: int = 0) -> None:
        self._call(self._replace_queue, track_ids, start_index)

    def add_to_queue(self, track_ids: list[str], play_next: bool = False) -> list[Entry]:
        return self._call(self._add_to_queue, track_ids, play_next)

    def remove_from_queue(self, entry_id: str) -> None:
        self._call(self._remove_from_queue, entry_id)

    def clear_queue(self) -> None:
        self._call(self._clear_queue)

    def update_settings(self, normalize: bool | None = None, loudness_target: str | None = None) -> None:
        self._call(self._update_settings, normalize, loudness_target)

    def loudness_measured(self, track_id: str) -> None:
        """Called by the loudness analyzer; re-levels the current track if it was the one measured."""
        self._call(self._loudness_measured, track_id)

    def library_changed(self) -> None:
        """Call after a rescan, so clients refresh track details shown in the queue."""
        self._call(self._library_changed)

    # ================= command implementations (engine thread only) =================

    def _toggle(self) -> None:
        if self._status == "playing":
            self._pause()
        else:
            self._resume()

    def _resume(self) -> None:
        if self._status == "playing":
            return
        if self._status == "paused" and self._loaded and self._audio_ok:
            self.backend.resume()
            self._status = "playing"
            return
        # Nothing loaded: after a restart, a seek while paused, a stop or the end of the queue.
        if self._queue.current() is None and self._queue.rewind() is None:
            raise CommandError("The queue is empty. Add something from the library.")
        self._play_current(self._position_ms if self._status == "paused" else 0)

    def _pause(self) -> None:
        if self._status != "playing":
            return
        if self._loaded and self._audio_ok:
            self._position_ms = self.backend.position_ms()
            self.backend.pause()
        self._status = "paused"

    def _stop(self, rewind: bool = False) -> None:
        if self._audio_ok:
            self.backend.stop()
        self._loaded = None
        self._status = "stopped"
        self._position_ms = 0
        if rewind:
            self._queue.rewind()

    def _next(self) -> None:
        if self._queue.next(manual=True) is None:
            if not len(self._queue):
                raise CommandError("The queue is empty.")
            self._stop(rewind=True)  # end of the queue
            return
        self._play_current(0)

    def _previous(self) -> None:
        if self._queue.current() is None:
            raise CommandError("The queue is empty.")
        if self._current_position() <= RESTART_THRESHOLD_MS:
            self._queue.previous()
        self._play_current(0)

    def _seek(self, position_ms: int) -> None:
        if self._queue.current() is None or self._status == "stopped":
            raise CommandError("Nothing is playing.")
        if self._duration_ms:
            position_ms = min(position_ms, self._duration_ms)
        position_ms = max(0, position_ms)

        if self._status == "playing" and self._loaded and self._audio_ok:
            if not self.backend.seek(position_ms):
                raise CommandError("Seeking isn't supported for this file's format.")
            return
        # Paused (or no device): remember it; resuming plays from here.
        if self._loaded and self._audio_ok:
            self.backend.stop()
        self._loaded = None
        self._position_ms = position_ms

    def _set_volume(self, volume: float) -> None:
        self._volume = min(1.0, max(0.0, float(volume)))
        self._apply_volume()

    def _update_settings(self, normalize: bool | None, loudness_target: str | None) -> None:
        if loudness_target is not None and loudness_target not in LOUDNESS_TARGETS:
            raise CommandError(f"loudness_target must be one of: {', '.join(LOUDNESS_TARGETS)}.", 400)
        if normalize is not None:
            self._normalize = normalize
        if loudness_target is not None:
            self._loudness_target = loudness_target
        self._apply_volume()

    def _loudness_measured(self, track_id: str) -> None:
        if self._queue.current() and self._queue.current().track_id == track_id:
            self._apply_volume()

    def _set_shuffle(self, enabled: bool | None) -> bool:
        self._queue.set_shuffle(not self._queue.shuffle if enabled is None else enabled)
        return self._queue.shuffle

    def _set_repeat(self, mode: str | None) -> str:
        if mode is None:
            return self._queue.cycle_repeat()
        if mode not in REPEAT_MODES:
            raise CommandError(f"Repeat must be one of: {', '.join(REPEAT_MODES)}.", 400)
        self._queue.set_repeat(mode)
        return mode

    def _play_track(self, track_id: str) -> None:
        """Play a library track without losing the queue: it's inserted after the current entry."""
        self._require_tracks([track_id])
        current = self._queue.current()
        if current is None or current.track_id != track_id:
            entry = self._queue.insert_next(track_id)
            self._queue.jump(entry.id)
        self._play_current(0)

    def _play_entry(self, entry_id: str) -> None:
        if not self._queue.jump(entry_id):
            raise CommandError("That queue entry no longer exists.", 404)
        self._play_current(0)

    def _play_all(self, shuffle: bool) -> int:
        track_ids = [t.id for t in self.library.tracks()]
        if not track_ids:
            raise CommandError("The library is empty.")
        self._queue.replace(track_ids, start=None if shuffle else 0, shuffle=shuffle)
        self._play_current(0)
        return len(track_ids)

    def _replace_queue(self, track_ids: list[str], start_index: int) -> None:
        self._require_tracks(track_ids)
        if track_ids and not 0 <= start_index < len(track_ids):
            raise CommandError("index is out of range.", 400)
        self._queue.replace(track_ids, start_index)
        if track_ids:
            self._play_current(0)
        else:
            self._stop()

    def _add_to_queue(self, track_ids: list[str], play_next: bool) -> list[Entry]:
        self._require_tracks(track_ids)
        if not track_ids:
            return []
        was_empty = self._queue.current() is None
        if play_next and not was_empty:
            # Inserting in reverse keeps the given order right after the current entry.
            return [self._queue.insert_next(t) for t in reversed(track_ids)][::-1]
        added = self._queue.add(track_ids)
        if was_empty:
            # Something to play now; don't carry over a position from an older track.
            self._queue.jump(added[0].id)
            self._stop()
        return added

    def _remove_from_queue(self, entry_id: str) -> None:
        was_current = self._queue.remove(entry_id)
        if was_current is None:
            raise CommandError("That queue entry no longer exists.", 404)
        if not was_current:
            return
        # The current entry is gone: whatever took its place plays (or waits) instead.
        if self._status == "playing" and self._queue.current() is not None:
            self._play_current(0)
        else:
            self._stop(rewind=self._queue.current() is None)

    def _clear_queue(self) -> None:
        self._stop()
        self._queue.clear()

    def _library_changed(self) -> None:
        self._queue_signature = None  # forces a new queue_version

    # ================= playback helpers =================

    def _require_tracks(self, track_ids: list[str]) -> None:
        missing = [t for t in track_ids if t not in self.library]
        if missing:
            shown = ", ".join(missing[:3]) + ("…" if len(missing) > 3 else "")
            raise CommandError(f"Not in the library: {shown}", 404)

    def _play_current(self, position_ms: int) -> None:
        """Start the current entry at position_ms. Unplayable entries are skipped."""
        for _ in range(max(1, len(self._queue))):
            entry = self._queue.current()
            if entry is None:
                self._stop(rewind=True)
                return
            try:
                self._start(entry, position_ms)
                return
            except BackendError as e:
                logger.warning(f"Skipping {entry.track_id}: {e}")
                position_ms = 0
                if self._queue.next(manual=True) is None:
                    break
        self._stop(rewind=True)
        raise CommandError("Couldn't play anything: the files are missing or unreadable.")

    def _start(self, entry: Entry, position_ms: int) -> None:
        path = self.library.path_for(entry.track_id)
        if path is None:
            raise BackendError("file is missing")
        track = self.library.get(entry.track_id)
        self._duration_ms = track.duration_ms if track else 0
        self._position_ms = position_ms
        self._status = "playing"
        self._loaded = None
        if not self._audio_ok:
            return  # starts once the device is back
        self.backend.load(path)
        self._loaded = entry.id
        self._apply_volume()  # this track's normalization gain
        self.backend.play(position_ms)

    def _gain_db(self) -> float | None:
        """Normalization gain for the current track: target loudness minus its measured loudness."""
        if not self._normalize:
            return None
        current = self._queue.current()
        track = self.library.get(current.track_id) if current else None
        if track is None or track.loudness is None:
            return None
        gain = LOUDNESS_TARGETS[self._loudness_target] - track.loudness
        return round(min(MAX_BOOST_DB, max(MAX_CUT_DB, gain)), 1)

    def _apply_volume(self) -> None:
        """Output volume = the user's volume, scaled by the track's gain.

        The mixer can't amplify past 1.0, so a quiet track is lifted only as far as the
        user's volume leaves room for.
        """
        if not self._audio_ok:
            return
        gain = self._gain_db()
        factor = 10 ** (gain / 20) if gain is not None else 1.0
        self.backend.set_volume(min(1.0, self._volume * factor))

    def _current_position(self) -> int:
        if self._status == "playing" and self._loaded and self._audio_ok:
            return self.backend.position_ms()
        return self._position_ms

    # ================= ticks =================

    def tick(self) -> None:
        """Periodic work; on the engine thread (or the caller's, when not threaded)."""
        try:
            now = self.clock()
            if not self._audio_ok and now >= self._next_audio_retry:
                if self._open_audio():
                    if self._status == "playing":
                        self._play_current(self._position_ms)
                    self._mark_changed()

            if self._status == "playing" and self._loaded and self._audio_ok and self.backend.is_finished():
                self._track_finished()
                self._mark_changed()

            self._maybe_save(now)
        except CommandError as e:
            logger.warning(str(e))
        except Exception:
            logger.exception("Engine tick failed")
        finally:
            self._publish()

    def _track_finished(self) -> None:
        if self._queue.next(manual=False) is None:
            self._stop(rewind=True)  # end of the queue: stop and get ready to start over
        else:
            self._play_current(0)

    def _open_audio(self) -> bool:
        try:
            self.backend.open()
        except AudioUnavailableError as e:
            if self._audio_error != str(e):
                logger.warning(f"Audio device unavailable ({e}); retrying every {AUDIO_RETRY_S:.0f}s")
            self._audio_ok, self._audio_error = False, str(e)
            self._next_audio_retry = self.clock() + AUDIO_RETRY_S
            return False
        if self._audio_error:
            logger.info("Audio device is back")
        self._audio_ok, self._audio_error = True, None
        self._apply_volume()
        return True

    # ================= state, snapshots, persistence =================

    def _mark_changed(self) -> None:
        self._version += 1
        self._dirty = True

    def _after_change(self) -> None:
        self._mark_changed()
        self._publish()

    def _publish(self) -> None:
        signature = self._queue.signature()
        if signature != self._queue_signature:
            self._queue_signature = signature
            self._queue_version += 1
            self._queue_tuple = tuple(self._queue.entries())
            self._version += 1

        current = self._queue.current()
        self._snapshot = Snapshot(
            version=self._version,
            queue_version=self._queue_version,
            status=self._status,
            position_ms=self._current_position(),
            position_at=self.clock(),
            duration_ms=self._duration_ms,
            volume=self._volume,
            shuffle=self._queue.shuffle,
            repeat=self._queue.repeat,
            current_entry_id=current.id if current else None,
            current_track_id=current.track_id if current else None,
            queue=self._queue_tuple,
            audio_available=self._audio_ok,
            audio_error=self._audio_error,
            normalize=self._normalize,
            loudness_target=self._loudness_target,
            gain_db=self._gain_db(),
        )

    def _state_dict(self) -> dict:
        return {
            "volume": self._volume,
            "normalize": self._normalize,
            "loudness_target": self._loudness_target,
            "status": self._status,
            "position_ms": self._current_position(),
            "queue": self._queue.to_dict(),
        }

    def _maybe_save(self, now: float) -> None:
        elapsed = now - self._last_save
        if (self._dirty and elapsed >= SAVE_DEBOUNCE_S) or (
            self._status == "playing" and elapsed >= POSITION_SAVE_INTERVAL_S
        ):
            self._save()

    def _save(self, force: bool = False) -> None:
        if self.store is None:
            return
        if force or self._dirty or self._status == "playing":
            self.store.save(self._state_dict())
            self._dirty = False
            self._last_save = self.clock()

    def _restore(self) -> None:
        data = self.store.load() if self.store else None
        if not data:
            return
        self._queue = PlayQueue.from_dict(data.get("queue") or {}, self._rng)
        volume = data.get("volume")
        if isinstance(volume, (int, float)) and not isinstance(volume, bool):
            self._volume = min(1.0, max(0.0, float(volume)))
        if isinstance(data.get("normalize"), bool):
            self._normalize = data["normalize"]
        if data.get("loudness_target") in LOUDNESS_TARGETS:
            self._loudness_target = data["loudness_target"]
        status = data.get("status")
        if status in STATUSES and self._queue.current() is not None:
            self._status = status
        position = data.get("position_ms")
        if self._status != "stopped" and isinstance(position, int) and position > 0:
            self._position_ms = position
        current = self._queue.current()
        track = self.library.get(current.track_id) if current else None
        self._duration_ms = track.duration_ms if track else 0
        logger.info(
            f"Restored: {len(self._queue)} queued, {self._status}, volume {round(self._volume * 100)}%"
        )
