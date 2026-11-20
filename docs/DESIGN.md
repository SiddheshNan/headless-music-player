# Design

How Headless Music Player works inside. Read the relevant section before changing behavior, and update it in the same pull request.

## Overview

One Python process does everything: it owns the sound card through the pygame mixer, keeps the player state in memory, saves it to `state.json`, and serves the web UI and the JSON API with Flask. The browser is a remote control; no audio goes to it.

```
browser ──HTTP──> Flask (routes/api.py, routes/views.py)
                    │
                    ├── services/queue.py   queue order, shuffle, repeat
                    ├── services/player.py  pygame mixer (load, play, pause, seek, volume)
                    ├── services/library.py folder scan, tags, cover cache
                    └── state.py            STATE + lock, atomic save to state.json
background thread ──> every second: detect track end, update position; every 5 s: save
```

There must be exactly one process. Docker runs gunicorn with one worker and four threads; a second worker would open the sound card again and keep its own copy of the state.

## Startup

`create_app()` (gunicorn calls `headless_music_player.app:create_app()`) runs `start_player()` once:

1. `load_state()` reads `state.json`. Only known keys are taken, so fields from older versions or bugs are dropped. A file that can't be parsed is renamed to `state.json.corrupt` and the defaults are used.
2. `init_player()` opens the mixer: 44.1 kHz, 16-bit, **mono** (one speaker, by design), 2048-sample buffer to avoid crackling on the Pi.
3. `scan_library()` indexes the music folder.
4. `restore_state()` sets the saved volume and reloads the current track at the saved position, paused or playing as it was.
5. The background thread starts, and `atexit` saves the state on a clean shutdown.

`create_app(start=False)` skips all of this, for CI and tests without a sound card.

## State and persistence

`state.STATE` has two sections:

- `playback`: `is_paused`, `current_file`, `volume` (0–1), `position_ms`, `duration_ms`
- `queue`: `tracks` (filenames, in play order), `index`, `shuffle`, `repeat_mode` (`off`, `all`, `one`), `original_order` (the order before shuffling)

Request threads and the background thread share it. Every read-modify-write holds `state.lock`, a re-entrant lock that also covers the mixer calls, so services can call each other while holding it.

`save_state()` writes JSON to `state.json.tmp`, fsyncs it, renames it over `state.json` and fsyncs the folder. After a power cut the file is either the old or the new version, never half-written. (Before 0.2 the file was rewritten in place every second, and a reboot could leave it empty, which reset the volume to 50% and lost the queue.) A save is skipped when the JSON is unchanged.

User actions save immediately. The position only changes in memory every second and is saved every `POSITION_SAVE_INTERVAL_S` (5) seconds, so a restart resumes within a few seconds of where it stopped without writing to the SD card every second.

`/api/state` and the templates work on `snapshot()`, a deep copy, and add derived fields (`current_track`, `upcoming`, `queue.version`) to the copy only.

## Playback position

pygame can't tell where playback is, so `player.py` remembers when playback last started (`_play_start_time`) and from where (`_play_start_position`) and adds the elapsed time. Seeking uses `mixer.music.set_pos`, which depends on the codec (it works for MP3 and OGG; see the pygame docs).

A track has ended when the mixer is no longer busy while the state says it's playing. The background loop then calls `next_track()`, which follows the repeat mode.

## Queue

There is one global queue and no saved playlists. The queue holds each file once. Playing a track from the library jumps to it if it's queued and otherwise replaces the queue with that track. Shuffle reorders `tracks` with the current track first and keeps `original_order` to go back to; adding or removing tracks updates both lists.

## Library

`scan_library()` lists the music folder (not subfolders) for `.mp3`, `.flac`, `.ogg` and `.wav`, reads tags with mutagen and writes embedded cover art to `cache/covers/<md5 of path and mtime>.jpg`. The index is kept in memory and rebuilt at startup and on **Rescan**.

## Web UI

The UI is server-rendered: `routes/views.py` renders `templates/index.html` with the state, the queue and the library. `static/js/app.js` (no framework, no build step) then:

- sends every button press to the JSON API and polls `/api/state` every second while the tab is visible, updating the now-playing card in place;
- reloads `/partials/queue` when `queue.version` (a hash of the queue's tracks, index and shuffle) changes, and `/partials/library` after a rescan;
- filters the library in the browser while you type.

Styles are Tailwind CSS v4 with daisyUI v5, compiled by the Tailwind standalone CLI (`scripts/build_css.py`, pinned versions) from `static/css/input.css`, which also defines the `player-dark` and `player-light` themes. The output `app.css` is gitignored; the Docker image builds it in a separate stage. Icons are inline Lucide SVGs in `templates/macros/icons.html`. Nothing is loaded from the internet, so the UI works on a LAN without access to the outside.

## Configuration

| Variable | Default | |
|---|---|---|
| `HMP_RUNTIME_DIR` | `<repo>/runtime` (`/app/data` in Docker) | `state.json` and `cache/covers/` |
| `HMP_MUSIC_DIR` | `$HMP_RUNTIME_DIR/music` (`/app/music` in Docker) | the music folder |
| `HMP_HOST`, `HMP_PORT` | `0.0.0.0`, `8000` | for `python -m headless_music_player` |
| `SDL_AUDIODRIVER` | `alsa` in Docker | `dummy` runs without a sound card |

## Known limitations

- No login. Keep it on a private network ([SECURITY.md](../SECURITY.md)).
- Subfolders of the music folder are not scanned.
- The cover cache is never pruned: changed or deleted files leave their old cover behind.
- The position is estimated from wall-clock time, so it can drift slightly from the audio.
- Docker images are built for `linux/amd64` and `linux/arm64`; 32-bit Raspberry Pi OS isn't supported.
