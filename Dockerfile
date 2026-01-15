# Headless Music Player - Raspberry Pi Docker Image
FROM python:3.11-slim-bookworm

# Install system dependencies for pygame/SDL audio
RUN apt-get update && apt-get install -y --no-install-recommends \
    libasound2-dev \
    libsdl2-mixer-2.0-0 \
    libsdl2-2.0-0 \
    alsa-utils \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application
COPY backend/ .

# Environment variables for audio and paths
ENV PYGAME_HIDE_SUPPORT_PROMPT=1
ENV SDL_AUDIODRIVER=alsa
ENV MUSIC_FOLDER=/app/music
ENV CONFIG_FOLDER=/app/config
ENV CACHE_FOLDER=/app/cache
ENV PLAYLISTS_FOLDER=/app/playlists

# Create mount point directories
RUN mkdir -p /app/music /app/config /app/cache /app/playlists

# Expose the Flask port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/status || exit 1

# Run with gunicorn for production
# - 1 worker (required for pygame audio state)
# - 4 threads for handling concurrent requests
# - 120s timeout for long operations
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "1", "--threads", "4", "--timeout", "120", "app:app"]
