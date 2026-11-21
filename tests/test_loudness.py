import math
import time
import wave

import numpy as np
import pytest

from headless_music_player.app import create_app
from headless_music_player.audio.fake import FakeBackend
from headless_music_player.config import LOUDNESS_TARGETS, MAX_BOOST_DB, Settings
from headless_music_player.library import Library
from headless_music_player.library.analyzer import LoudnessAnalyzer
from headless_music_player.library.loudness import LoudnessError, integrated_loudness, measure

from .conftest import ids, make_wav


def sine(path, amplitude, seconds=5.0, freq=997, rate=44_100, silence_after=0.0):
    t = np.arange(int(rate * seconds)) / rate
    x = amplitude * np.sin(2 * np.pi * freq * t)
    x = np.concatenate([x, np.zeros(int(rate * silence_after))])
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes((x * 32767).astype("<i2").tobytes())
    return path


# ---------- measurement ----------


@pytest.mark.parametrize("amplitude", [1.0, 0.1, 0.02])
def test_matches_the_bs1770_reference(tmp_path, amplitude):
    """A 997 Hz sine at full scale measures -3.01 LUFS."""
    expected = -3.01 + 20 * math.log10(amplitude)
    assert measure(sine(tmp_path / "s.wav", amplitude)) == pytest.approx(expected, abs=0.1)


def test_other_sample_rates_measure_the_same(tmp_path):
    assert measure(sine(tmp_path / "s.wav", 0.1, rate=22_050)) == pytest.approx(-23.01, abs=0.15)


def test_silence_is_gated_out(tmp_path):
    """20 s of silence after 3 s of tone barely moves the result (ungated it'd drop ~9 dB).

    The few 400 ms blocks straddling the end are partly silent and still pass the gates,
    as BS.1770 intends, hence the small difference.
    """
    tone = measure(sine(tmp_path / "a.wav", 0.1, seconds=3))
    tone_then_silence = measure(sine(tmp_path / "b.wav", 0.1, seconds=3, silence_after=20))
    assert tone_then_silence == pytest.approx(tone, abs=0.5)


def test_silent_and_very_short_files_have_no_loudness(tmp_path):
    assert measure(make_wav(tmp_path / "silent.wav", 3000)) is None
    assert measure(sine(tmp_path / "short.wav", 0.5, seconds=0.2)) is None
    assert integrated_loudness([]) is None


def test_unreadable_files_raise(tmp_path):
    bad = tmp_path / "bad.mp3"
    bad.write_bytes(b"not audio at all" * 100)
    with pytest.raises(LoudnessError):
        measure(bad)


# ---------- library and analyzer ----------


@pytest.fixture
def levels_dir(tmp_path):
    d = tmp_path / "music"
    sine(d / "Loud.wav", 0.8)  # about -5 LUFS
    sine(d / "Quiet.wav", 0.02)  # about -37 LUFS
    make_wav(d / "Silent.wav", 2000)
    return d


def run_analyzer(library, **kwargs):
    analyzer = LoudnessAnalyzer(library, **kwargs)
    analyzer.start()
    deadline = time.monotonic() + 10
    while library.unanalyzed() and time.monotonic() < deadline:
        time.sleep(0.02)
    analyzer.stop()
    return analyzer


def test_analyzer_measures_everything_and_caches_it(tmp_path, levels_dir):
    lib = Library(levels_dir, tmp_path / "cache")
    lib.scan()
    version = lib.version
    measured = []
    run_analyzer(lib, on_measured=measured.append)

    assert lib.analysis_progress() == (3, 3)
    assert lib.get("Loud.wav").loudness == pytest.approx(-4.95, abs=0.2)
    assert lib.get("Quiet.wav").loudness == pytest.approx(-36.99, abs=0.2)
    assert lib.get("Silent.wav").loudness is None and lib.get("Silent.wav").analyzed
    assert sorted(measured) == ["Loud.wav", "Quiet.wav", "Silent.wav"]
    assert lib.version == version  # the library list doesn't need re-rendering

    again = Library(levels_dir, tmp_path / "cache")
    again.load_cache()
    again.scan()
    assert again.unanalyzed() == []
    assert again.get("Quiet.wav").loudness == lib.get("Quiet.wav").loudness


