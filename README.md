# headless-music-player

Play music on a headless Raspberry Pi and control it from a web UI in your browser.

## Stack

- **Backend** — Flask + pygame mixer for audio, serves the API and the built UI
- **Frontend** — Svelte, Vite, Tailwind
- **Docker** — image built for Raspberry Pi, with ALSA/SDL audio in the container

## Running it

```bash
cd backend
pip install -r requirements.txt
python app.py
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Docker: `python build_docker.py`

## License

MIT
