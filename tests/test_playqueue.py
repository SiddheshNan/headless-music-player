import random

import pytest

from headless_music_player.playqueue import PlayQueue


def tracks(q):
    return [e.track_id for e in q.entries()]


def current(q):
    return q.current().track_id if q.current() else None


@pytest.fixture
def q():
    queue = PlayQueue(random.Random(3))
    queue.replace(["a", "b", "c", "d"])
    return queue


def test_replace_sets_current(q):
    assert tracks(q) == ["a", "b", "c", "d"]
    assert current(q) == "a"
    q.replace(["x", "y"], start=1)
    assert current(q) == "y"


def test_next_moves_on_and_stops_at_end(q):
    assert q.next(manual=True).track_id == "b"
    q.jump(q.entries()[-1].id)
    assert q.next(manual=True) is None
    assert current(q) == "d"


def test_repeat_all_wraps_both_ways(q):
    q.set_repeat("all")
    q.jump(q.entries()[-1].id)
    assert q.next(manual=False).track_id == "a"
    assert q.previous().track_id == "d"


def test_repeat_one_only_holds_for_automatic_advance(q):
    q.set_repeat("one")
    assert q.next(manual=False).track_id == "a"
    assert q.next(manual=True).track_id == "b"


def test_previous_at_start_stays(q):
    assert q.previous().track_id == "a"


def test_cycle_repeat(q):
    assert [q.cycle_repeat() for _ in range(3)] == ["all", "one", "off"]
    with pytest.raises(ValueError):
        q.set_repeat("sometimes")


def test_shuffle_keeps_current_first_and_off_restores_order(q):
    q.next(manual=True)  # b
    q.set_shuffle(True)
    assert tracks(q)[0] == "b"
    assert sorted(tracks(q)) == ["a", "b", "c", "d"]
    q.set_shuffle(False)
    assert tracks(q) == ["a", "b", "c", "d"]
    assert current(q) == "b"


def test_replace_shuffled_with_random_start_unshuffles_to_given_order():
    q = PlayQueue(random.Random(1))
    q.replace(["a", "b", "c", "d", "e"], start=None, shuffle=True)
    assert q.shuffle and tracks(q)[0] == current(q)
    q.set_shuffle(False)
    assert tracks(q) == ["a", "b", "c", "d", "e"]


def test_duplicates_are_separate_entries(q):
    added = q.add(["a"])
    assert tracks(q) == ["a", "b", "c", "d", "a"]
    assert added[0].id != q.entries()[0].id


def test_insert_next_goes_after_current_also_when_shuffled(q):
    q.next(manual=True)  # b
    q.insert_next("x")
    assert tracks(q) == ["a", "b", "x", "c", "d"]
    q.set_shuffle(True)
    q.insert_next("y")
    assert tracks(q)[:2] == ["b", "y"]
    q.set_shuffle(False)
    assert tracks(q) == ["a", "b", "y", "x", "c", "d"]


def test_insert_next_in_empty_queue_becomes_current():
    q = PlayQueue()
    q.insert_next("x")
    assert current(q) == "x"


def test_remove_other_entry_keeps_current(q):
    b = q.entries()[1]
    assert q.remove(b.id) is False
    assert tracks(q) == ["a", "c", "d"] and current(q) == "a"


def test_remove_current_moves_to_the_next_entry(q):
    q.next(manual=True)  # b
    assert q.remove(q.current_id) is True
    assert current(q) == "c"


def test_remove_last_current_leaves_none(q):
    q.jump(q.entries()[-1].id)
    assert q.remove(q.current_id) is True
    assert q.current() is None


def test_removed_entry_stays_gone_after_unshuffle(q):
    q.set_shuffle(True)
    victim = next(e for e in q.entries() if e.track_id == "c")
    q.remove(victim.id)
    q.set_shuffle(False)
    assert tracks(q) == ["a", "b", "d"]


def test_remove_unknown_returns_none(q):
    assert q.remove("nope") is None


def test_round_trip(q):
    q.set_shuffle(True)
    q.set_repeat("all")
    q.next(manual=True)
    restored = PlayQueue.from_dict(q.to_dict())
    assert restored.signature() == q.signature()


def test_from_dict_drops_garbage():
    q = PlayQueue.from_dict(
        {
            "entries": [["e1", "a"], ["e1", "dupe"], "junk", ["e2", 5], ["e3", "c"]],
            "shuffled": ["e3", "missing"],
            "current": "missing",
            "repeat": "sometimes",
        }
    )
    assert tracks(q) == ["c", "a"]
    assert current(q) == "c"
    assert q.repeat == "off"
