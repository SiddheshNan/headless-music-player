# Playlist management service
import os
import json
import random
import logging

from config import PLAYLISTS_FOLDER
from models.state import STATE, update_queue, save_state
from services.library import get_all_filenames

logger = logging.getLogger(__name__)


def get_saved_playlists():
    """Get list of saved playlist names."""
    if not os.path.exists(PLAYLISTS_FOLDER):
        return []
    
    playlists = []
    for filename in os.listdir(PLAYLISTS_FOLDER):
        if filename.endswith('.json'):
            playlists.append(filename[:-5])  # Remove .json extension
    
    return sorted(playlists)


def save_playlist(name, tracks):
    """Save a playlist to disk."""
    os.makedirs(PLAYLISTS_FOLDER, exist_ok=True)
    
    filepath = os.path.join(PLAYLISTS_FOLDER, f"{name}.json")
    
    playlist_data = {
        "name": name,
        "tracks": tracks
    }
    
    with open(filepath, 'w') as f:
        json.dump(playlist_data, f, indent=2)
    
    logger.info(f"Saved playlist: {name} ({len(tracks)} tracks)")
    return True


def load_playlist(name):
    """Load a playlist from disk."""
    filepath = os.path.join(PLAYLISTS_FOLDER, f"{name}.json")
    
    if not os.path.exists(filepath):
        logger.warning(f"Playlist not found: {name}")
        return None
    
    with open(filepath, 'r') as f:
        data = json.load(f)
    
    return data


def delete_playlist(name):
    """Delete a saved playlist."""
    filepath = os.path.join(PLAYLISTS_FOLDER, f"{name}.json")
    
    if os.path.exists(filepath):
        os.remove(filepath)
        logger.info(f"Deleted playlist: {name}")
        return True
    
    return False


def set_queue(tracks, start_index=0):
    """Set the current play queue."""
    update_queue(
        tracks=tracks,
        index=start_index,
        original_order=tracks.copy()
    )
    logger.info(f"Queue set: {len(tracks)} tracks, starting at {start_index}")


def add_to_queue(filename):
    """Add a track to the end of the queue."""
    queue = STATE["queue"]
    
    if filename not in queue["tracks"]:
        queue["tracks"].append(filename)
        queue["original_order"].append(filename)
        save_state()
        logger.info(f"Added to queue: {filename}")


def remove_from_queue(index):
    """Remove a track from the queue by index."""
    queue = STATE["queue"]
    
    if 0 <= index < len(queue["tracks"]):
        removed = queue["tracks"].pop(index)
        
        # Adjust current index if needed
        if index < queue["index"]:
            queue["index"] -= 1
        elif index == queue["index"] and queue["index"] >= len(queue["tracks"]):
            queue["index"] = max(0, len(queue["tracks"]) - 1)
        
        save_state()
        logger.info(f"Removed from queue: {removed}")
        return True
    
    return False


def clear_queue():
    """Clear the play queue."""
    update_queue(
        tracks=[],
        index=0,
        original_order=[],
        shuffle=False
    )
    logger.info("Queue cleared")


def toggle_shuffle():
    """Toggle shuffle mode and reshuffle queue if enabling."""
    queue = STATE["queue"]
    
    if queue["shuffle"]:
        # Turning off shuffle - restore original order
        current_track = queue["tracks"][queue["index"]] if queue["tracks"] else None
        queue["tracks"] = queue["original_order"].copy()
        
        # Find current track in original order
        if current_track and current_track in queue["tracks"]:
            queue["index"] = queue["tracks"].index(current_track)
        
        queue["shuffle"] = False
        
    else:
        # Turning on shuffle
        current_track = queue["tracks"][queue["index"]] if queue["tracks"] else None
        
        # Shuffle all tracks except current
        other_tracks = [t for t in queue["tracks"] if t != current_track]
        random.shuffle(other_tracks)
        
        # Put current track at the beginning, followed by shuffled
        if current_track:
            queue["tracks"] = [current_track] + other_tracks
            queue["index"] = 0
        else:
            queue["tracks"] = other_tracks
        
        queue["shuffle"] = True
    
    save_state()
    logger.info(f"Shuffle: {'on' if queue['shuffle'] else 'off'}")
    return queue["shuffle"]


def set_repeat_mode(mode):
    """Set repeat mode: 'off', 'one', or 'all'."""
    if mode not in ['off', 'one', 'all']:
        return False
    
    update_queue(repeat_mode=mode)
    logger.info(f"Repeat mode: {mode}")
    return True


def cycle_repeat_mode():
    """Cycle through repeat modes: off -> all -> one -> off."""
    current = STATE["queue"]["repeat_mode"]
    
    if current == "off":
        new_mode = "all"
    elif current == "all":
        new_mode = "one"
    else:
        new_mode = "off"
    
    set_repeat_mode(new_mode)
    return new_mode


def get_queue():
    """Get the current queue state."""
    return STATE["queue"]


def get_upcoming_tracks(count=10):
    """Get the next N upcoming tracks."""
    queue = STATE["queue"]
    
    if not queue["tracks"]:
        return []
    
    upcoming = []
    start = queue["index"] + 1
    
    for i in range(count):
        idx = start + i
        if idx >= len(queue["tracks"]):
            if queue["repeat_mode"] == "all":
                idx = idx % len(queue["tracks"])
            else:
                break
        
        if idx < len(queue["tracks"]):
            upcoming.append(queue["tracks"][idx])
    
    return upcoming


def play_all(shuffle=False):
    """Create a queue from all library tracks."""
    tracks = get_all_filenames()
    
    if shuffle:
        random.shuffle(tracks)
    
    set_queue(tracks, 0)
    
    if shuffle:
        STATE["queue"]["shuffle"] = True
        save_state()
    
    return tracks
