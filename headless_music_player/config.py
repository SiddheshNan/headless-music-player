"""Paths and settings, overridable through HMP_* environment variables."""

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Everything written at runtime lives here: the saved state and the cover art cache.
RUNTIME_DIR = Path(os.environ.get("HMP_RUNTIME_DIR", PROJECT_ROOT / "runtime"))
MUSIC_DIR = Path(os.environ.get("HMP_MUSIC_DIR", RUNTIME_DIR / "music"))
STATE_FILE = RUNTIME_DIR / "state.json"
COVERS_DIR = RUNTIME_DIR / "cache" / "covers"

HOST = os.environ.get("HMP_HOST", "0.0.0.0")
PORT = int(os.environ.get("HMP_PORT", "8000"))

SUPPORTED_FORMATS = (".mp3", ".wav", ".ogg", ".flac")
DEFAULT_VOLUME = 0.5

# Mono output is intentional: the player drives a single speaker.
MIXER_SETTINGS = {"frequency": 44100, "size": -16, "channels": 1, "buffer": 2048}

# Position changes every second while playing; writing it that often wears out SD cards.
POSITION_SAVE_INTERVAL_S = 5


def ensure_directories():
    for d in (RUNTIME_DIR, MUSIC_DIR, COVERS_DIR):
        d.mkdir(parents=True, exist_ok=True)
