"""JSON API under /api. The web UI uses it for every action."""

import hashlib
import json
import os

from flask import Blueprint, jsonify, request, send_file

from .. import __version__
from ..services import library, player
from ..services import queue as play_queue
from ..state import STATE, lock, snapshot

api = Blueprint("api", __name__, url_prefix="/api")

PUBLIC_TRACK_FIELDS = ("filename", "title", "artist", "album", "duration_ms", "has_cover")


def public_track(filename):
    """Track metadata for clients, without internal fields such as the cover's path on disk."""
    info = library.get_track_info(filename)
    if not info:
        return None
    return {k: info.get(k) for k in PUBLIC_TRACK_FIELDS}


def queue_version(queue):
    """Changes whenever the queue's tracks or position change, so the UI knows to re-render it."""
    raw = json.dumps([queue["tracks"], queue["index"], queue["shuffle"]])
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def public_state():
    """The state as clients see it. Built from a copy, so nothing here leaks into the saved file."""
    with lock:
        state = snapshot()
        state["playback"]["position_ms"] = player.get_position()
        state["queue"]["upcoming"] = play_queue.get_upcoming_tracks(5)

    current = state["playback"]["current_file"]
    state["playback"]["current_track"] = public_track(current) if current else None
    state["queue"]["version"] = queue_version(state["queue"])
    del state["queue"]["original_order"]
    return state


def _error(message, status=400):
    return jsonify({"error": message}), status


@api.route("/health")
def health():
    return jsonify({"status": "ok", "version": __version__})


@api.route("/state")
def get_state():
    return jsonify(public_state())


# ============== Playback ==============


@api.route("/playback/play", methods=["POST"])
def playback_play():
    """Play a track: jump to it if it's in the queue, otherwise make it the whole queue."""
    filename = (request.get_json(silent=True) or {}).get("filename")
    if not filename:
        return _error("filename is required")
    if filename not in library.get_all_filenames():
        return _error("Track not found", 404)

    with lock:
        queue = STATE["queue"]
        if filename in queue["tracks"]:
            queue["index"] = queue["tracks"].index(filename)
        else:
            play_queue.set_queue([filename], 0)
        ok = player.play(filename)

    if ok:
        return jsonify({"message": "Playing", "filename": filename})
    return _error("Failed to play", 500)


@api.route("/playback/pause", methods=["POST"])
def playback_pause():
    if player.pause():
        return jsonify({"message": "Paused"})
    return _error("Not playing or already paused")


@api.route("/playback/resume", methods=["POST"])
def playback_resume():
    if player.resume():
        return jsonify({"message": "Resumed"})
    return _error("Not paused")


@api.route("/playback/toggle", methods=["POST"])
def playback_toggle():
    with lock:
        if STATE["playback"]["is_paused"]:
            player.resume()
            return jsonify({"message": "Resumed", "is_paused": False})
        player.pause()
        return jsonify({"message": "Paused", "is_paused": True})


@api.route("/playback/stop", methods=["POST"])
def playback_stop():
    player.stop()
    return jsonify({"message": "Stopped"})


@api.route("/playback/seek", methods=["POST"])
def playback_seek():
    position_ms = (request.get_json(silent=True) or {}).get("position_ms")
    if position_ms is None:
        return _error("position_ms is required")
    if player.seek(int(position_ms)):
        return jsonify({"message": "Seeked", "position_ms": position_ms})
    return _error("Seek failed")


@api.route("/playback/volume", methods=["POST"])
def playback_volume():
    volume = (request.get_json(silent=True) or {}).get("volume")
    if volume is None:
        return _error("volume is required")
    player.set_volume(float(volume))
    return jsonify({"message": "Volume set", "volume": volume})


@api.route("/playback/next", methods=["POST"])
def playback_next():
    track = player.next_track()
    if track:
        return jsonify({"message": "Next track", "filename": track})
    return jsonify({"message": "End of queue"})


@api.route("/playback/prev", methods=["POST"])
def playback_prev():
    track = player.prev_track()
    if track:
        return jsonify({"message": "Previous track", "filename": track})
    return _error("No previous track")


@api.route("/playback/position")
def playback_position():
    with lock:
        return jsonify(
            {
                "position_ms": player.get_position(),
                "duration_ms": STATE["playback"]["duration_ms"],
                "is_paused": STATE["playback"]["is_paused"],
                "is_playing": player.is_playing(),
            }
        )


# ============== Library ==============


def _library_tracks():
    tracks = [public_track(f) for f in library.get_library()]
    return sorted(tracks, key=lambda t: (t["title"] or "").lower())


@api.route("/library")
def get_library():
    return jsonify(_library_tracks())


@api.route("/library/reload", methods=["POST"])
def reload_library():
    library.scan_library()
    return jsonify(_library_tracks())


@api.route("/library/cover/<filename>")
def get_cover(filename):
    track = library.get_track_info(filename)
    if track and track.get("cover_path") and os.path.exists(track["cover_path"]):
        response = send_file(track["cover_path"], mimetype="image/jpeg")
        response.headers["Cache-Control"] = "public, max-age=86400"
        return response
    return _error("No cover art", 404)


# ============== Queue ==============


@api.route("/queue")
def get_queue():
    with lock:
        queue = snapshot()["queue"]
    return jsonify(
        {
            "tracks": [t for t in (public_track(f) for f in queue["tracks"]) if t],
            "index": queue["index"],
            "shuffle": queue["shuffle"],
            "repeat_mode": queue["repeat_mode"],
        }
    )


@api.route("/queue/set", methods=["POST"])
def set_queue():
    data = request.get_json(silent=True) or {}
    tracks = data.get("tracks", [])
    start_index = data.get("index", 0)

    with lock:
        play_queue.set_queue(tracks, start_index)
        if tracks:
            player.play(tracks[start_index])
    return jsonify({"message": "Queue set", "count": len(tracks)})


@api.route("/queue/add", methods=["POST"])
def add_to_queue():
    filename = (request.get_json(silent=True) or {}).get("filename")
    if not filename:
        return _error("filename is required")
    added = play_queue.add_to_queue(filename)
    message = "Added to queue" if added else "Already in queue"
    return jsonify({"message": message, "filename": filename, "added": added})


@api.route("/queue/remove", methods=["POST"])
def remove_from_queue():
    index = (request.get_json(silent=True) or {}).get("index")
    if index is None:
        return _error("index is required")
    if play_queue.remove_from_queue(int(index)):
        return jsonify({"message": "Removed from queue"})
    return _error("Invalid index")


@api.route("/queue/clear", methods=["POST"])
def clear_queue():
    with lock:
        play_queue.clear_queue()
        player.stop()
    return jsonify({"message": "Queue cleared"})


@api.route("/queue/shuffle", methods=["POST"])
def toggle_shuffle():
    return jsonify({"shuffle": play_queue.toggle_shuffle()})


@api.route("/queue/repeat", methods=["POST"])
def set_repeat():
    """Set the repeat mode, or cycle to the next one when no mode is given."""
    mode = (request.get_json(silent=True) or {}).get("mode")
    if mode:
        if play_queue.set_repeat_mode(mode):
            return jsonify({"repeat_mode": mode})
        return _error("Invalid mode")
    return jsonify({"repeat_mode": play_queue.cycle_repeat_mode()})


@api.route("/queue/play-all", methods=["POST"])
def play_all():
    shuffle = bool((request.get_json(silent=True) or {}).get("shuffle", False))
    with lock:
        tracks = play_queue.play_all(shuffle)
        if not tracks:
            return _error("Library is empty")
        player.play(tracks[0])
    return jsonify({"message": "Playing all", "count": len(tracks)})
