# Changelog

Notable changes to Headless Music Player. Versions follow [semantic versioning](https://semver.org).

## Unreleased (0.2.0)

- **New web UI.** Server-rendered with Jinja, styled with Tailwind CSS and daisyUI, light and dark. The separate Svelte frontend is gone; a small script sends actions and refreshes the page's parts. Works offline: no fonts or scripts from the internet.
- **Playlists removed.** There is one global queue. The `/api/playlists*` endpoints are gone.
- Fixed: after a power cut or a reboot of the Pi, the volume could go back to 50% and the queue be lost. The state was rewritten in place every second, so an interrupted write could leave an empty or partial file, which failed to load and was replaced by the defaults. It's now written to a temp file, fsynced and renamed, and an unreadable file is kept as `state.json.corrupt` instead of being overwritten.
- Fixed: `/api/state` wrote `current_track` and `upcoming` into the saved state.
- Fixed: requests and the background loop changed the state without a lock.
- Fixed: a track removed from the queue came back when shuffle was turned off.
- Fixed: the Docker health check called `curl`, which the image doesn't have, so the container was always unhealthy.
- The position is saved every 5 seconds instead of every second, and nothing is written while paused, to spare SD cards.
- Adding a track that's already queued now says so (`"added": false`) instead of claiming success.
- New `/api/health` endpoint.
- New repository layout: the `headless_music_player` package at the root, `pyproject.toml`, `docker-compose.yml`, `scripts/build.py` (replaces `build_docker.py`), CI and release workflows.
- Configuration through `HMP_RUNTIME_DIR`, `HMP_MUSIC_DIR`, `HMP_HOST` and `HMP_PORT` replaces `MUSIC_FOLDER`, `CONFIG_FOLDER`, `CACHE_FOLDER` and `PLAYLISTS_FOLDER`.

### Upgrading from 0.1

The state file moved from `config/config.json` to `data/state.json`. With Docker Compose, from the folder you ran `build_docker.py` in:

```bash
docker rm -f music-player
mkdir -p data && cp config/config.json data/state.json
docker compose up -d
```

`music/` stays where it is. `config/`, `cache/` and `playlists/` are no longer used and can be deleted.

## v0.1.0

First version: Flask + pygame backend, Svelte UI, saved playlists, Docker image for the Raspberry Pi.
