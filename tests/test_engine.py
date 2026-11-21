import pytest

from headless_music_player.audio.fake import FakeBackend
from headless_music_player.config import AUDIO_RETRY_S
from headless_music_player.engine import CommandError

from .conftest import TRACK_MS, ids, make_wav


def playing(engine):
    snap = engine.snapshot()
    return snap.status, snap.current_track_id


def queue_tracks(engine):
    return [e.track_id for e in engine.snapshot().queue]


def finish_track(engine, clock):
    clock.advance(TRACK_MS / 1000 + 1)
    engine.tick()


def test_play_all_then_advance_and_stop_at_the_end(engine, library, clock, backend):
    order = ids(library)
    engine.play_all()
    assert playing(engine) == ("playing", order[0])
    for track_id in order[1:]:
        finish_track(engine, clock)
        assert playing(engine) == ("playing", track_id)
    finish_track(engine, clock)
    # End of the queue: stopped, ready to start over from the top.
    assert playing(engine) == ("stopped", order[0])
    engine.toggle()
    assert playing(engine) == ("playing", order[0])


def test_position_comes_from_the_backend_and_freezes_when_paused(engine, clock):
    engine.play_all()
    clock.advance(12)
    engine.pause()
    clock.advance(30)
    engine.tick()
    assert engine.snapshot().position_ms == 12_000


def test_restored_pause_resumes_at_the_saved_position(make_engine, clock, library):
    """Bug 1: after a restart while paused, playback and the shown position start where they were."""
    first = make_engine()
    first.play_all()
    clock.advance(42)
    first.pause()
    first.shutdown()

    backend = FakeBackend(clock)
    second = make_engine(backend)
    assert second.snapshot().status == "paused"
    assert second.snapshot().position_ms == 42_000
    second.toggle()
    assert backend.calls[-1] == "play 42000"
    clock.advance(3)
    second.tick()
    assert second.snapshot().position_ms == 45_000


def test_restored_playback_continues(make_engine, clock):
    first = make_engine()
    first.play_all()
    clock.advance(20)
    first.tick()
    first.shutdown()

    backend = FakeBackend(clock)
    second = make_engine(backend)
    assert second.snapshot().status == "playing"
    assert backend.calls[-1] == "play 20000"


def test_next_skips_even_with_repeat_one(engine, library, clock):
    """Bug 2: repeat "one" replays when a track ends, but Next still moves on."""
    order = ids(library)
    engine.play_all()
    engine.set_repeat("one")
    finish_track(engine, clock)
    assert playing(engine) == ("playing", order[0])
    engine.next()
    assert playing(engine) == ("playing", order[1])


def test_play_when_stopped_starts_the_queue(engine, library):
    """Bug 3: play with nothing loaded starts the current track instead of pretending to play."""
    engine.play_all()
    engine.stop()
    assert engine.snapshot().status == "stopped"
    engine.toggle()
    assert playing(engine) == ("playing", ids(library)[0])


def test_play_with_an_empty_queue_says_so(engine):
    with pytest.raises(CommandError, match="queue is empty"):
        engine.toggle()
    assert engine.snapshot().status == "stopped"


def test_shuffle_all_then_unshuffle_restores_library_order(engine, library):
    """Bug 4: turning shuffle off after "Shuffle all" gives the library order back."""
    engine.play_all(shuffle=True)
    assert engine.snapshot().shuffle
    engine.set_shuffle(False)
    assert queue_tracks(engine) == ids(library)


def test_playing_a_library_track_keeps_the_queue(engine, library):
    """Bug 5: a track played from the library is inserted after the current one."""
    order = ids(library)
    engine.replace_queue(order[:2])
    engine.play_track(order[3])
    assert queue_tracks(engine) == [order[0], order[3], order[1]]
    assert playing(engine) == ("playing", order[3])


def test_playing_the_current_track_restarts_it(engine, library, clock, backend):
    engine.play_all()
    clock.advance(10)
    engine.play_track(ids(library)[0])
    assert len(engine.snapshot().queue) == 4
    assert backend.position_ms() == 0


def test_removing_the_playing_entry_plays_the_next(engine, library):
    """Bug 6: removing the current entry moves playback to what took its place."""
    order = ids(library)
    engine.play_all()
    engine.remove_from_queue(engine.snapshot().current_entry_id)
    assert playing(engine) == ("playing", order[1])
    assert queue_tracks(engine) == order[1:]


