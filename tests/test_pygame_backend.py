"""The real pygame backend, on SDL's dummy driver (no sound card needed)."""

import os
import time

import pytest

from .conftest import make_wav

pytest.importorskip("pygame")


@pytest.fixture
def backend(monkeypatch):
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    from headless_music_player.audio.pygame_backend import PygameBackend

    b = PygameBackend()
    b.open()
    yield b
    b.close()


def test_position_advances_and_freezes_while_paused(backend, tmp_path):
    backend.load(make_wav(tmp_path / "t.wav", 5000))
    backend.play()
    time.sleep(0.3)
    backend.pause()
    paused_at = backend.position_ms()
    assert 100 <= paused_at <= 1000
    time.sleep(0.3)
    assert backend.position_ms() == paused_at
    assert not backend.is_finished()  # paused is not finished
    backend.resume()
    time.sleep(0.2)
    assert backend.position_ms() > paused_at


def test_finishes(backend, tmp_path):
    backend.load(make_wav(tmp_path / "short.wav", 200))
    backend.play()
    deadline = time.monotonic() + 3
    while not backend.is_finished() and time.monotonic() < deadline:
        time.sleep(0.05)
    assert backend.is_finished()


def test_unloadable_file_raises_backend_error(backend, tmp_path):
    from headless_music_player.audio import BackendError

    bad = tmp_path / "bad.mp3"
    bad.write_bytes(os.urandom(64))
    with pytest.raises(BackendError):
        backend.load(bad)


def test_lists_outputs_and_refuses_a_missing_one(monkeypatch):
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    from headless_music_player.audio import AudioUnavailableError
    from headless_music_player.audio.pygame_backend import PygameBackend

    b = PygameBackend()
    assert isinstance(b.output_devices(), list)  # works before open() too
    with pytest.raises(AudioUnavailableError):
        b.open("No Such DAC")
    b.open()
    assert isinstance(b.output_devices(), list)
    b.close()
