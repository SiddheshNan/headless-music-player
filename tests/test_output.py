import time

import pytest

from headless_music_player.app import create_app
from headless_music_player.audio.fake import FakeBackend
from headless_music_player.config import AUDIO_RETRY_S, Settings
from headless_music_player.engine import CommandError


def test_opens_the_system_default_first(engine, backend):
    assert backend.device is None and engine.snapshot().output is None


def test_switching_while_playing_continues_from_the_same_spot(engine, backend, clock):
    engine.play_all()
    clock.advance(30)
    engine.set_output("USB DAC")
    assert backend.device == "USB DAC"
    assert backend.calls[-2:] == ["load " + backend.loaded.name, "play 30000"]
    assert engine.snapshot().status == "playing" and engine.snapshot().output == "USB DAC"


def test_switching_while_paused_stays_paused(engine, backend, clock):
    engine.play_all()
    clock.advance(12)
    engine.pause()
    engine.set_output("USB DAC")
    assert engine.snapshot().status == "paused" and not backend.playing
    engine.toggle()
    assert backend.calls[-1] == "play 12000"


def test_back_to_the_default(engine, backend):
    engine.set_output("USB DAC")
    engine.set_output(None)
    assert backend.device is None and engine.snapshot().output is None


def test_a_device_that_isnt_connected_is_refused(engine, backend):
    with pytest.raises(CommandError) as e:
        engine.set_output("HDMI")
    assert e.value.status == 404
    assert backend.device is None and engine.snapshot().output is None


def test_volume_is_kept_on_the_new_device(engine, backend):
    engine.update_settings(normalize=False)
    engine.set_volume(0.3)
    engine.set_output("USB DAC")
    assert backend.volume == pytest.approx(0.3)


def test_waits_for_a_chosen_device_that_appears_after_boot(make_engine, clock):
    """A USB DAC can show up seconds after the player starts; it waits instead of using another output."""
    first = make_engine()
    first.set_output("USB DAC")
    first.play_all()
    clock.advance(8)
    first.tick()
    first.shutdown()

    backend = FakeBackend(clock, devices=["Built-in Audio"])  # DAC not there yet
    engine = make_engine(backend)
    snap = engine.snapshot()
    assert not snap.audio_available and "USB DAC" in snap.audio_error
    assert snap.output == "USB DAC" and snap.status == "playing"

    backend.devices.append("USB DAC")
    clock.advance(AUDIO_RETRY_S)
    engine.tick()
    assert engine.snapshot().audio_available
    assert backend.device == "USB DAC" and backend.calls[-1] == "play 8000"


# ---------- API and page ----------


@pytest.fixture
def client(tmp_path, music_dir):
    app = create_app(Settings(music_dir=music_dir, runtime_dir=tmp_path / "data"), backend=FakeBackend(time.monotonic))
    yield app.test_client()
    app.extensions["player"].shutdown()


def test_outputs_api(client):
    assert client.get("/api/audio/outputs").get_json() == {"selected": None, "devices": ["Built-in Audio", "USB DAC"]}

    settings = client.post("/api/settings", json={"output": "USB DAC"}).get_json()
    assert settings["audio"] == {"available": True, "error": None, "output": "USB DAC"}
    assert client.get("/api/audio/outputs").get_json()["selected"] == "USB DAC"

    assert client.post("/api/settings", json={"output": None}).get_json()["audio"]["output"] is None
    assert client.post("/api/settings", json={"output": "Nope"}).status_code == 404
    assert client.post("/api/settings", json={"output": 3}).status_code == 400
    assert client.post("/api/settings", json={"output": ""}).status_code == 400


def test_settings_page_lists_outputs(client):
    html = client.get("/settings").get_data(as_text=True)
    assert 'id="setting-output"' in html
    assert '<option value="USB DAC"' in html and "System default" in html
