# Changelog

Notable changes to Headless Music Player. Versions follow [semantic versioning](https://semver.org).

## Unreleased (0.2.0)

### New design

- **One engine thread owns the player.** Web requests send commands to it and read immutable snapshots, so the audio device and the queue are never touched from two threads at once. Replaces the shared state dictionary and locks.
- **The queue is a separate, tested model.** Entries have ids, so a track can be queued more than once. Turning shuffle off always restores the order tracks were added in.
- **Audio behind an interface**, with a fake backend: the whole engine is tested without a sound card. `pytest` runs in CI.
- **Library index cache** (`cache/library.json`): a restart only reads tags from files that changed. Covers are stored once per image and pruned when unused.
- **Versioned state file** (`state.json` version 2), migrated automatically from 0.1.
- **New web UI.** Server-rendered with Jinja, styled with Tailwind CSS and daisyUI, light and dark; the separate Svelte frontend is gone. Works offline: no fonts or scripts from the internet.
- **New repository layout**: the `headless_music_player` package at the root, `pyproject.toml`, `docker-compose.yml`, `scripts/build.py` (replaces `build_docker.py`), tests, CI and release workflows.

### Added

- **Upload songs from the browser.** An Upload button opens a modal: drop songs anywhere on the page or browse, keep adding more, remove any with ✕, then upload them one by one with progress for each. Duplicates are detected, name clashes get a number, and uploaded songs can be queued in one click. `POST /api/library/upload`; size limit `HMP_MAX_UPLOAD_MB` (500 by default).
- **Play next** in the library, next to Add to queue.
- Subfolders of the music folder are scanned. Track ids are paths inside the music folder.
- Untagged files named "Artist - Title" show the artist and title.
- If the sound card isn't ready at boot, the player waits for it (retrying every 5 s, with a notice in the UI) and then starts playing.
- `/api/health`. Action endpoints answer with the new state.

### Changed

- Playing a track from the library inserts it after the current track instead of replacing the whole queue.
- Playlists are removed: there is one global queue. The `/api/playlists*` endpoints are gone.
- API: tracks are addressed by `track_id` and queue entries by `entry_id`. `POST /api/queue/remove` is now `DELETE /api/queue/<entry_id>`, `POST /api/queue/set` is `POST /api/queue`, `POST /api/library/reload` is `POST /api/library/rescan`, and covers are at `/api/library/covers/<name>`. `/api/playback/resume` and `/api/playback/position` are gone (use `/api/playback/play` and `/api/state`). Errors are always `{"error": "message"}`.
- The position comes from the mixer's own clock instead of the wall clock, so it no longer drifts.
- Configuration through `HMP_RUNTIME_DIR`, `HMP_MUSIC_DIR`, `HMP_HOST` and `HMP_PORT` replaces `MUSIC_FOLDER`, `CONFIG_FOLDER`, `CACHE_FOLDER` and `PLAYLISTS_FOLDER`.
- State is written at most once a second after a change and every 5 seconds while playing, and not at all when nothing changed, to spare SD cards.

### Fixed

- `python -m headless_music_player` ignored SIGTERM (SDL took over the signal), so `kill` didn't stop it.
- `--dev` didn't reload changed templates.
- After a power cut or a reboot of the Pi, the volume could go back to 50% and the queue be lost. The state was rewritten in place every second, so an interrupted write could leave an empty or partial file, which then failed to load. It's now written atomically, and an unreadable file is kept as `state.json.corrupt`.
- After a restart while paused, pressing Play continued the audio but showed the progress from 0:00.
- Next did nothing useful with repeat "one": it replayed the same track. Repeat "one" now only applies when a track ends by itself.
- Play after Stop or the end of the queue showed "playing" but played nothing. It now starts the queue.
- After "Shuffle all", turning shuffle off didn't restore the library order.
- Removing the playing track from the queue left it playing while another track was highlighted. The next track now plays.
- A sound card that wasn't ready at boot crashed the app in a restart loop.
- The API accepted unknown tracks and malformed values (500 errors, or tracks that couldn't play). Every field is now checked: bad requests get a 400 or 404 with a message.
- `/api/state` wrote `current_track` and `upcoming` into the saved state.
- A track removed from the queue came back when shuffle was turned off.
- The Docker health check called `curl`, which the image doesn't have, so the container was always unhealthy.

### Upgrading from 0.1

The state file moved from `config/config.json` to `data/state.json`; it's converted on first start. With Docker Compose, from the folder you ran `build_docker.py` in:

```bash
docker rm -f music-player
mkdir -p data && cp config/config.json data/state.json
docker compose up -d
```

`music/` stays where it is. `config/`, `cache/` and `playlists/` are no longer used and can be deleted.

## v0.1.0

First version: Flask + pygame backend, Svelte UI, saved playlists, Docker image for the Raspberry Pi.
