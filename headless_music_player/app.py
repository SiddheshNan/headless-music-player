"""Flask app factory and the background loop."""

import atexit
import logging
import threading
import time

from flask import Flask

from . import __version__
from .config import POSITION_SAVE_INTERVAL_S, ensure_directories
from .routes.api import api
from .routes.views import views
from .services import library, player
from .state import load_state, save_state

logger = logging.getLogger(__name__)

_started = False


def _background_loop():
    ticks = 0
    while True:
        try:
            player.check_track_ended()
            player.sync_position()
            ticks += 1
            if ticks % POSITION_SAVE_INTERVAL_S == 0:
                save_state()
        except Exception:
            logger.exception("Background task error")
        time.sleep(1)


def start_player():
    """Load state, open the audio device, scan the library and resume playback. Runs once."""
    global _started
    if _started:
        return
    _started = True

    logger.info(f"Headless Music Player {__version__} starting")
    ensure_directories()
    load_state()
    player.init_player()
    library.scan_library()
    player.restore_state()

    threading.Thread(target=_background_loop, name="player-loop", daemon=True).start()
    # Save the latest position on a clean shutdown (docker stop sends SIGTERM).
    atexit.register(save_state)


def create_app(start=True):
    """Build the app. With start=False the audio device and library are left alone (for tests and CI)."""
    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging.INFO,
    )

    app = Flask(__name__)
    app.register_blueprint(api)
    app.register_blueprint(views)

    if start:
        start_player()
    return app
