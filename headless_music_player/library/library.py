"""The music library: the music folder (subfolders included), indexed and cached.

A track's id is its path inside the music folder, with forward slashes. The index is saved
to cache/library.json keyed by size and modification time, so a restart only reads tags
from files that changed. Covers are stored once per image, named by a hash of their bytes.
"""

import hashlib
import json
import logging
import os
import re
import threading
from dataclasses import asdict, dataclass
from pathlib import Path

from ..config import SUPPORTED_EXTENSIONS
from ..fsutil import atomic_write_bytes, atomic_write_text
from .metadata import read_metadata

logger = logging.getLogger(__name__)

INDEX_VERSION = 1
COVER_NAME = re.compile(r"^[0-9a-f]{20}\.(jpg|png|gif|webp)$")


@dataclass(frozen=True)
class Track:
    id: str
    title: str
    artist: str | None
    album: str | None
    duration_ms: int
    cover: str | None  # file name in the covers folder
    size: int
    mtime_ns: int


@dataclass(frozen=True)
class ScanResult:
    total: int
    added: int
    removed: int
    updated: int


class Library:
    def __init__(self, music_dir: Path, cache_dir: Path):
        self.music_dir = Path(music_dir)
        self.covers_dir = Path(cache_dir) / "covers"
        self._index_file = Path(cache_dir) / "library.json"
        self._tracks: dict[str, Track] = {}
        self._sorted: list[Track] = []
        self._scan_lock = threading.Lock()
        self.version = 0  # bumps whenever the set of tracks or their metadata changes

    # ---------- reading (safe from any thread: the dicts are replaced, never mutated) ----------

    def get(self, track_id: str) -> Track | None:
        return self._tracks.get(track_id)

    def __contains__(self, track_id: str) -> bool:
        return track_id in self._tracks

    def __len__(self) -> int:
        return len(self._tracks)

    def tracks(self) -> list[Track]:
        """All tracks, sorted by title, then artist."""
        return self._sorted

    def path_for(self, track_id: str) -> Path | None:
        if track_id not in self._tracks:
            return None
        path = self.music_dir / track_id
        return path if path.is_file() else None

    def cover_path(self, name: str) -> Path | None:
        if not COVER_NAME.match(name):
            return None
        path = self.covers_dir / name
        return path if path.is_file() else None

    # ---------- indexing ----------

    def load_cache(self) -> None:
        """Load the saved index, so the library is available before the first scan finishes."""
        try:
            data = json.loads(self._index_file.read_text(encoding="utf-8"))
            if data.get("version") != INDEX_VERSION:
                return
            tracks = {t["id"]: Track(**t) for t in data["tracks"]}
        except FileNotFoundError:
            return
        except (OSError, ValueError, KeyError, TypeError) as e:
            logger.warning(f"Ignoring unreadable library index: {e}")
            return
        self._set(tracks)

    def scan(self) -> ScanResult:
        """Re-index the music folder. One scan at a time; readers see the old index until it's done."""
        with self._scan_lock:
            old = self._tracks
            new: dict[str, Track] = {}
            updated = 0
            for path in self._walk():
                track_id = path.relative_to(self.music_dir).as_posix()
                try:
                    stat = path.stat()
                except OSError:
                    continue
                cached = old.get(track_id)
                if cached and cached.size == stat.st_size and cached.mtime_ns == stat.st_mtime_ns:
                    new[track_id] = cached
                    continue
                new[track_id] = self._read(track_id, path, stat)
                if cached:
                    updated += 1

            result = ScanResult(
                total=len(new),
                added=len(new.keys() - old.keys()),
                removed=len(old.keys() - new.keys()),
                updated=updated,
            )
            if new != old or not self._index_file.exists():
                self._set(new)
                self._save_index()
                self._prune_covers()
            logger.info(
                f"Library: {result.total} tracks ({result.added} new, {result.updated} changed, {result.removed} gone)"
            )
            return result

    def add_file(self, path: Path) -> Track:
        """Index one file in the music folder without rescanning everything (used after uploads)."""
        with self._scan_lock:
            track_id = path.relative_to(self.music_dir).as_posix()
            track = self._read(track_id, path, path.stat())
            self._set({**self._tracks, track_id: track})
            self._save_index()
            return track

    def _walk(self):
        if not self.music_dir.is_dir():
            return
        for root, dirs, files in os.walk(self.music_dir):
            dirs[:] = sorted(d for d in dirs if not d.startswith("."))
            for name in sorted(files):
                if not name.startswith(".") and name.lower().endswith(SUPPORTED_EXTENSIONS):
                    yield Path(root) / name

    def _read(self, track_id: str, path: Path, stat) -> Track:
        meta = read_metadata(path)
        return Track(
            id=track_id,
            title=meta.title,
            artist=meta.artist,
            album=meta.album,
            duration_ms=meta.duration_ms,
            cover=self._store_cover(meta.cover) if meta.cover else None,
            size=stat.st_size,
            mtime_ns=stat.st_mtime_ns,
        )

    def _store_cover(self, data: bytes) -> str | None:
        ext = _image_ext(data)
        if not ext:
            return None
        name = f"{hashlib.sha1(data).hexdigest()[:20]}.{ext}"
        path = self.covers_dir / name
        if not path.exists():
            try:
                atomic_write_bytes(path, data)
            except OSError as e:
                logger.warning(f"Can't save cover art: {e}")
                return None
        return name

    def _prune_covers(self) -> None:
        used = {t.cover for t in self._tracks.values() if t.cover}
        if not self.covers_dir.is_dir():
            return
        for path in self.covers_dir.iterdir():
            if path.name not in used and (COVER_NAME.match(path.name) or path.suffix == ".tmp"):
                path.unlink(missing_ok=True)

    def _set(self, tracks: dict[str, Track]) -> None:
        self._sorted = sorted(tracks.values(), key=lambda t: (t.title.casefold(), (t.artist or "").casefold(), t.id))
        self._tracks = tracks
        self.version += 1

    def _save_index(self) -> None:
        data = {"version": INDEX_VERSION, "tracks": [asdict(t) for t in self._tracks.values()]}
        try:
            atomic_write_text(self._index_file, json.dumps(data, ensure_ascii=False))
        except OSError as e:
            logger.warning(f"Can't save the library index: {e}")


def _image_ext(data: bytes) -> str | None:
    if data.startswith(b"\xff\xd8"):
        return "jpg"
    if data.startswith(b"\x89PNG"):
        return "png"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return None
