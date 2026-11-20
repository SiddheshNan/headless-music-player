# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Headless Music Player: plays music on a Raspberry Pi with no screen. A Flask app owns the sound card through the pygame mixer, keeps the player state in memory (saved to `state.json`) and serves a server-rendered web UI (Jinja + Tailwind/daisyUI) and a JSON API that the UI uses. [docs/DESIGN.md](docs/DESIGN.md) describes startup, state, persistence and known limitations; read the relevant section before changing behavior.

## Commands

```bash
pip install -e ".[dev]"
python scripts/build_css.py              # app.css (downloads the Tailwind CLI + daisyUI into .tools/ once)
python scripts/build_css.py --watch      # while editing templates or app.js
python -m headless_music_player --dev    # :8000; SDL_AUDIODRIVER=dummy without a sound card
ruff check .
```

There are no tests yet. `create_app(start=False)` builds the app without touching audio, for tests. Release: `scripts/build.py` writes the version into `headless_music_player/__init__.py` and `pyproject.toml` and builds the image; a `vX.Y.Z` tag runs `.github/workflows/release.yml`.

## Architecture

- `app.py`: `create_app()` registers the blueprints and calls `start_player()` once (load state, open mixer, scan, restore, start the background loop). Gunicorn uses `headless_music_player.app:create_app()`. Exactly one process.
- `state.py`: `STATE`, the re-entrant `lock`, `save_state()` (atomic: temp file, fsync, rename; skipped when unchanged), `snapshot()`, queue navigation helpers.
- `services/player.py` (mixer, position estimate), `services/queue.py` (global queue, shuffle, repeat), `services/library.py` (scan, tags, cover cache).
- `routes/api.py`: JSON API under `/api`; `public_state()` builds the client view from a snapshot. `routes/views.py`: `/`, `/partials/queue`, `/partials/library`.
- `templates/`: `index.html`, `partials/`, `macros/icons.html` (inline Lucide icons, `cover()` macro). `static/js/app.js` sends actions, polls `/api/state` and swaps partials; no framework.

## Conventions

- Change `STATE` only under `lock`; persist with `update_playback`/`update_queue` or `save_state()`. Never put derived fields into `STATE`.
- Mono output (`MIXER_SETTINGS`) is intentional.
- No Node or frontend framework; new UI goes into templates, with Tailwind/daisyUI classes. Rebuild the CSS after adding classes.
- There are no saved playlists; there is one global queue.
