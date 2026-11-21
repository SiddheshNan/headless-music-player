"""Server-rendered page and the partials the page script swaps in."""

from flask import Blueprint, current_app, render_template

from ..config import SUPPORTED_EXTENSIONS
from .serialize import queue_json, runtime, settings_json, state_json, track_json

views = Blueprint("views", __name__)


@views.app_template_filter("mmss")
def mmss(ms):
    seconds = max(0, int(ms or 0) // 1000)
    if seconds >= 3600:
        return f"{seconds // 3600}:{seconds % 3600 // 60:02d}:{seconds % 60:02d}"
    return f"{seconds // 60}:{seconds % 60:02d}"


def _library_context():
    lib = runtime().library
    return {"library_tracks": [track_json(t) for t in lib.tracks()], "library_version": lib.version}


@views.get("/")
def index():
    state = state_json()
    return render_template(
        "index.html",
        state=state,
        queue=queue_json(),
        max_upload_bytes=current_app.config.get("MAX_CONTENT_LENGTH") or 0,
        extensions=SUPPORTED_EXTENSIONS,
        **_library_context(),
    )


@views.get("/settings")
def settings():
    return render_template("settings.html", settings=settings_json())


@views.get("/partials/queue")
def queue_partial():
    return render_template("partials/queue.html", queue=queue_json())


@views.get("/partials/library")
def library_partial():
    current = state_json()["current"]
    current_track_id = current["track"]["id"] if current and current["track"] else None
    return render_template("partials/library.html", current_track_id=current_track_id, **_library_context())