def test_priority_tracks_go_first(tmp_path, levels_dir):
    lib = Library(levels_dir, tmp_path / "cache")
    lib.scan()
    analyzer = LoudnessAnalyzer(lib, priority=lambda: ["Silent.wav", "Quiet.wav"])
    assert analyzer._next_track().id == "Silent.wav"
    analyzer.measure_one(lib.get("Silent.wav"))
    assert analyzer._next_track().id == "Quiet.wav"


def test_a_file_that_changed_while_measured_is_measured_again(tmp_path, levels_dir):
    lib = Library(levels_dir, tmp_path / "cache")
    lib.scan()
    stale = lib.get("Loud.wav")
    sine(levels_dir / "Loud.wav", 0.5, seconds=6)
    lib.scan()
    assert lib.set_loudness(stale, -5.0) is False
    assert not lib.get("Loud.wav").analyzed


# ---------- engine ----------


def factor(db):
    return 10 ** (db / 20)


def test_gain_is_applied_per_track(engine, library, backend):
    normal = LOUDNESS_TARGETS["normal"]
    order = ids(library)
    library.set_loudness(library.get(order[0]), normal + 6)  # 6 dB too loud
    library.set_loudness(library.get(order[1]), normal - 4)  # 4 dB too quiet
    engine.set_volume(0.5)
    engine.play_all()
    assert engine.snapshot().gain_db == -6.0
    assert backend.volume == pytest.approx(0.5 * factor(-6))
    engine.next()
    assert engine.snapshot().gain_db == 4.0
    assert backend.volume == pytest.approx(0.5 * factor(4))
    engine.next()  # not measured yet: plays at the user's volume
    assert engine.snapshot().gain_db is None
    assert backend.volume == pytest.approx(0.5)


def test_boost_is_limited_by_volume_and_max(engine, library, backend):
    library.set_loudness(library.get(ids(library)[0]), -60.0)
    engine.set_volume(0.9)
    engine.play_all()
    assert engine.snapshot().gain_db == MAX_BOOST_DB
    assert backend.volume == 1.0  # can't go past full scale


def test_turning_it_off_and_changing_the_target(engine, library, backend):
    library.set_loudness(library.get(ids(library)[0]), -20.0)
    engine.set_volume(0.4)
    engine.play_all()
    engine.update_settings(normalize=False)
    assert backend.volume == pytest.approx(0.4) and engine.snapshot().gain_db is None
    engine.update_settings(normalize=True, loudness_target="quiet")
    assert engine.snapshot().gain_db == LOUDNESS_TARGETS["quiet"] + 20


def test_measuring_the_playing_track_relevels_it(engine, library, backend):
    engine.set_volume(0.5)
    engine.play_all()
    assert backend.volume == pytest.approx(0.5)
    track = library.get(engine.snapshot().current_track_id)
    library.set_loudness(track, LOUDNESS_TARGETS["normal"] + 10)
    engine.loudness_measured(track.id)
    assert backend.volume == pytest.approx(0.5 * factor(-10))


def test_settings_survive_a_restart(make_engine, clock):
    first = make_engine()
    first.update_settings(normalize=False, loudness_target="loud")
    first.shutdown()
    snap = make_engine(FakeBackend(clock)).snapshot()
    assert (snap.normalize, snap.loudness_target) == (False, "loud")


def test_unknown_target_is_rejected(engine):
    from headless_music_player.engine import CommandError

    with pytest.raises(CommandError):
        engine.update_settings(loudness_target="deafening")


# ---------- API and page ----------


@pytest.fixture
def client(tmp_path, levels_dir):
    app = create_app(Settings(music_dir=levels_dir, runtime_dir=tmp_path / "data"), backend=FakeBackend(time.monotonic))
    yield app.test_client()
    app.extensions["player"].shutdown()


def test_settings_api(client):
    settings = client.get("/api/settings").get_json()
    assert settings["normalize"] is True and settings["loudness_target"] == "normal"
    assert settings["analysis"]["total"] == 3

    updated = client.post("/api/settings", json={"normalize": False, "loudness_target": "quiet"}).get_json()
    assert (updated["normalize"], updated["loudness_target"]) == (False, "quiet")
    assert client.get("/api/state").get_json()["normalization"]["enabled"] is False

    assert client.post("/api/settings", json={"loudness_target": "max"}).status_code == 400
    assert client.post("/api/settings", json={"normalize": "yes"}).status_code == 400


def test_settings_page_renders(client):
    html = client.get("/settings").get_data(as_text=True)
    assert "Volume normalization" in html and 'id="setting-normalize"' in html
    assert 'href="/settings"' in client.get("/").get_data(as_text=True)
