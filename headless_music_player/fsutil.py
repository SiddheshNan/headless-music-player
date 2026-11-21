"""Crash-safe file writes."""

import os
from pathlib import Path


def atomic_write_bytes(path: Path, data: bytes) -> None:
    """Write via a temp file that is fsynced and renamed over the target.

    After a power cut the file is either the old or the new version, never a truncated one.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)
    _fsync_dir(path.parent)


def atomic_write_text(path: Path, text: str) -> None:
    atomic_write_bytes(path, text.encode("utf-8"))


def _fsync_dir(path: Path) -> None:
    # Makes the rename itself durable. Not possible on Windows, where it isn't needed.
    try:
        fd = os.open(path, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(fd)
    except OSError:
        pass
    finally:
        os.close(fd)
