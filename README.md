<p align="center"><img src="assets/logo.svg" width="96" alt="Headless Music Player logo"></p>

<h1 align="center">Headless Music Player</h1>

<p align="center">Play music on a Raspberry Pi with no screen, and control it from any browser on your network.</p>

<p align="center">
  <a href="docs/DESIGN.md">Design</a> ·
  <a href="CHANGELOG.md">Changelog</a> ·
  <a href="CONTRIBUTING.md">Contributing</a>
</p>

> **Status: early.** It works, but expect rough edges and breaking changes before 1.0.

The audio comes out of the Pi itself (3.5 mm jack, USB DAC or HDMI). Your phone or laptop is only the remote, so playback keeps going when you close the page.

## Features

- One global play queue: play, pause, seek, next and previous, shuffle, repeat (off, all, one)
- Library from a folder of `.mp3`, `.flac`, `.ogg` and `.wav` files, with tags, cover art and search
- Picks up where it left off after a restart or power cut: queue, track, position and volume
- A fast, server-rendered web UI that works on phones and desktops, in light and dark
- Mono output, for a single speaker
- One small container; no database, no Node at runtime

## Quick start

You need a Raspberry Pi running 64-bit Raspberry Pi OS (or any Linux with ALSA) and Docker with Compose.

```bash
git clone https://github.com/SiddheshNan/headless-music-player.git
cd headless-music-player
mkdir -p music && cp /path/to/your/songs/* music/
docker compose up -d
```

Open `http://<raspberry-pi-ip>:8000`. Music lives in `music/`; the saved state (`state.json`) and the cover art cache in `data/`. After adding songs, press **Rescan**.

The container needs the sound device: `docker-compose.yml` passes `/dev/snd` and the `audio` group. If you hear nothing, check the Pi's output and level with `alsamixer` on the host.

Keep it on your own network: there is no login, so anyone who can reach port 8000 can control playback ([SECURITY.md](SECURITY.md)).

## Development

You need Python 3.10+. No Node: the CSS is built with the Tailwind standalone CLI, which the script downloads.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python scripts/build_css.py
python -m headless_music_player --dev
```

Open http://localhost:8000. Put a few songs in `runtime/music/`; the state is saved in `runtime/state.json`. Run `python scripts/build_css.py --watch` in a second terminal while you change templates. See [CONTRIBUTING.md](CONTRIBUTING.md) for the layout and conventions.

## Contributing

Issues and pull requests are welcome. Please open an issue to discuss bigger changes first. See [CONTRIBUTING.md](CONTRIBUTING.md), and report security issues as described in [SECURITY.md](SECURITY.md).

## License

[MIT](LICENSE).
