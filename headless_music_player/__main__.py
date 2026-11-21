"""`python -m headless_music_player`: run the player with Flask's built-in server."""

import argparse
import dataclasses

from .app import create_app
from .config import Settings


def main():
    settings = Settings.from_env()
    parser = argparse.ArgumentParser(prog="headless-music-player")
    parser.add_argument("--host", default=settings.host)
    parser.add_argument("--port", type=int, default=settings.port)
    parser.add_argument("--dev", action="store_true", help="reload templates on change")
    args = parser.parse_args()
    settings = dataclasses.replace(settings, host=args.host, port=args.port)

    app = create_app(settings)
    app.config["TEMPLATES_AUTO_RELOAD"] = args.dev
    # No reloader: it would start a second process that opens the audio device too.
    app.run(host=settings.host, port=settings.port, threaded=True, use_reloader=False)


if __name__ == "__main__":
    main()
