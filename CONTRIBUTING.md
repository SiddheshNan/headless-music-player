# Contributing to Headless Music Player

Thanks for helping. The project is small and early, so for anything bigger than a bug fix please open an issue first and describe what you want to change. It saves both of us a rewrite.

## Setup

You need Python 3.10+. Docker is only needed to build the image.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python scripts/build_css.py            # downloads Tailwind + daisyUI into .tools/, builds app.css
python -m headless_music_player --dev  # http://localhost:8000, templates reload on change
```

Put some music in `runtime/music/`. Everything written at runtime (`state.json`, the cover cache) lands in `runtime/` and is gitignored. Set `SDL_AUDIODRIVER=dummy` to run without a sound card.

While changing templates or `static/js/app.js`, keep `python scripts/build_css.py --watch` running so new Tailwind classes end up in the CSS.

## Layout

```
headless_music_player/   the app (Flask)
  app.py                 app factory, startup and the background loop
  config.py              paths and settings (HMP_* environment variables)
  state.py               the shared state, its lock and the atomic save to state.json
  services/player.py     pygame mixer playback
  services/library.py    folder scan, tags and cover art
  services/queue.py      the global queue: order, shuffle, repeat
  routes/api.py          JSON API under /api
  routes/views.py        server-rendered page and partials
  templates/             Jinja templates (pages, partials, icon macros)
  static/                app.js, input.css (built to app.css), favicon
scripts/build_css.py     Tailwind standalone CLI + daisyUI
scripts/build.py         release build
docs/DESIGN.md           how it works
```

[docs/DESIGN.md](docs/DESIGN.md) explains how the pieces fit. Read the relevant section before changing how something behaves, and update it in the same pull request when you do.

## Before you open a pull request

```bash
ruff check .
python scripts/build_css.py
```

- Keep changes focused; one pull request per fix or feature.
- Match the code around you. Comments explain why, not what, and only where it isn't obvious.
- Change `STATE` only while holding `state.lock`, and go through `update_playback`/`update_queue` or call `save_state()` after.
- The UI stays server-rendered: markup lives in templates, and `app.js` only sends actions and swaps in partials. No frontend framework or Node build.
- Audio output is mono on purpose.

## Releases

`python scripts/build.py` asks for the version, writes it into `headless_music_player/__init__.py` and `pyproject.toml`, builds the CSS and the Docker image. Pushing a `vX.Y.Z` tag publishes the image to GitHub Container Registry for `linux/amd64` and `linux/arm64`.

By contributing you agree that your work is licensed under the [MIT license](LICENSE).
