import io
import time

import pytest

from headless_music_player.app import create_app
from headless_music_player.audio.fake import FakeBackend
from headless_music_player.config import Settings
from headless_music_player.library.uploads import UploadError, safe_filename

from .conftest import make_wav


@pytest.fixture
def app(tmp_path, music_dir):
    settings = Settings(music_dir=music_dir, runtime_dir=tmp_path / "data", max_upload_mb=1)
    app = create_app(settings, backend=FakeBackend(time.monotonic))
    yield app
    app.extensions["player"].shutdown()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def song(tmp_path):
    return make_wav(tmp_path / "src" / "E - Five.wav", 2000).read_bytes()


def upload(client, data: bytes, name: str):
    return client.post("/api/library/upload", data={"file": (io.BytesIO(data), name)}, content_type="multipart/form-data")


def test_upload_adds_the_song_to_the_library(client, music_dir, song):
    response = upload(client, song, "E - Five.wav")
    assert response.status_code == 201
    body = response.get_json()
    assert body == {"track": body["track"], "duplicate": False}
    assert (body["track"]["id"], body["track"]["title"], body["track"]["artist"]) == ("E - Five.wav", "Five", "E")
    assert (music_dir / "E - Five.wav").read_bytes() == song

    titles = [t["title"] for t in client.get("/api/library").get_json()["tracks"]]
    assert "Five" in titles
    # It's playable right away.
    state = client.post("/api/playback/play", json={"track_id": "E - Five.wav"}).get_json()
    assert state["current"]["track"]["title"] == "Five"


def test_uploading_the_same_file_again_is_a_duplicate(client, music_dir, song):
    upload(client, song, "E - Five.wav")
    response = upload(client, song, "E - Five.wav")
    assert response.status_code == 200 and response.get_json()["duplicate"] is True
    assert sorted(p.name for p in music_dir.iterdir()).count("E - Five.wav") == 1


def test_a_different_file_with_the_same_name_gets_a_number(client, music_dir, song, tmp_path):
    upload(client, song, "E - Five.wav")
    other = make_wav(tmp_path / "src" / "other.wav", 3000).read_bytes()
    response = upload(client, other, "E - Five.wav")
    assert response.status_code == 201
    assert response.get_json()["track"]["id"] == "E - Five (2).wav"


def test_names_cannot_escape_the_music_folder(client, music_dir, song):
    response = upload(client, song, "../../../etc/Song.wav")
    assert response.get_json()["track"]["id"] == "Song.wav"
    assert (music_dir / "Song.wav").exists()


def test_non_latin_names_are_kept(client, music_dir, song):
    response = upload(client, song, "ॐ नमः शिवाय.wav")
    assert response.get_json()["track"]["id"] == "ॐ नमः शिवाय.wav"


@pytest.mark.parametrize(
    "data, name, message",
    [
        (b"hello", "notes.txt", "Unsupported file type"),
        (b"\x00" * 4096, "fake.mp3", "doesn't look like an audio file"),
        (b"", "empty.wav", "empty"),
    ],
)
def test_bad_uploads_are_rejected_and_leave_nothing_behind(client, music_dir, data, name, message):
    before = sorted(p.name for p in music_dir.iterdir())
    response = upload(client, data, name)
    assert response.status_code == 400
    assert message in response.get_json()["error"]
    assert sorted(p.name for p in music_dir.iterdir()) == before


def test_missing_file_field(client):
    response = client.post("/api/library/upload", data={}, content_type="multipart/form-data")
    assert response.status_code == 400


def test_too_large(client):
    response = upload(client, b"\x00" * (2 * 1024 * 1024), "big.wav")
    assert response.status_code == 413
    assert "1 MB" in response.get_json()["error"]


def test_upload_page_renders_the_modal(client):
    html = client.get("/").get_data(as_text=True)
    assert 'id="upload-modal"' in html and 'data-max-bytes="1048576"' in html


@pytest.mark.parametrize(
    "name, expected",
    [
        ("Song.MP3", "Song.mp3"),
        ("..hidden.flac", "hidden.flac"),
        ('bad<>:"|?*name.ogg', "badname.ogg"),
        (".wav", "Untitled.wav"),
        ("a\\b\\c.wav", "c.wav"),
    ],
)
def test_safe_filename(name, expected):
    assert safe_filename(name) == expected


def test_safe_filename_rejects_other_types():
    with pytest.raises(UploadError):
        safe_filename("movie.mp4")
