"""Server-rendered pages. The page script swaps in the partials when the queue or library change."""

from flask import Blueprint, render_template

from ..services import library
from ..state import lock, snapshot
from .api import _library_tracks, public_state, public_track

views = Blueprint("views", __name__)


@views.app_template_filter("mmss")
def mmss(ms):
    seconds = max(0, int(ms or 0) // 1000)
    if seconds >= 3600:
        return f"{seconds // 3600}:{seconds % 3600 // 60:02d}:{seconds % 60:02d}"
    return f"{seconds // 60}:{seconds % 60:02d}"


def _queue_context():
    with lock:
        queue = snapshot()["queue"]
    entries = []
    for i, filename in enumerate(queue["tracks"]):
        track = public_track(filename) or {
            "filename": filename,
            "title": filename,
            "artist": "Missing file",
            "duration_ms": 0,
            "has_cover": False,
        }
        entries.append({"index": i, "track": track, "current": i == queue["index"]})
    return {"queue_entries": entries}


def _library_context():
    return {"library_tracks": _library_tracks()}


@views.route("/")
def index():
    library.get_library()
    return render_template(
        "index.html",
        state=public_state(),
        **_queue_context(),
        **_library_context(),
    )


@views.route("/partials/queue")
def queue_partial():
    return render_template("partials/queue.html", **_queue_context())


@views.route("/partials/library")
def library_partial():
    return render_template(
        "partials/library.html", current_file=public_state()["playback"]["current_file"], **_library_context()
    )
