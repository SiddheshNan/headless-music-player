# Music library service - scanning and metadata extraction
import os
import base64
import hashlib
import logging
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC
from mutagen.flac import FLAC
from mutagen.oggvorbis import OggVorbis
from mutagen import File as MutagenFile

from config import MUSIC_FOLDER, COVERS_CACHE_FOLDER, SUPPORTED_FORMATS

logger = logging.getLogger(__name__)

# In-memory cache of library metadata
LIBRARY_CACHE = {}


def get_file_hash(filepath):
    """Generate a hash for cache key based on file path and mtime."""
    mtime = os.path.getmtime(filepath)
    return hashlib.md5(f"{filepath}:{mtime}".encode()).hexdigest()


def extract_cover_art(filepath):
    """Extract cover art from audio file and cache it."""
    try:
        audio = MutagenFile(filepath)
        if audio is None:
            return None
        
        cover_data = None
        
        # Handle different formats
        if isinstance(audio, MP3):
            if audio.tags:
                for tag in audio.tags.values():
                    if isinstance(tag, APIC):
                        cover_data = tag.data
                        break
        elif hasattr(audio, 'pictures') and audio.pictures:
            cover_data = audio.pictures[0].data
        
        if cover_data:
            # Cache the cover art
            file_hash = get_file_hash(filepath)
            cover_path = os.path.join(COVERS_CACHE_FOLDER, f"{file_hash}.jpg")
            
            with open(cover_path, 'wb') as f:
                f.write(cover_data)
            
            return cover_path
        
    except Exception as e:
        logger.warning(f"Failed to extract cover art from {filepath}: {e}")
    
    return None


def get_track_metadata(filepath):
    """Extract metadata from an audio file."""
    filename = os.path.basename(filepath)
    
    # Default metadata
    metadata = {
        "filename": filename,
        "title": os.path.splitext(filename)[0],
        "artist": "Unknown Artist",
        "album": "Unknown Album",
        "duration_ms": 0,
        "has_cover": False,
        "cover_path": None
    }
    
    try:
        audio = MutagenFile(filepath)
        if audio is None:
            return metadata
        
        # Get duration
        if hasattr(audio, 'info') and hasattr(audio.info, 'length'):
            metadata["duration_ms"] = int(audio.info.length * 1000)
        
        # Get tags based on format
        if isinstance(audio, MP3) and audio.tags:
            tags = audio.tags
            if 'TIT2' in tags:
                metadata["title"] = str(tags['TIT2'])
            if 'TPE1' in tags:
                metadata["artist"] = str(tags['TPE1'])
            if 'TALB' in tags:
                metadata["album"] = str(tags['TALB'])
        elif hasattr(audio, 'tags') and audio.tags:
            tags = audio.tags
            if 'title' in tags:
                metadata["title"] = tags['title'][0]
            if 'artist' in tags:
                metadata["artist"] = tags['artist'][0]
            if 'album' in tags:
                metadata["album"] = tags['album'][0]
        
        # Extract cover art
        cover_path = extract_cover_art(filepath)
        if cover_path:
            metadata["has_cover"] = True
            metadata["cover_path"] = cover_path
        
    except Exception as e:
        logger.warning(f"Failed to read metadata from {filepath}: {e}")
    
    return metadata


def scan_library():
    """Scan music folder and build library cache."""
    global LIBRARY_CACHE
    
    logger.info(f"Scanning music library at {MUSIC_FOLDER}")
    
    if not os.path.exists(MUSIC_FOLDER):
        os.makedirs(MUSIC_FOLDER)
        logger.info(f"Created music folder at {MUSIC_FOLDER}")
        return {}
    
    new_cache = {}
    
    for filename in os.listdir(MUSIC_FOLDER):
        ext = os.path.splitext(filename)[1].lower()
        if ext in SUPPORTED_FORMATS:
            filepath = os.path.join(MUSIC_FOLDER, filename)
            
            # Check if we already have cached metadata
            file_hash = get_file_hash(filepath)
            if filename in LIBRARY_CACHE:
                cached = LIBRARY_CACHE[filename]
                if cached.get("_hash") == file_hash:
                    new_cache[filename] = cached
                    continue
            
            # Extract fresh metadata
            metadata = get_track_metadata(filepath)
            metadata["_hash"] = file_hash
            new_cache[filename] = metadata
            logger.debug(f"Indexed: {filename}")
    
    LIBRARY_CACHE = new_cache
    logger.info(f"Library scan complete: {len(LIBRARY_CACHE)} tracks found")
    
    return LIBRARY_CACHE


def get_library():
    """Get the current library cache."""
    if not LIBRARY_CACHE:
        scan_library()
    return LIBRARY_CACHE


def get_track_info(filename):
    """Get metadata for a specific track."""
    if filename not in LIBRARY_CACHE:
        filepath = os.path.join(MUSIC_FOLDER, filename)
        if os.path.exists(filepath):
            return get_track_metadata(filepath)
        return None
    return LIBRARY_CACHE[filename]


def get_cover_base64(filename):
    """Get cover art as base64 string."""
    track = get_track_info(filename)
    if track and track.get("cover_path") and os.path.exists(track["cover_path"]):
        with open(track["cover_path"], 'rb') as f:
            return base64.b64encode(f.read()).decode('utf-8')
    return None


def get_all_filenames():
    """Get list of all track filenames."""
    return list(get_library().keys())