def test_removing_the_last_playing_entry_stops(engine, library):
    engine.play_all()
    last = engine.snapshot().queue[-1]
    engine.play_entry(last.id)
    engine.remove_from_queue(last.id)
    assert playing(engine) == ("stopped", ids(library)[0])


def test_missing_sound_card_is_retried_and_playback_resumes(make_engine, clock, library):
    """Bug 7: no audio device at boot no longer crashes; playback starts once it appears."""
    first = make_engine()
    first.play_all()
    clock.advance(5)
    first.tick()
    first.shutdown()

    backend = FakeBackend(clock, unavailable_times=2)
    engine = make_engine(backend)
    snap = engine.snapshot()
    assert not snap.audio_available and snap.audio_error
    assert snap.status == "playing" and snap.position_ms == 5000
    engine.next()  # commands still work without a device
    assert engine.snapshot().current_track_id == ids(library)[1]

    clock.advance(AUDIO_RETRY_S)
    engine.tick()  # second failure
    assert not engine.snapshot().audio_available
    clock.advance(AUDIO_RETRY_S)
    engine.tick()
    assert engine.snapshot().audio_available
    assert backend.playing and backend.calls[-1] == "play 0"


def test_unknown_tracks_are_rejected(engine):
    """Bug 8: track ids are checked against the library."""
    with pytest.raises(CommandError) as e:
        engine.add_to_queue(["nope.mp3"])
    assert e.value.status == 404
    with pytest.raises(CommandError):
        engine.replace_queue(["nope.mp3"])
    with pytest.raises(CommandError):
        engine.play_track("../../etc/passwd")
    assert engine.snapshot().queue == ()


def test_replace_queue_checks_the_index(engine, library):
    with pytest.raises(CommandError) as e:
        engine.replace_queue(ids(library), 9)
    assert e.value.status == 400


def test_add_to_empty_queue_makes_it_playable(engine, library):
    engine.add_to_queue([ids(library)[2]])
    assert playing(engine) == ("stopped", ids(library)[2])
    engine.toggle()
    assert playing(engine) == ("playing", ids(library)[2])


def test_play_next_keeps_the_given_order(engine, library):
    order = ids(library)
    engine.replace_queue(order[:2])
    engine.add_to_queue([order[2], order[3]], play_next=True)
    assert queue_tracks(engine) == [order[0], order[2], order[3], order[1]]


def test_seek_while_paused_resumes_from_there(engine, backend):
    engine.play_all()
    engine.pause()
    engine.seek(30_000)
    assert engine.snapshot().position_ms == 30_000
    engine.toggle()
    assert backend.calls[-1] == "play 30000"


def test_seek_is_clamped_and_unsupported_formats_say_so(make_engine, clock):
    backend = FakeBackend(clock, seekable=False)
    engine = make_engine(backend)
    engine.play_all()
    with pytest.raises(CommandError, match="Seeking"):
        engine.seek(10_000)
    engine.pause()
    engine.seek(999_999)
    assert engine.snapshot().position_ms == TRACK_MS


def test_previous_restarts_after_three_seconds(engine, library, clock, backend):
    order = ids(library)
    engine.play_all()
    engine.next()
    clock.advance(10)
    engine.previous()
    assert playing(engine) == ("playing", order[1])
    engine.previous()
    assert playing(engine) == ("playing", order[0])


def test_unplayable_files_are_skipped(make_engine, library, music_dir, clock):
    make_wav(music_dir / "AA - corrupt.wav")
    library.scan()
    engine = make_engine()
    engine.replace_queue(["AA - corrupt.wav", "A - One.wav"])
    assert playing(engine) == ("playing", "A - One.wav")


def test_volume_survives_a_restart(make_engine, clock):
    first = make_engine()
    first.set_volume(0.76)
    first.shutdown()
    backend = FakeBackend(clock)
    second = make_engine(backend)
    assert second.snapshot().volume == 0.76
    assert backend.volume == 0.76


def test_position_is_saved_while_playing(engine, store, clock):
    engine.play_all()
    for _ in range(30):
        clock.advance(0.25)
        engine.tick()
    assert store.load()["position_ms"] >= 5000


def test_queue_version_changes_only_with_the_queue(engine, clock):
    engine.play_all()
    version = engine.snapshot().queue_version
    clock.advance(1)
    engine.tick()
    engine.set_volume(0.2)
    assert engine.snapshot().queue_version == version
    engine.next()
    assert engine.snapshot().queue_version > version
