"""Saving uploaded songs into the music folder.

The upload is written to a hidden temp file in the music folder (the scan skips hidden
files), checked to be audio, then renamed into place, so a half-uploaded file is never
indexed or played. Names are kept readable (spaces and non-Latin letters stay) but can't
escape the folder.
"""

import hashlib
import logging
import os
import secrets
import threading
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from mutagen import File as MutagenFile

from ..config import SUPPORTED_EXTENSIONS
from .library import Library, Track

logger = logging.getLogger(__name__)

MAX_NAME_LENGTH = 150
_FORBIDDEN = set('<>:"/\\|?*')
_name_lock = threading.Lock()  # choosing a free name and renaming into it happen together


class UploadError(Exception):
    pass


@dataclass(frozen=True)
class UploadResult:
    track: Track
    created: bool  # False when the identical file was already in the library


def safe_filename(name: str) -> str:
    """A file name that stays inside the music folder; raises UploadError for unsupported types."""
    name = unicodedata.normalize("NFC", name.replace("\\", "/").rsplit("/", 1)[-1])
    name = "".join(c for c in name if c.isprintable() and c not in _FORBIDDEN).strip()
    dot = name.rfind(".")
    stem, ext = (name[:dot], name[dot:]) if dot != -1 else (name, "")
    if ext.lower() not in SUPPORTED_EXTENSIONS:
        supported = ", ".join(e.lstrip(".") for e in SUPPORTED_EXTENSIONS)
        raise UploadError(f"Unsupported file type. Use {supported}.")
    # No leading dots: hidden files are skipped by the library scan.
    stem = stem.lstrip(". ")[:MAX_NAME_LENGTH].strip() or "Untitled"
    return stem + ext.lower()


def save_upload(library: Library, stream: BinaryIO, filename: str) -> UploadResult:
    name = safe_filename(filename)
    music_dir = library.music_dir
    music_dir.mkdir(parents=True, exist_ok=True)
    tmp = music_dir / f".upload-{secrets.token_hex(6)}{Path(name).suffix}"

    try:
        digest = hashlib.sha256()
        with open(tmp, "wb") as f:
            while chunk := stream.read(1024 * 1024):
                digest.update(chunk)
                f.write(chunk)
            f.flush()
            os.fsync(f.fileno())
        if tmp.stat().st_size == 0:
            raise UploadError("The file is empty.")
        if not _is_audio(tmp):
            raise UploadError("This doesn't look like an audio file.")

        stem, ext = os.path.splitext(name)
        with _name_lock:
            dest, n = music_dir / name, 1
            while dest.exists():
                if _sha256(dest) == digest.hexdigest():
                    existing = library.get(dest.relative_to(music_dir).as_posix()) or library.add_file(dest)
                    return UploadResult(existing, created=False)
                n += 1
                dest = music_dir / f"{stem} ({n}){ext}"
            os.replace(tmp, dest)
        logger.info(f"Uploaded {dest.name}")
        return UploadResult(library.add_file(dest), created=True)
    finally:
        tmp.unlink(missing_ok=True)


def _is_audio(path: Path) -> bool:
    try:
        audio = MutagenFile(path)
    except Exception:
        return False
    return audio is not None and getattr(getattr(audio, "info", None), "length", 0) > 0


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()
