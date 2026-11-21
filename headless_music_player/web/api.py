"""JSON API under /api. The web UI uses it for every action.

Errors always look like {"error": "message"} with a 4xx/5xx status.
"""

from flask import Blueprint, abort, jsonify, request, send_file

from .. import __version__
from ..config import LOUDNESS_TARGETS
from ..library.uploads import UploadError, save_upload
from ..playqueue import REPEAT_MODES
from . import validate as v
from .serialize import queue_json, runtime, settings_json, state_json, track_json

api = Blueprint("api", __name__, url_prefix="/api")


def _ok():
    return jsonify(state_json())


@api.get("/health")
def health():
    snap = runtime().engine.snapshot()
    return jsonify({"status": "ok", "version": __version__, "audio": snap.audio_available})


@api.get("/state")
def state():
    return _ok()


# ============== Playback ==============


@api.post("/playback/play")
def playback_play():
    """Play a library track ({"track_id"}), a queue entry ({"entry_id"}), or resume ({})."""
    body = v.json_body()
    track_id = v.string(body, "track_id", required=False)
    entry_id = v.string(body, "entry_id", required=False)
    engine = runtime().engine
    if track_id and entry_id:
        raise v.ApiError("Send track_id or entry_id, not both.")
    if track_id:
        engine.play_track(track_id)
    elif entry_id:
        engine.play_entry(entry_id)
    else:
        engine.play()
    return _ok()


@api.post("/playback/toggle")
def playback_toggle():
    runtime().engine.toggle()
    return _ok()


@api.post("/playback/pause")
def playback_pause():
    runtime().engine.pause()
    return _ok()


@api.post("/playback/stop")
def playback_stop():
    runtime().engine.stop()
    return _ok()


@api.post("/playback/next")
def playback_next():
    runtime().engine.next()
    return _ok()


@api.post("/playback/prev")
def playback_prev():
    runtime().engine.previous()
    return _ok()


@api.post("/playback/seek")
def playback_seek():
    position = v.integer(v.json_body(), "position_ms")
    runtime().engine.seek(position)
    return _ok()


@api.post("/playback/volume")
def playback_volume():
    volume = v.number(v.json_body(), "volume", 0, 1)
    runtime().engine.set_volume(volume)
    return _ok()


# ============== Library ==============


@api.get("/library")
def library():
    lib = runtime().library
    return jsonify({"version": lib.version, "tracks": [track_json(t) for t in lib.tracks()]})


@api.post("/library/rescan")
def library_rescan():
    rt = runtime()
    result = rt.library.scan()
    rt.engine.library_changed()
    rt.analyzer.wake()
    return jsonify(
        {
            "version": rt.library.version,
            "total": result.total,
            "added": result.added,
            "removed": result.removed,
            "updated": result.updated,
        }
    )


@api.post("/library/upload")
def library_upload():
    """Add one song to the music folder: multipart form with a "file" field.

    One file per request, so clients can show progress per file. Answers 201 with the new
    track, or 200 with "duplicate": true when the identical file is already there.
    """
    upload = request.files.get("file")
    if upload is None or not upload.filename:
        raise v.ApiError("Send the song as a multipart form field named file.")
    rt = runtime()
    try:
        result = save_upload(rt.library, upload.stream, upload.filename)
    except UploadError as e:
        raise v.ApiError(str(e)) from e
    if result.created:
        rt.engine.library_changed()
        rt.analyzer.wake()
    return jsonify({"track": track_json(result.track), "duplicate": not result.created}), 201 if result.created else 200


@api.get("/library/covers/<name>")
def cover(name):
    path = runtime().library.cover_path(name)
    if path is None:
        abort(404)
    # Covers are named by a hash of their content, so they never change.
    return send_file(path, max_age=31_536_000)


# ============== Settings ==============


@api.get("/settings")
def settings():
    return jsonify(settings_json())


@api.post("/settings")
def settings_update():
    """Change settings: {"normalize": bool, "loudness_target": "quiet" | "normal" | "loud"}."""
    body = v.json_body()
    normalize = v.boolean(body, "normalize")
    target = v.choice(body, "loudness_target", tuple(LOUDNESS_TARGETS))
    runtime().engine.update_settings(normalize, target)
    return jsonify(settings_json())


# ============== Queue ==============


@api.get("/queue")
def queue():
    return jsonify(queue_json())


@api.post("/queue")
def queue_replace():
    """Replace the queue and start playing: {"track_ids": [...], "index": 0}."""
    body = v.json_body()
    track_ids = v.string_list(body, "track_ids")
    index = v.integer(body, "index", required=False, default=0)
    runtime().engine.replace_queue(track_ids, index)
    return _ok()


@api.post("/queue/add")
def queue_add():
    """Queue tracks at the end, or right after the current one with "next": true."""
    body = v.json_body()
    track_ids = v.string_list(body, "track_ids")
    play_next = v.boolean(body, "next", default=False)
    added = runtime().engine.add_to_queue(track_ids, play_next)
    return jsonify({"entry_ids": [e.id for e in added], "state": state_json()})


@api.delete("/queue/<entry_id>")
def queue_remove(entry_id):
    runtime().engine.remove_from_queue(entry_id)
    return _ok()


@api.post("/queue/clear")
def queue_clear():
    runtime().engine.clear_queue()
    return _ok()


@api.post("/queue/shuffle")
def queue_shuffle():
    """Turn shuffle on or off ({"enabled": bool}), or toggle it ({})."""
    enabled = v.boolean(v.json_body(), "enabled")
    runtime().engine.set_shuffle(enabled)
    return _ok()


@api.post("/queue/repeat")
def queue_repeat():
    """Set the repeat mode ({"mode": "off" | "all" | "one"}), or cycle it ({})."""
    mode = v.choice(v.json_body(), "mode", REPEAT_MODES)
    runtime().engine.set_repeat(mode)
    return _ok()


@api.post("/queue/play-all")
def queue_play_all():
    shuffle = v.boolean(v.json_body(), "shuffle", default=False)
    runtime().engine.play_all(shuffle)
    return _ok()
