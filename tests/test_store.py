import json

from headless_music_player.playqueue import PlayQueue
from headless_music_player.store import STATE_VERSION


def test_round_trip_and_skip_unchanged(store):
    state = {"volume": 0.3, "status": "paused", "position_ms": 1234, "queue": {"entries": []}}
    assert store.save(state) is True
    assert store.save(state) is False
    loaded = store.load()
    assert loaded["volume"] == 0.3 and loaded["version"] == STATE_VERSION
    assert not list(store.path.parent.glob("*.tmp"))


def test_truncated_file_is_kept_aside(store):
    store.path.parent.mkdir(parents=True, exist_ok=True)
    store.path.write_text('{"volume": 0.8, "queue": {"entr')
    assert store.load() is None
    assert not store.path.exists()
    assert store.path.with_name("state.json.corrupt").exists()


def test_empty_file_is_kept_aside(store):
    store.path.parent.mkdir(parents=True, exist_ok=True)
    store.path.write_text("")
    assert store.load() is None


def test_migrates_the_0_1_format(store):
    old = {
        "playback": {
            "is_paused": False,
            "current_file": "b.mp3",
            "volume": 0.76,
            "position_ms": 15437,
            "duration_ms": 25000,
            "current_track": {"cover_path": "D:\\old\\path.jpg"},
        },
        "queue": {
            "tracks": ["c.mp3", "b.mp3", "a.mp3"],
            "index": 1,
            "shuffle": True,
            "repeat_mode": "one",
            "original_order": ["a.mp3", "b.mp3", "c.mp3"],
            "upcoming": ["a.mp3"],
        },
    }
    store.path.parent.mkdir(parents=True, exist_ok=True)
    store.path.write_text(json.dumps(old))
    state = store.load()
    assert state["volume"] == 0.76
    assert state["status"] == "playing" and state["position_ms"] == 15437

    q = PlayQueue.from_dict(state["queue"])
    assert [e.track_id for e in q.entries()] == ["c.mp3", "b.mp3", "a.mp3"]
    assert q.current().track_id == "b.mp3" and q.repeat == "one"
    q.set_shuffle(False)
    assert [e.track_id for e in q.entries()] == ["a.mp3", "b.mp3", "c.mp3"]
