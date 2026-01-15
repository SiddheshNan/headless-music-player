# State management for the music player
import os
import json
import logging
from config import CONFIG_FILE, DEFAULT_VOLUME

logger = logging.getLogger(__name__)

# Global state
STATE = {
    "playback": {
        "is_paused": True,
        "current_file": "",
        "volume": DEFAULT_VOLUME,
        "position_ms": 0,
        "duration_ms": 0
    },
    "queue": {
        "tracks": [],
        "index": 0,
        "shuffle": False,
        "repeat_mode": "off",  # off, one, all
        "original_order": []   # For unshuffling
    }
}


def load_state():
    """Load state from config file."""
    global STATE
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                saved = json.load(f)
                
            # Merge saved state with defaults (in case new fields were added)
            if "playback" in saved:
                STATE["playback"].update(saved["playback"])
            if "queue" in saved:
                STATE["queue"].update(saved["queue"])
                
            logger.info(f"Loaded state from {CONFIG_FILE}")
        else:
            logger.info("No saved state found, using defaults")
    except Exception as e:
        logger.error(f"Failed to load state: {e}")


def save_state():
    """Save current state to config file."""
    try:
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, 'w') as f:
            json.dump(STATE, f, indent=2)
        logger.debug("State saved")
    except Exception as e:
        logger.error(f"Failed to save state: {e}")


def get_state():
    """Get current state."""
    return STATE


def update_playback(**kwargs):
    """Update playback state."""
    STATE["playback"].update(kwargs)
    save_state()


def update_queue(**kwargs):
    """Update queue state."""
    STATE["queue"].update(kwargs)
    save_state()


def get_current_track():
    """Get the currently playing track filename."""
    queue = STATE["queue"]
    if queue["tracks"] and 0 <= queue["index"] < len(queue["tracks"]):
        return queue["tracks"][queue["index"]]
    return None


def get_next_track():
    """Get the next track based on repeat mode."""
    queue = STATE["queue"]
    
    if not queue["tracks"]:
        return None
    
    if queue["repeat_mode"] == "one":
        return queue["tracks"][queue["index"]]
    
    next_index = queue["index"] + 1
    
    if next_index >= len(queue["tracks"]):
        if queue["repeat_mode"] == "all":
            next_index = 0
        else:
            return None
    
    return queue["tracks"][next_index]


def advance_queue():
    """Move to the next track in queue. Returns the new current track or None."""
    queue = STATE["queue"]
    
    if not queue["tracks"]:
        return None
    
    if queue["repeat_mode"] == "one":
        # Stay on same track
        save_state()
        return queue["tracks"][queue["index"]]
    
    next_index = queue["index"] + 1
    
    if next_index >= len(queue["tracks"]):
        if queue["repeat_mode"] == "all":
            queue["index"] = 0
        else:
            # End of queue, no repeat
            return None
    else:
        queue["index"] = next_index
    
    save_state()
    return queue["tracks"][queue["index"]]


def go_previous():
    """Go to previous track in queue. Returns the new current track or None."""
    queue = STATE["queue"]
    
    if not queue["tracks"]:
        return None
    
    prev_index = queue["index"] - 1
    
    if prev_index < 0:
        if queue["repeat_mode"] == "all":
            prev_index = len(queue["tracks"]) - 1
        else:
            prev_index = 0
    
    queue["index"] = prev_index
    save_state()
    return queue["tracks"][queue["index"]]
