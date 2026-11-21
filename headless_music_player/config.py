"""Settings, read from HMP_* environment variables, and fixed tuning constants."""

import os
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

SUPPORTED_EXTENSIONS = (".mp3", ".flac", ".ogg", ".wav")
DEFAULT_VOLUME = 0.5

# Mono output is intentional: the player drives a single speaker.
# The larger buffer avoids crackling on a Raspberry Pi.
MIXER_SETTINGS = {"frequency": 44100, "size": -16, "channels": 1, "buffer": 2048}

ENGINE_TICK_S = 0.25  # how often the engine checks for the end of a track
AUDIO_RETRY_S = 5.0  # how often to retry opening a missing sound card
SAVE_DEBOUNCE_S = 1.0  # changes are written at most this often
POSITION_SAVE_INTERVAL_S = 5.0  # while playing, the position is written this often
RESTART_THRESHOLD_MS = 3000  # "previous" past this point restarts the track instead


@dataclass(frozen=True)
class Settings:
    music_dir: Path
    runtime_dir: Path
    host: str = "0.0.0.0"
    port: int = 8000

    @property
    def state_file(self) -> Path:
        return self.runtime_dir / "state.json"

    @property
    def cache_dir(self) -> Path:
        return self.runtime_dir / "cache"

    @classmethod
    def from_env(cls) -> "Settings":
        runtime_dir = Path(os.environ.get("HMP_RUNTIME_DIR", PROJECT_ROOT / "runtime"))
        return cls(
            music_dir=Path(os.environ.get("HMP_MUSIC_DIR", runtime_dir / "music")),
            runtime_dir=runtime_dir,
            host=os.environ.get("HMP_HOST", "0.0.0.0"),
            port=int(os.environ.get("HMP_PORT", "8000")),
        )

    def ensure_directories(self) -> None:
        for d in (self.runtime_dir, self.music_dir, self.cache_dir):
            d.mkdir(parents=True, exist_ok=True)
