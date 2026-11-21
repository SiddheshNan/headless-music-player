"""JSON shapes shared by the API and the templates."""

from flask import current_app, url_for

from .. import __version__
from ..config import LOUDNESS_TARGETS
from ..library import Track


def runtime():
    return current_app.extensions["player"]


def track_json(track: Track | None) -> dict | None:
    if track is None:
        return None
    return {
        "id": track.id,
        "title": track.title,
        "artist": track.artist,
        "album": track.album,
        "duration_ms": track.duration_ms,
        "cover_url": url_for("api.cover", name=track.cover) if track.cover else None,
    }


def state_json() -> dict:
    rt = runtime()
    snap = rt.engine.snapshot()
    library = rt.library
    current = None
    if snap.current_entry_id:
        current = {"entry_id": snap.current_entry_id, "track": track_json(library.get(snap.current_track_id))}
    index = next((i for i, e in enumerate(snap.queue) if e.id == snap.current_entry_id), None)
    return {
        "version": snap.version,
        "queue_version": snap.queue_version,
        "library_version": library.version,
        "status": snap.status,
        "position_ms": snap.position_now(rt.engine.clock()),
        "duration_ms": snap.duration_ms,
        "volume": snap.volume,
        "shuffle": snap.shuffle,
        "repeat": snap.repeat,
        "audio": {"available": snap.audio_available, "error": snap.audio_error},
        "normalization": {"enabled": snap.normalize, "target": snap.loudness_target, "gain_db": snap.gain_db},
        "current": current,
        "queue": {"length": len(snap.queue), "index": index},
    }


def settings_json() -> dict:
    rt = runtime()
    snap = rt.engine.snapshot()
    analyzed, total = rt.library.analysis_progress()
    return {
        "normalize": snap.normalize,
        "loudness_target": snap.loudness_target,
        "loudness_targets": {name: lufs for name, lufs in LOUDNESS_TARGETS.items()},
        "analysis": {"analyzed": analyzed, "total": total, "running": rt.analyzer.running},
        "library": {"music_dir": str(rt.settings.music_dir), "tracks": total},
        "data_dir": str(rt.settings.runtime_dir),
        "max_upload_mb": rt.settings.max_upload_mb,
        "audio": {"available": snap.audio_available, "error": snap.audio_error, "output": snap.output},
        "version": __version__,
    }


def queue_json() -> dict:
    rt = runtime()
    snap = rt.engine.snapshot()
    return {
        "version": snap.queue_version,
        "current_entry_id": snap.current_entry_id,
        "shuffle": snap.shuffle,
        "repeat": snap.repeat,
        "entries": [
            {"id": e.id, "track_id": e.track_id, "track": track_json(rt.library.get(e.track_id))} for e in snap.queue
        ],
    }
