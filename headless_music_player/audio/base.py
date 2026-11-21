from pathlib import Path
from typing import Protocol


class AudioUnavailableError(Exception):
    """The audio device can't be opened (missing, busy, or not ready yet at boot)."""


class BackendError(Exception):
    """A file couldn't be loaded or played."""


class AudioBackend(Protocol):
    """One track at a time. Only the engine thread calls these methods."""

    def open(self) -> None:
        """Open the device. Raises AudioUnavailableError."""

    def close(self) -> None: ...

    def load(self, path: Path) -> None:
        """Load a file, stopping whatever played. Raises BackendError."""

    def play(self, start_ms: int = 0) -> None:
        """Play the loaded file from start_ms (from the start if the format can't begin mid-file)."""

    def pause(self) -> None: ...

    def resume(self) -> None: ...

    def stop(self) -> None: ...

    def seek(self, position_ms: int) -> bool:
        """Jump within the playing file. False if the format doesn't support it."""

    def set_volume(self, volume: float) -> None: ...

    def position_ms(self) -> int:
        """Position in the loaded file; frozen while paused."""

    def is_finished(self) -> bool:
        """True once a playing (not paused) file has played to its end."""
