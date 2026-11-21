# Design

How Headless Music Player works inside. Read the relevant section before changing behavior, and update it in the same pull request.

## Overview

One Python process owns the sound card, the player state and the web server. The browser is a remote control; no audio goes to it.

```
browser ──HTTP──> web/ (Flask)        validate input, call the engine, return a snapshot
                    │  commands (thread-safe calls)        ▲ snapshots (read without locks)
                    ▼                                       │
                  engine.py  PlayerEngine: one thread runs every command and tick
                    ├── playqueue.py   PlayQueue: pure queue model (no I/O)
                    ├── audio/         AudioBackend: PygameBackend, FakeBackend for tests
                    ├── library/       Library: folder index, tags, covers (own cache)
                    │                  + LoudnessAnalyzer: background loudness measurement
                    └── store.py       StateStore: state.json, versioned, atomic
```

There must be exactly one process. Docker runs gunicorn with one worker; a second worker would open the sound card again and keep its own state.

## Engine

`PlayerEngine` is the only code that changes playback or the queue, and the only code that calls the audio backend. Public methods (`toggle()`, `next()`, `add_to_queue()`, …) put a command on a queue and wait for the engine thread to run it, so commands never overlap and there is nothing to lock. Between commands the thread ticks every 250 ms:

- **End of track:** when the backend reports the file finished, advance (`queue.next(manual=False)`, which honors repeat "one"). At the end of the queue it stops and rewinds, so Play starts over.
- **Missing sound card:** if the device couldn't be opened (common at boot, before ALSA is ready), retry every 5 s. Commands keep working meanwhile; once the device appears, playback starts where the state says it should.
- **Saving:** see below.

After each command and tick the engine publishes a frozen `Snapshot` (status, position and when it was taken, current entry, the queue as a tuple, modes, audio availability, and `version`/`queue_version` counters). Web handlers read it without touching engine state. `queue_version` changes only when the queue's entries, order, current entry or modes change; the UI re-renders the queue only then.

Rules worth knowing:

- **Next** always moves on; repeat "one" only replays when a track ends by itself. **Previous** restarts the track when more than 3 s in.
- **Play with nothing loaded** (after a restart, a stop, the end of the queue, or a seek while paused) starts the current entry from the remembered position.
- **Playing a library track** inserts it after the current entry and plays it; the rest of the queue stays. Playing the track that's already current restarts it.
- **Removing the current entry** plays the one that took its place (or stops at the end).
- **Unplayable entries** (file gone or unreadable) are skipped.
- **Seek while paused** just remembers the position; Resume plays from there. Formats that can't seek return an error.

With `threaded=False` commands run on the caller's thread and `tick()` is called by hand. The tests use that with `FakeBackend` and a fake clock.

## Queue model

`PlayQueue` holds `Entry(id, track_id)` objects. Entry ids make duplicates possible and keep references stable while the queue changes. It keeps two orders: insertion order, and (while shuffle is on) a shuffled order of entry ids with the current entry first. Turning shuffle off always goes back to insertion order; adding, inserting and removing update both. "Shuffle all" queues the library in its order with a shuffled play order, so unshuffling restores the library order.

## Audio backend

`AudioBackend` is a small protocol: `open`, `load`, `play(start_ms)`, `pause`, `resume`, `stop`, `seek`, `set_volume`, `position_ms`, `is_finished`. `open` raises `AudioUnavailableError`; `load` raises `BackendError`.

`PygameBackend` sets `SDL_NO_SIGNAL_HANDLERS`, because SDL otherwise takes over SIGTERM when nothing else handles it and ignores it, so the player couldn't be stopped without gunicorn. It opens the mixer at 44.1 kHz, 16-bit, **mono** (one speaker, by design), with a 2048-sample buffer against crackling on the Pi. The position is `mixer.music.get_pos()` (which counts from `play()` and stops while paused) plus an offset for where playback started or was seeked to, so it doesn't drift like a wall clock. `get_busy()` is also False while paused, so the backend tracks pause itself to tell "paused" from "finished".

## Library

`Library` walks the music folder, subfolders included (hidden files and folders skipped), for `.mp3`, `.flac`, `.ogg` and `.wav`. A track's id is its path inside the music folder with forward slashes; only ids from the index are turned into paths, so clients can't name arbitrary files.

Tags are read with mutagen (ID3 frames for MP3/WAV, Vorbis comments for FLAC/OGG). Untagged files named "Artist - Title" are split into both. Embedded cover art is stored in `cache/covers/` named by a hash of the image (shared covers are stored once, and the URLs can be cached forever); covers no longer used are deleted after a scan.

The index is saved to `cache/library.json` with each file's size and modification time. At startup it's loaded first, then a scan re-reads only files that changed. A scan builds a new index and swaps it in, so readers never see a half-built one. **Rescan** runs a scan, then tells the engine so clients refresh.

## Volume normalization

Songs are mastered at very different levels, so the player evens them out the way streaming apps do: every song's loudness is measured once, and its volume is scaled to bring it to a target.

