"""A backend with no sound, driven by an injectable clock. For tests and SDL-free development."""

from collections.abc import Callable
from pathlib import Path

from .base import AudioUnavailableError, BackendError


class FakeBackend:
    def __init__(
        self,
        clock: Callable[[], float],
        durations_ms: dict[str, int] | None = None,
        default_duration_ms: int = 60_000,
        unavailable_times: int = 0,
        seekable: bool = True,
        devices: list[str] | None = None,
    ):
        self.clock = clock
        self.durations_ms = durations_ms or {}
        self.default_duration_ms = default_duration_ms
        self.unavailable_times = unavailable_times  # open() fails this many times first
        self.seekable = seekable
        self.devices = devices if devices is not None else ["Built-in Audio", "USB DAC"]  # plugged in now
        self.device: str | None = None
        self.is_open = False
        self.volume = None
        self.loaded: Path | None = None
        self.calls: list[str] = []
        self._playing = self._paused = False
        self._base_ms = 0
        self._since = 0.0

    def open(self, device: str | None = None) -> None:
        if self.unavailable_times > 0:
            self.unavailable_times -= 1
            raise AudioUnavailableError("no sound card (fake)")
        if device is not None and device not in self.devices:
            raise AudioUnavailableError(f"{device} isn't connected")
        self.is_open, self.device = True, device
        self.calls.append(f"open {device or 'default'}")

    def output_devices(self) -> list[str]:
        return list(self.devices)

    def close(self) -> None:
        self.is_open = False
        self._playing = self._paused = False

    def load(self, path: Path) -> None:
        if "corrupt" in path.name:
            raise BackendError(f"Can't load {path.name}")
        self.loaded = path
        self._playing = self._paused = False
        self.calls.append(f"load {path.name}")

    @property
    def duration_ms(self) -> int:
        return self.durations_ms.get(self.loaded.name, self.default_duration_ms) if self.loaded else 0

    def play(self, start_ms: int = 0) -> None:
        self._base_ms, self._since = start_ms, self.clock()
        self._playing, self._paused = True, False
        self.calls.append(f"play {start_ms}")

    def pause(self) -> None:
        self._base_ms = self.position_ms()
        self._paused = True
        self.calls.append("pause")

    def resume(self) -> None:
        self._since = self.clock()
        self._paused = False
        self.calls.append("resume")

    def stop(self) -> None:
        self._playing = self._paused = False
        self.calls.append("stop")

    def seek(self, position_ms: int) -> bool:
        if not self.seekable:
            return False
        self._base_ms, self._since = position_ms, self.clock()
        self.calls.append(f"seek {position_ms}")
        return True

    def set_volume(self, volume: float) -> None:
        self.volume = volume

    @property
    def playing(self) -> bool:
        return self._playing and not self._paused

    def position_ms(self) -> int:
        if not self._playing:
            return 0
        if self._paused:
            return self._base_ms
        return min(self.duration_ms, int(self._base_ms + (self.clock() - self._since) * 1000))

    def is_finished(self) -> bool:
        return self.playing and self.position_ms() >= self.duration_ms
