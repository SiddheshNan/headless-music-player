import time

import pytest

from headless_music_player.app import create_app
from headless_music_player.audio.fake import FakeBackend
from headless_music_player.config import Settings


@pytest.fixture
def client(tmp_path, music_dir):
    settings = Settings(music_dir=music_dir, runtime_dir=tmp_path / "data")
    app = create_app(settings, backend=FakeBackend(time.monotonic))
    yield app.test_client()
    app.extensions["player"].shutdown()


def error(response):
    return response.status_code, response.get_json()["error"]


def test_pages_render(client):
    assert client.get("/").status_code == 200
    assert client.get("/partials/queue").status_code == 200
    assert client.get("/partials/library").status_code == 200


def test_health(client):
    assert client.get("/api/health").get_json()["status"] == "ok"


def test_play_all_and_state(client):
    state = client.post("/api/queue/play-all", json={}).get_json()
    assert state["status"] == "playing"
    assert state["current"]["track"]["title"] == "Four"
    assert state["queue"] == {"length": 4, "index": 0}
    assert "original_order" not in state

    queue = client.get("/api/queue").get_json()
    assert [e["track"]["title"] for e in queue["entries"]] == ["Four", "One", "Three", "Two"]


def test_queue_add_remove(client):
    added = client.post("/api/queue/add", json={"track_ids": ["A - One.wav", "A - One.wav"]}).get_json()
    assert len(added["entry_ids"]) == 2
    state = client.delete(f"/api/queue/{added['entry_ids'][1]}").get_json()
    assert state["queue"]["length"] == 1


@pytest.mark.parametrize(
    "method, path, body, status",
    [
        ("post", "/api/playback/volume", {"volume": "loud"}, 400),
        ("post", "/api/playback/volume", {"volume": 2}, 400),
        ("post", "/api/playback/volume", {"volume": True}, 400),
        ("post", "/api/playback/volume", {}, 400),
        ("post", "/api/playback/seek", {"position_ms": "10"}, 400),
        ("post", "/api/playback/seek", {"position_ms": -1}, 400),
        ("post", "/api/playback/seek", {"position_ms": 1000}, 409),
        ("post", "/api/queue", {"track_ids": "A - One.wav"}, 400),
        ("post", "/api/queue", {"track_ids": ["A - One.wav"], "index": 5}, 400),
        ("post", "/api/queue/add", {"track_ids": ["missing.mp3"]}, 404),
        ("post", "/api/queue/repeat", {"mode": "forever"}, 400),
        ("post", "/api/queue/shuffle", {"enabled": "yes"}, 400),
        ("post", "/api/playback/play", {"track_id": "A - One.wav", "entry_id": "x"}, 400),
        ("post", "/api/playback/toggle", None, 409),
        ("delete", "/api/queue/nope", None, 404),
        ("get", "/api/nope", None, 404),
        ("get", "/api/library/covers/..%2Fstate.json", None, 404),
    ],
)
def test_bad_requests_get_clear_errors(client, method, path, body, status):
    response = getattr(client, method)(path, json=body) if body is not None else getattr(client, method)(path)
    code, message = error(response)
    assert code == status and message


def test_body_must_be_an_object(client):
    response = client.post("/api/playback/volume", data="[1]", content_type="application/json")
    assert error(response)[0] == 400


def test_rescan(client, music_dir):
    from .conftest import make_wav

    make_wav(music_dir / "New" / "E - Five.wav")
    result = client.post("/api/library/rescan").get_json()
    assert result["total"] == 5 and result["added"] == 1
    titles = [t["title"] for t in client.get("/api/library").get_json()["tracks"]]
    assert "Five" in titles
