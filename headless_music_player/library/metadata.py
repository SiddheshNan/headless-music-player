"""Tags, duration and embedded cover art from an audio file."""

import base64
import logging
from dataclasses import dataclass
from pathlib import Path

from mutagen import File as MutagenFile
from mutagen.flac import Picture

logger = logging.getLogger(__name__)


@dataclass
class Metadata:
    title: str
    artist: str | None
    album: str | None
    duration_ms: int
    cover: bytes | None = None


def read_metadata(path: Path) -> Metadata:
    title = artist = album = None
    duration_ms = 0
    cover = None

    try:
        audio = MutagenFile(path)
    except Exception as e:  # mutagen raises many types for broken files
        logger.warning(f"Can't read tags from {path.name}: {e}")
        audio = None

    if audio is not None:
        length = getattr(getattr(audio, "info", None), "length", 0) or 0
        duration_ms = int(length * 1000)
        tags = audio.tags
        if tags is not None:
            title = _text(tags, "TIT2", "title")
            artist = _text(tags, "TPE1", "artist")
            album = _text(tags, "TALB", "album")
        cover = _cover(audio, tags)

    if not title:
        title, guessed_artist = _from_filename(path.stem)
        artist = artist or guessed_artist
    return Metadata(title=title, artist=artist, album=album, duration_ms=duration_ms, cover=cover)


def _text(tags, id3_key: str, vorbis_key: str) -> str | None:
    """ID3 frames and Vorbis comments store text differently; take the first non-empty value."""
    for key in (id3_key, vorbis_key):
        try:
            value = tags.get(key)
        except (KeyError, ValueError, TypeError):
            continue
        if value is None:
            continue
        value = getattr(value, "text", value)
        if isinstance(value, (list, tuple)):
            value = value[0] if value else None
        text = str(value).strip() if value is not None else ""
        if text:
            return text
    return None


def _cover(audio, tags) -> bytes | None:
    pictures = getattr(audio, "pictures", None)  # FLAC
    if pictures:
        return pictures[0].data
    if tags is None:
        return None
    if hasattr(tags, "getall"):  # ID3 (MP3, WAV)
        frames = tags.getall("APIC")
        if frames:
            front = next((f for f in frames if f.type == 3), frames[0])
            return front.data
        return None
    try:
        blocks = tags.get("metadata_block_picture")  # Ogg Vorbis
        if blocks:
            return Picture(base64.b64decode(blocks[0])).data
    except Exception:
        pass
    return None


def _from_filename(stem: str) -> tuple[str, str | None]:
    """Untagged files are often named "Artist - Title"."""
    name = stem.replace("_", " ").strip()
    if " - " in name:
        artist, title = name.split(" - ", 1)
        if artist.strip() and title.strip():
            return title.strip(), artist.strip()
    return name or stem, None
