"""`python -m headless_music_player`: run the player with Flask's built-in server."""

import argparse

from .app import create_app
from .config import HOST, PORT


def main():
    parser = argparse.ArgumentParser(prog="headless-music-player")
    parser.add_argument("--host", default=HOST)
    parser.add_argument("--port", type=int, default=PORT)
    parser.add_argument("--dev", action="store_true", help="reload templates on change")
    args = parser.parse_args()

    app = create_app()
    app.config["TEMPLATES_AUTO_RELOAD"] = args.dev
    # No reloader: it would start a second process that opens the audio device too.
    app.run(host=args.host, port=args.port, threaded=True, use_reloader=False)


if __name__ == "__main__":
    main()
