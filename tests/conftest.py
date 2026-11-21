import random
import wave
from pathlib import Path

import pytest

from headless_music_player.audio.fake import FakeBackend
from headless_music_player.engine import PlayerEngine
from headless_music_player.library import Library
from headless_music_player.store import StateStore

TRACK_MS = 60_000


class Clock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self) -> float:
        return self.t

    def advance(self, seconds: float) -> None:
        self.t += seconds


def make_wav(path: Path, duration_ms: int = TRACK_MS) -> Path:
    """A silent WAV; 1 kHz, 8-bit keeps a minute at 60 KB."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(1)
        w.setframerate(1000)
        w.writeframes(b"\x80" * duration_ms)
    return path


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def music_dir(tmp_path):
    d = tmp_path / "music"
    for name in ("A - One.wav", "B - Two.wav", "C - Three.wav", "D - Four.wav"):
        make_wav(d / name)
    return d


@pytest.fixture
def library(tmp_path, music_dir):
    lib = Library(music_dir, tmp_path / "data" / "cache")
    lib.scan()
    return lib


@pytest.fixture
def store(tmp_path):
    return StateStore(tmp_path / "data" / "state.json")


@pytest.fixture
def backend(clock):
    return FakeBackend(clock)


@pytest.fixture
def make_engine(library, store, clock):
    def make(backend=None, **kwargs):
        engine = PlayerEngine(
            backend or FakeBackend(clock), library, store, clock=clock, threaded=False, rng=random.Random(7), **kwargs
        )
        engine.start()
        return engine

    return make


@pytest.fixture
def engine(make_engine, backend):
    return make_engine(backend)


def ids(library):
    """Track ids in library order: One, Two, Three, Four sort as Four, One, Three, Two."""
    return [t.id for t in library.tracks()]
