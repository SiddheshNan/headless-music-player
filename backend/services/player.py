# Audio playback service using pygame
import os
import time
import logging
import threading

os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
from pygame import mixer

from config import MUSIC_FOLDER
from models.state import (
    STATE, update_playback, save_state, 
    get_current_track, advance_queue, go_previous
)
from services.library import get_track_info

logger = logging.getLogger(__name__)

# Track playback timing
_play_start_time = 0
_play_start_position = 0
_is_initialized = False

# Lock for thread-safe operations
_player_lock = threading.Lock()


def init_player():
    """Initialize the pygame mixer."""
    global _is_initialized
    if not _is_initialized:
        mixer.init()
        _is_initialized = True
        logger.info("Player initialized")


def _get_filepath(filename):
    """Get full path for a music file."""
    return os.path.join(MUSIC_FOLDER, filename)


def play(filename, start_position_ms=0):
    """Start playing a track."""
    global _play_start_time, _play_start_position
    
    with _player_lock:
        filepath = _get_filepath(filename)
        
        if not os.path.exists(filepath):
            logger.error(f"File not found: {filepath}")
            return False
        
        try:
            # Get track info for duration
            track_info = get_track_info(filename)
            duration_ms = track_info.get("duration_ms", 0) if track_info else 0
            
            # Load and play
            mixer.music.load(filepath)
            
            # Seek to position if specified
            if start_position_ms > 0:
                mixer.music.play()
                mixer.music.set_pos(start_position_ms / 1000.0)
            else:
                mixer.music.play()
            
            # Track timing
            _play_start_time = time.time()
            _play_start_position = start_position_ms
            
            # Update state
            update_playback(
                is_paused=False,
                current_file=filename,
                position_ms=start_position_ms,
                duration_ms=duration_ms
            )
            
            logger.info(f"Playing: {filename}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to play {filename}: {e}")
            return False


def pause():
    """Pause playback."""
    global _play_start_position
    
    with _player_lock:
        if STATE["playback"]["is_paused"]:
            return False
        
        # Save current position before pausing
        _play_start_position = get_position()
        
        mixer.music.pause()
        update_playback(is_paused=True, position_ms=_play_start_position)
        logger.info("Paused")
        return True


def resume():
    """Resume playback."""
    global _play_start_time
    
    with _player_lock:
        if not STATE["playback"]["is_paused"]:
            return False
        
        _play_start_time = time.time()
        mixer.music.unpause()
        update_playback(is_paused=False)
        logger.info("Resumed")
        return True


def stop():
    """Stop playback."""
    global _play_start_position
    
    with _player_lock:
        mixer.music.stop()
        _play_start_position = 0
        update_playback(
            is_paused=True,
            current_file="",
            position_ms=0,
            duration_ms=0
        )
        logger.info("Stopped")


def seek(position_ms):
    """Seek to a position in the current track."""
    global _play_start_time, _play_start_position
    
    with _player_lock:
        if not STATE["playback"]["current_file"]:
            return False
        
        try:
            position_sec = position_ms / 1000.0
            mixer.music.set_pos(position_sec)
            
            _play_start_time = time.time()
            _play_start_position = position_ms
            
            update_playback(position_ms=position_ms)
            logger.debug(f"Seeked to {position_ms}ms")
            return True
            
        except Exception as e:
            logger.error(f"Seek failed: {e}")
            return False


def get_position():
    """Get current playback position in milliseconds."""
    if STATE["playback"]["is_paused"]:
        return STATE["playback"]["position_ms"]
    
    if not mixer.music.get_busy():
        return STATE["playback"]["position_ms"]
    
    # Calculate position based on elapsed time
    elapsed = (time.time() - _play_start_time) * 1000
    position = _play_start_position + elapsed
    
    # Clamp to duration
    duration = STATE["playback"]["duration_ms"]
    if duration > 0 and position > duration:
        position = duration
    
    return int(position)


def set_volume(volume):
    """Set volume level (0.0 to 1.0)."""
    volume = max(0.0, min(1.0, volume))
    mixer.music.set_volume(volume)
    update_playback(volume=volume)
    logger.debug(f"Volume set to {volume}")


def get_volume():
    """Get current volume level."""
    return STATE["playback"]["volume"]


def is_playing():
    """Check if music is currently playing."""
    return mixer.music.get_busy() and not STATE["playback"]["is_paused"]


def next_track():
    """Play the next track in queue."""
    track = advance_queue()
    if track:
        play(track)
        return track
    else:
        stop()
        return None


def prev_track():
    """Play the previous track in queue."""
    # If we're more than 3 seconds in, restart current track
    if get_position() > 3000:
        current = get_current_track()
        if current:
            play(current)
            return current
    
    track = go_previous()
    if track:
        play(track)
        return track
    return None


def on_track_end():
    """Called when a track ends naturally."""
    logger.info("Track ended")
    next_track()


def check_track_ended():
    """Check if the current track has ended and handle it."""
    if STATE["playback"]["current_file"] and not STATE["playback"]["is_paused"]:
        if not mixer.music.get_busy():
            on_track_end()
            return True
    return False


def restore_state():
    """Restore playback state after restart."""
    init_player()
    
    # Set volume
    mixer.music.set_volume(STATE["playback"]["volume"])
    
    # If there was a track playing, load it
    if STATE["playback"]["current_file"]:
        filepath = _get_filepath(STATE["playback"]["current_file"])
        
        if os.path.exists(filepath):
            try:
                mixer.music.load(filepath)
                
                # Seek to saved position
                if STATE["playback"]["position_ms"] > 0:
                    mixer.music.play()
                    mixer.music.set_pos(STATE["playback"]["position_ms"] / 1000.0)
                else:
                    mixer.music.play()
                
                # Pause if it was paused
                if STATE["playback"]["is_paused"]:
                    mixer.music.pause()
                else:
                    global _play_start_time, _play_start_position
                    _play_start_time = time.time()
                    _play_start_position = STATE["playback"]["position_ms"]
                
                logger.info(f"Restored playback: {STATE['playback']['current_file']}")
                
            except Exception as e:
                logger.error(f"Failed to restore playback: {e}")
        else:
            logger.warning(f"Saved track not found: {filepath}")
            update_playback(current_file="", position_ms=0, is_paused=True)
