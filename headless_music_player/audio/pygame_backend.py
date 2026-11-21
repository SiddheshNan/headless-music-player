"""Playback through pygame's mixer (SDL_mixer), which outputs through ALSA on the Pi."""

import logging
import os
from pathlib import Path

from ..config import MIXER_SETTINGS
from .base import AudioUnavailableError, BackendError

logger = logging.getLogger(__name__)

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
# Otherwise SDL takes over SIGTERM (when nothing else handles it) and ignores it,
# so `kill` or `docker stop` without gunicorn couldn't stop the player.
os.environ.setdefault("SDL_NO_SIGNAL_HANDLERS", "1")


class PygameBackend:
    def __init__(self, settings: dict | None = None):
        self._settings = settings or MIXER_SETTINGS
        self._mixer = None
        self._error = Exception
        self._started = False  # play() was called on the loaded file
        self._paused = False
        self._offset_ms = 0  # get_pos() counts from play(); this maps it to the file position

    def open(self, device: str | None = None) -> None:
        try:
            import pygame
            from pygame import mixer
        except ImportError as e:
            raise AudioUnavailableError(f"pygame is not installed: {e}") from e
        try:
            if device:
                mixer.init(**self._settings, devicename=device)
            else:
                mixer.init(**self._settings)
        except pygame.error as e:
            if device and "no such device" in str(e).lower():
                raise AudioUnavailableError(f"{device} isn't connected") from e
            raise AudioUnavailableError(str(e)) from e
        self._mixer = mixer
        self._error = pygame.error
        logger.info(f"Audio output open: {device or 'system default'} {mixer.get_init()}")

    def output_devices(self) -> list[str]:
        """SDL lists devices only while audio is initialised; open the default briefly if needed."""
        try:
            import pygame
            from pygame import mixer
            from pygame._sdl2 import audio as sdl_audio
        except ImportError:
            return []

        if self._mixer is not None:
            return list(sdl_audio.get_audio_device_names(False))
        try:
            mixer.init(**self._settings)
        except pygame.error:
            return []
        try:
            return list(sdl_audio.get_audio_device_names(False))
        finally:
            mixer.quit()

    def close(self) -> None:
        if self._mixer:
            self._mixer.quit()
            self._mixer = None
        self._started = self._paused = False

    def load(self, path: Path) -> None:
        self._started = self._paused = False
        try:
            self._mixer.music.load(str(path))
        except self._error as e:
            raise BackendError(f"Can't load {path.name}: {e}") from e

    def play(self, start_ms: int = 0) -> None:
        music = self._mixer.music
        try:
            if start_ms > 0:
                music.play(start=start_ms / 1000)
                self._offset_ms = start_ms
            else:
                music.play()
                self._offset_ms = 0
        except self._error:
            # Some formats can't start mid-file; play from the start rather than not at all.
            music.play()
            self._offset_ms = 0
        self._started, self._paused = True, False

    def pause(self) -> None:
        self._mixer.music.pause()
        self._paused = True

    def resume(self) -> None:
        self._mixer.music.unpause()
        self._paused = False

    def stop(self) -> None:
        if self._mixer:
            self._mixer.music.stop()
        self._started = self._paused = False

    def seek(self, position_ms: int) -> bool:
        try:
            self._mixer.music.set_pos(position_ms / 1000)
        except self._error:
            return False
        self._offset_ms = position_ms - max(0, self._mixer.music.get_pos())
        return True

    def set_volume(self, volume: float) -> None:
        if self._mixer:
            self._mixer.music.set_volume(volume)

    def position_ms(self) -> int:
        if not self._started or self._mixer is None:
            return 0
        # get_pos() stops while paused, so this doesn't drift like a wall clock would.
        return max(0, self._offset_ms + max(0, self._mixer.music.get_pos()))

    def is_finished(self) -> bool:
        # get_busy() is also False while paused, hence the flag.
        return self._started and not self._paused and self._mixer is not None and not self._mixer.music.get_busy()
