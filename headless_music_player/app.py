"""App factory: wires settings, library, state store, audio backend and engine to Flask."""

import atexit
import logging
from dataclasses import dataclass

from flask import Flask

from . import __version__, web
from .audio import AudioBackend
from .config import Settings
from .engine import PlayerEngine
from .library import Library
from .store import StateStore

logger = logging.getLogger(__name__)


@dataclass
class Runtime:
    settings: Settings
    library: Library
    engine: PlayerEngine

    def shutdown(self) -> None:
        self.engine.shutdown()


def build_runtime(settings: Settings, backend: AudioBackend | None = None, **engine_options) -> Runtime:
    settings.ensure_directories()
    library = Library(settings.music_dir, settings.cache_dir)
    library.load_cache()
    library.scan()

    if backend is None:
        from .audio.pygame_backend import PygameBackend

        backend = PygameBackend()
    engine = PlayerEngine(backend, library, StateStore(settings.state_file), **engine_options)
    return Runtime(settings=settings, library=library, engine=engine)


def create_app(settings: Settings | None = None, backend: AudioBackend | None = None, start: bool = True, **engine_options):
    """Build the app. With start=False nothing touches the disk or audio (for CI import checks)."""
    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging.INFO,
    )
    app = Flask(__name__)
    app.json.sort_keys = False
    web.register(app)

    if start:
        settings = settings or Settings.from_env()
        logger.info(f"Headless Music Player {__version__}: music in {settings.music_dir}, data in {settings.runtime_dir}")
        rt = build_runtime(settings, backend, **engine_options)
        rt.engine.start()
        app.extensions["player"] = rt
        # Save the position and close the device on a clean shutdown (docker stop sends SIGTERM).
        atexit.register(rt.shutdown)
    return app
