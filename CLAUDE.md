# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Headless Music Player: plays music on a Raspberry Pi with no screen. One process: a `PlayerEngine` thread owns the pygame mixer, the queue and the saved state; Flask serves a server-rendered UI (Jinja + Tailwind/daisyUI) and a JSON API that the UI uses. [docs/DESIGN.md](docs/DESIGN.md) describes the engine, queue rules, persistence and limitations; read the relevant section before changing behavior.

## Commands

```bash
pip install -e ".[dev]"
pytest                                   # no sound card needed (fake backend; pygame tests use SDL's dummy driver)
ruff check .
python scripts/build_css.py              # app.css (downloads the Tailwind CLI + daisyUI into .tools/ once)
python scripts/build_css.py --watch      # while editing templates or app.js
python -m headless_music_player --dev    # :8000; SDL_AUDIODRIVER=dummy without a sound card
```

Release: `scripts/build.py` writes the version into `headless_music_player/__init__.py` and `pyproject.toml` and builds the image; a `vX.Y.Z` tag runs `.github/workflows/release.yml`.

## Architecture

- `app.py`: `create_app(settings, backend, start)` builds the `Runtime` (library, engine) and registers `web/`. Gunicorn uses `headless_music_player.app:create_app()`. Exactly one process.
- `engine.py`: `PlayerEngine`. Public methods are thread-safe and run as commands on the engine thread (`_call`); `_`-prefixed methods run only there. `tick()` detects track ends, retries the audio device, saves. `snapshot()` returns a frozen `Snapshot`. Refusals raise `CommandError(message, status)`.
- `playqueue.py`: `PlayQueue`, a pure model (entries with ids, insertion and shuffled orders, current entry, repeat).
- `audio/`: `AudioBackend` protocol, `PygameBackend`, `FakeBackend` (injectable clock).
- `library/`: `Library` (scan with index cache in `cache/library.json`, track id = path in the music folder, hashed cover files, `add_file` for single files), `metadata.py`, `uploads.py` (safe names, temp file + audio check + rename, duplicates), `loudness.py` (BS.1770 LUFS via miniaudio + numpy), `analyzer.py` (`LoudnessAnalyzer` background thread; `Runtime` starts it).
- `store.py`: `StateStore` (versioned `state.json`, atomic writes, 0.1 migration). `fsutil.py`: atomic write helpers.
- `web/`: `api.py` (JSON API), `views.py` (page and partials), `validate.py` (body checks raising `ApiError`), `serialize.py` (shared JSON shapes).
- `templates/`, `static/js/app.js`: the UI; the script posts actions, polls `/api/state`, swaps partials on `queue_version`/`library_version` changes, and exposes `window.hmp` (toast, refresh). `static/js/upload.js` + `partials/upload_modal.html`: the upload modal.

## Conventions

- Only the engine changes playback or the queue, and only on its thread. Add behavior as an engine command plus a test in `tests/test_engine.py`.
- Validate every request field in `web/validate.py` helpers; never let bad input reach the engine as a 500.
- Mono output (`MIXER_SETTINGS`) is intentional.
- Output volume is always set through `PlayerEngine._apply_volume()` (user volume × normalization gain); never call `backend.set_volume` directly.
- No Node or frontend framework; new UI goes into templates with Tailwind/daisyUI classes. Rebuild the CSS after adding classes.
- There are no saved playlists; there is one global queue, which may contain duplicates.
