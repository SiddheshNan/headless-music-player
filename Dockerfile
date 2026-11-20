# The CSS is the same on every platform, so build it natively on the build machine.
FROM --platform=$BUILDPLATFORM python:3.11-slim-bookworm AS css
WORKDIR /src
COPY scripts/build_css.py scripts/
COPY headless_music_player/templates headless_music_player/templates
COPY headless_music_player/static headless_music_player/static
RUN python scripts/build_css.py

FROM python:3.11-slim-bookworm

# SDL (bundled in the pygame wheel) plays through ALSA.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libasound2-dev \
    libsdl2-mixer-2.0-0 \
    libsdl2-2.0-0 \
    alsa-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml README.md ./
COPY headless_music_player/ headless_music_player/
COPY --from=css /src/headless_music_player/static/css/app.css headless_music_player/static/css/app.css
RUN pip install --no-cache-dir .

# Both are meant to be volumes: data/ holds state.json and the cover cache.
RUN mkdir -p /app/music /app/data
ENV HMP_MUSIC_DIR=/app/music \
    HMP_RUNTIME_DIR=/app/data \
    PYGAME_HIDE_SUPPORT_PROMPT=1 \
    SDL_AUDIODRIVER=alsa \
    PYTHONUNBUFFERED=1

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4)"

# Exactly one worker: the audio device and the player state live in that process.
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "1", "--threads", "4", "--timeout", "120", \
     "--graceful-timeout", "5", "headless_music_player.app:create_app()"]