- **Measuring** (`library/loudness.py`): miniaudio decodes the file in 100 ms chunks to mono at 44.1 kHz (mono is what the speaker plays). Each chunk is K-weighted in the frequency domain with numpy (the BS.1770 filter's response applied to the chunk's spectrum, so no SciPy is needed), and the integrated loudness in LUFS is computed from 400 ms blocks with the standard -70 LUFS absolute and -10 LU relative gates. A 997 Hz sine at full scale reads -3.01 LUFS, as the standard specifies. Silent files have no loudness.
- **Analyzer** (`library/analyzer.py`): a background thread, at lowered CPU priority on Linux, measures every song that hasn't been measured yet, starting with the current and next song in the queue. Results are stored on the `Track` (`loudness`, `analyzed`) and saved with the library index every few songs, so each file is analyzed once. A scan or upload wakes it. A result for a file that changed while it was being measured is discarded.
- **Applying** (engine): gain = target − measured loudness, limited to +12/−24 dB. The output volume is the user's volume × gain, capped at full scale, since the mixer can't amplify; quiet songs are lifted only as far as the user's volume leaves room for. It's set when a song starts, when the volume or settings change, and when the playing song's measurement arrives. Songs not measured yet play at the user's volume.
- **Settings**: on by default; the targets are quiet (−19 LUFS), normal (−14) and loud (−11), as in common streaming apps. Both are saved in `state.json`.

## Settings page

`/settings` (`templates/settings.html`, `static/js/settings.js`) shows the normalization toggle and target, the analysis progress (polled every 2 s), the music folder with a rescan button, and the version, audio status and data folder. Each change is saved immediately through `POST /api/settings`.

## Uploads

`POST /api/library/upload` takes one file per request (multipart field `file`), so the UI can show progress per file. `library/uploads.py`:

1. Cleans the name: the last path component only, no control or reserved characters, no leading dots; spaces and non-Latin letters stay. Only supported extensions are accepted.
2. Streams the body to a hidden temp file in the music folder (the scan skips hidden files), fsyncs it and checks with mutagen that it's audio with a length.
3. If a file with that name exists and has the same content, it's reported as a duplicate; otherwise the new file gets " (2)", " (3)"… Choosing the name and renaming into it happen under one lock.
4. Renames it into the music folder root and indexes just that file (`Library.add_file`), so it's playable at once without a rescan.

The size limit is `HMP_MAX_UPLOAD_MB` (Flask's `MAX_CONTENT_LENGTH`); larger requests get a 413.

The upload modal (`partials/upload_modal.html`, `static/js/upload.js`) collects files from the file picker or from dropping anywhere on the page, adding to the list on every drop and skipping files already in it. Unsupported or too-large files are flagged before uploading. Upload sends them one at a time with XHR upload progress; each row shows its own spinner, progress and result, and the header button shows a spinner while uploads continue in the background. Finished uploads can be added to the queue in one click.

## State and persistence

`state.json` (version 2) holds `volume`, `status`, `position_ms` and the queue (`entries`, `shuffled`, `current`, `repeat`). `StateStore` writes it to a temp file, fsyncs, renames over the old file and fsyncs the folder, so a power cut leaves the old or the new file, never a broken one. Before 0.2 the file was rewritten in place every second, and a reboot could leave it empty, which reset the volume to 50% and lost the queue. An unreadable file is kept as `state.json.corrupt` and the player starts fresh. The 0.1 format is migrated on load.

The engine saves at most once a second after a change, every 5 seconds while playing (for the position), and on shutdown (`atexit`, which `docker stop` triggers). Unchanged state isn't rewritten, which spares SD cards.

## Web

`web/api.py` is the JSON API; `web/validate.py` checks bodies (types, ranges, required fields), so malformed requests get a 400 and never a 500. Engine refusals (`CommandError`) map to 404/409 with a message. Every error body is `{"error": "message"}`. Most action endpoints answer with the new state.

The UI is server-rendered: `web/views.py` renders `index.html` and the `partials/queue.html` and `partials/library.html` fragments. `static/js/app.js` (no framework, no build step) sends actions, renders the returned state, polls `/api/state` every second while the tab is visible, moves the progress bar between polls, and swaps in a partial when `queue_version` or `library_version` changes.

Styles are Tailwind CSS v4 with daisyUI v5, compiled by the standalone CLI (`scripts/build_css.py`, pinned versions) from `static/css/input.css`, which also defines the `player-dark` and `player-light` themes. `app.css` is gitignored; the Docker image builds it. Icons are inline Lucide SVGs. Nothing loads from the internet.

## Configuration

| Variable | Default | |
|---|---|---|
| `HMP_RUNTIME_DIR` | `<repo>/runtime` (`/app/data` in Docker) | `state.json` and `cache/` |
| `HMP_MUSIC_DIR` | `$HMP_RUNTIME_DIR/music` (`/app/music` in Docker) | the music folder |
| `HMP_HOST`, `HMP_PORT` | `0.0.0.0`, `8000` | for `python -m headless_music_player` |
| `HMP_MAX_UPLOAD_MB` | `500` | largest song that can be uploaded |
| `SDL_AUDIODRIVER` | `alsa` in Docker | `dummy` runs without a sound card |

Tuning constants (tick, retry and save intervals, mixer settings) are in `config.py`.

## Known limitations

- No login. Keep it on a private network ([SECURITY.md](../SECURITY.md)).
- Seeking depends on the format's support in SDL_mixer.
- The library isn't watched; press Rescan after adding music.
- Docker images are built for `linux/amd64` and `linux/arm64`; 32-bit Raspberry Pi OS isn't supported.
