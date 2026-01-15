# Configuration management for the music player
import os
import json
import logging

logger = logging.getLogger(__name__)

# Base paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MUSIC_FOLDER = os.environ.get('MUSIC_FOLDER', os.path.join(BASE_DIR, 'music'))
PLAYLISTS_FOLDER = os.path.join(BASE_DIR, 'playlists')
CONFIG_FILE = os.path.join(BASE_DIR, 'config', 'config.json')
COVERS_CACHE_FOLDER = os.path.join(BASE_DIR, 'cache', 'covers')

# Supported audio formats
SUPPORTED_FORMATS = ['.mp3', '.wav', '.ogg', '.flac']

# Default settings
DEFAULT_VOLUME = 0.5
POSITION_POLL_INTERVAL_MS = 500

# Ensure directories exist
def ensure_directories():
    """Create necessary directories if they don't exist."""
    dirs = [MUSIC_FOLDER, PLAYLISTS_FOLDER, COVERS_CACHE_FOLDER, os.path.dirname(CONFIG_FILE)]
    for d in dirs:
        os.makedirs(d, exist_ok=True)
        logger.debug(f"Ensured directory exists: {d}")

ensure_directories()
