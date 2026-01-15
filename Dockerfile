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

# Environment variables for audio
ENV PYGAME_HIDE_SUPPORT_PROMPT=1
ENV SDL_AUDIODRIVER=alsa

# Create music directory mount point
RUN mkdir -p /app/music

# Expose the Flask port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/status || exit 1

# Run the application
CMD ["python", "app.py"]
