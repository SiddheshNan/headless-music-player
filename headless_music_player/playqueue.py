"""The play queue: a plain model with no I/O or audio, so every rule here is unit-tested.

Entries have their own ids, so the same track can be queued more than once and an entry
can be addressed even after the queue around it changed. The insertion order is kept
separately from the shuffled order, so turning shuffle off always restores it.
"""

import random
import secrets
from dataclasses import dataclass

REPEAT_MODES = ("off", "all", "one")


@dataclass(frozen=True)
class Entry:
    id: str
    track_id: str


def _new_id() -> str:
    return secrets.token_hex(6)


class PlayQueue:
    def __init__(self, rng: random.Random | None = None):
        self._entries: list[Entry] = []  # insertion order
        self._shuffled: list[str] | None = None  # entry ids in play order while shuffle is on
        self.current_id: str | None = None
        self.repeat = "off"
        self._rng = rng or random.Random()

    # ---------- reading ----------

    @property
    def shuffle(self) -> bool:
        return self._shuffled is not None

    def __len__(self) -> int:
        return len(self._entries)

    def _order(self) -> list[str]:
        if self._shuffled is not None:
            return self._shuffled
        return [e.id for e in self._entries]

    def entries(self) -> list[Entry]:
        """Entries in play order."""
        by_id = {e.id: e for e in self._entries}
        return [by_id[i] for i in self._order()]

    def get(self, entry_id: str) -> Entry | None:
        return next((e for e in self._entries if e.id == entry_id), None)

    def current(self) -> Entry | None:
        return self.get(self.current_id) if self.current_id else None

    def current_index(self) -> int | None:
        """Position of the current entry in play order."""
        order = self._order()
        return order.index(self.current_id) if self.current_id in order else None

    def signature(self) -> tuple:
        """Changes whenever anything a client shows about the queue changes."""
        return (tuple((e.id, e.track_id) for e in self.entries()), self.current_id, self.shuffle, self.repeat)

    # ---------- editing ----------

    def replace(self, track_ids: list[str], start: int = 0, shuffle: bool | None = None) -> Entry | None:
        """Make these tracks the whole queue, current at `start`.

        shuffle=None keeps the shuffle mode; with shuffle on, `start` plays first and the rest
        is shuffled. shuffle=True with start=None picks a random first track.
        """
        self._entries = [Entry(_new_id(), t) for t in track_ids]
        if shuffle is not None:
            self._shuffled = [] if shuffle else None
        self.current_id = None
        if self._entries and start is not None:
            self.current_id = self._entries[start].id
        if self._shuffled is not None:
            self._reshuffle()
        if self.current_id is None:
            self.rewind()
        return self.current()

    def add(self, track_ids: list[str]) -> list[Entry]:
        """Append to the end. In an empty queue the first added entry becomes current."""
        added = [Entry(_new_id(), t) for t in track_ids]
        self._entries.extend(added)
        if self._shuffled is not None:
            self._shuffled.extend(e.id for e in added)
        if self.current_id is None and added:
            self.current_id = self._order()[0]
        return added

    def insert_next(self, track_id: str) -> Entry:
        """Insert right after the current entry (at the start when there is none)."""
        entry = Entry(_new_id(), track_id)
        self._insert_after(self._entries, entry, self.current_id, key=lambda e: e.id)
        if self._shuffled is not None:
            self._insert_after(self._shuffled, entry.id, self.current_id, key=lambda i: i)
        if self.current_id is None:
            self.current_id = entry.id
        return entry

    @staticmethod
    def _insert_after(items: list, item, anchor_id, key) -> None:
        ids = [key(x) for x in items]
        index = ids.index(anchor_id) + 1 if anchor_id in ids else 0
        items.insert(index, item)

    def remove(self, entry_id: str) -> bool | None:
        """Remove an entry. Returns None if it doesn't exist, else whether it was the current one.

        When the current entry is removed, the one after it becomes current (none at the end).
        """
        order = list(self._order())
        if entry_id not in order:
            return None
        index = order.index(entry_id)
        self._entries = [e for e in self._entries if e.id != entry_id]
        if self._shuffled is not None:
            self._shuffled.remove(entry_id)

        if entry_id != self.current_id:
            return False
        remaining = self._order()
        self.current_id = remaining[index] if index < len(remaining) else None
        return True

    def clear(self) -> None:
        self._entries = []
        if self._shuffled is not None:
            self._shuffled = []
        self.current_id = None

    def jump(self, entry_id: str) -> bool:
        if self.get(entry_id) is None:
            return False
        self.current_id = entry_id
        return True

    # ---------- navigation ----------

    def next(self, manual: bool) -> Entry | None:
        """Move to the next entry, or None at the end of the queue (current stays).

        Repeat "one" only holds for automatic advances: a skip always moves on.
        """
        order = self._order()
        if not order:
            return None
        if self.current_id not in order:
            self.current_id = order[0]
            return self.current()
        if not manual and self.repeat == "one":
            return self.current()

        index = order.index(self.current_id) + 1
        if index >= len(order):
            if self.repeat == "off":
                return None
            index = 0
        self.current_id = order[index]
        return self.current()

    def previous(self) -> Entry | None:
        """Move to the previous entry; at the start, wrap with repeat "all", else stay."""
        order = self._order()
        if not order:
            return None
        if self.current_id not in order:
            self.current_id = order[0]
            return self.current()

        index = order.index(self.current_id) - 1
        if index < 0:
            index = len(order) - 1 if self.repeat == "all" else 0
        self.current_id = order[index]
        return self.current()

    def rewind(self) -> Entry | None:
        """Make the first entry in play order current."""
        order = self._order()
        self.current_id = order[0] if order else None
        return self.current()

    # ---------- modes ----------

    def set_shuffle(self, enabled: bool) -> None:
        if enabled and self._shuffled is None:
            self._shuffled = []
            self._reshuffle()
        elif not enabled:
            self._shuffled = None

    def _reshuffle(self) -> None:
        """Current entry first, then the rest in random order."""
        rest = [e.id for e in self._entries if e.id != self.current_id]
        self._rng.shuffle(rest)
        self._shuffled = ([self.current_id] if self.get(self.current_id or "") else []) + rest

    def set_repeat(self, mode: str) -> None:
        if mode not in REPEAT_MODES:
            raise ValueError(f"repeat mode must be one of {', '.join(REPEAT_MODES)}")
        self.repeat = mode

    def cycle_repeat(self) -> str:
        """off -> all -> one -> off."""
        self.repeat = REPEAT_MODES[(REPEAT_MODES.index(self.repeat) + 1) % len(REPEAT_MODES)]
        return self.repeat

    # ---------- persistence ----------

    def to_dict(self) -> dict:
        return {
            "entries": [[e.id, e.track_id] for e in self._entries],
            "shuffled": list(self._shuffled) if self._shuffled is not None else None,
            "current": self.current_id,
            "repeat": self.repeat,
        }

    @classmethod
    def from_dict(cls, data: dict, rng: random.Random | None = None) -> "PlayQueue":
        """Rebuild from to_dict() output, dropping anything inconsistent instead of failing."""
        queue = cls(rng)
        seen = set()
        for item in data.get("entries") or []:
            if (
                isinstance(item, (list, tuple))
                and len(item) == 2
                and all(isinstance(x, str) for x in item)
                and item[0] not in seen
            ):
                queue._entries.append(Entry(item[0], item[1]))
                seen.add(item[0])

        shuffled = data.get("shuffled")
        if isinstance(shuffled, list):
            order = [i for i in shuffled if i in seen]
            order += [e.id for e in queue._entries if e.id not in order]
            queue._shuffled = list(dict.fromkeys(order))

        current = data.get("current")
        queue.current_id = current if current in seen else None
        if queue.current_id is None and queue._entries:
            queue.rewind()
        if data.get("repeat") in REPEAT_MODES:
            queue.repeat = data["repeat"]
        return queue
