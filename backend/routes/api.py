# API routes for the music player
import os
from flask import Blueprint, jsonify, request, send_file

from models.state import STATE, get_state
from services import player, library, playlist

api = Blueprint('api', __name__, url_prefix='/api')


# ============== State ==============

@api.route('/state')
def get_full_state():
    """Get the complete player state."""
    state = get_state()
    
    # Add current position
    state["playback"]["position_ms"] = player.get_position()
    
    # Add current track info
    current_file = state["playback"]["current_file"]
    if current_file:
        state["playback"]["current_track"] = library.get_track_info(current_file)
    else:
        state["playback"]["current_track"] = None
    
    # Add upcoming tracks
    state["queue"]["upcoming"] = playlist.get_upcoming_tracks(5)
    
    return jsonify(state)


# ============== Playback Controls ==============

@api.route('/playback/play', methods=['POST'])
def playback_play():
    """Start playing a specific track."""
    data = request.get_json() or {}
    filename = data.get('filename')
    
    if not filename:
        return jsonify({'error': 'filename is required'}), 400
    
    # Check if track exists
    if filename not in library.get_all_filenames():
        return jsonify({'error': 'Track not found'}), 404
    
    # Add to queue if not already there, or find it in queue
    queue = playlist.get_queue()
    if filename in queue["tracks"]:
        # Jump to this track in queue
        idx = queue["tracks"].index(filename)
        queue["index"] = idx
    else:
        # Set as single-track queue
        playlist.set_queue([filename], 0)
    
    if player.play(filename):
        return jsonify({'message': 'Playing', 'filename': filename})
    else:
        return jsonify({'error': 'Failed to play'}), 500


@api.route('/playback/pause', methods=['POST'])
def playback_pause():
    """Pause playback."""
    if player.pause():
        return jsonify({'message': 'Paused'})
    else:
        return jsonify({'error': 'Not playing or already paused'}), 400


@api.route('/playback/resume', methods=['POST'])
def playback_resume():
    """Resume playback."""
    if player.resume():
        return jsonify({'message': 'Resumed'})
    else:
        return jsonify({'error': 'Not paused'}), 400


@api.route('/playback/toggle', methods=['POST'])
def playback_toggle():
    """Toggle play/pause."""
    if STATE["playback"]["is_paused"]:
        player.resume()
        return jsonify({'message': 'Resumed', 'is_paused': False})
    else:
        player.pause()
        return jsonify({'message': 'Paused', 'is_paused': True})


@api.route('/playback/stop', methods=['POST'])
def playback_stop():
    """Stop playback."""
    player.stop()
    return jsonify({'message': 'Stopped'})


@api.route('/playback/seek', methods=['POST'])
def playback_seek():
    """Seek to a position."""
    data = request.get_json() or {}
    position_ms = data.get('position_ms')
    
    if position_ms is None:
        return jsonify({'error': 'position_ms is required'}), 400
    
    if player.seek(int(position_ms)):
        return jsonify({'message': 'Seeked', 'position_ms': position_ms})
    else:
        return jsonify({'error': 'Seek failed'}), 400


@api.route('/playback/volume', methods=['POST'])
def playback_volume():
    """Set volume level."""
    data = request.get_json() or {}
    volume = data.get('volume')
    
    if volume is None:
        return jsonify({'error': 'volume is required'}), 400
    
    player.set_volume(float(volume))
    return jsonify({'message': 'Volume set', 'volume': volume})


@api.route('/playback/next', methods=['POST'])
def playback_next():
    """Skip to next track."""
    track = player.next_track()
    if track:
        return jsonify({'message': 'Next track', 'filename': track})
    else:
        return jsonify({'message': 'End of queue'})


@api.route('/playback/prev', methods=['POST'])
def playback_prev():
    """Go to previous track."""
    track = player.prev_track()
    if track:
        return jsonify({'message': 'Previous track', 'filename': track})
    else:
        return jsonify({'error': 'No previous track'}), 400


@api.route('/playback/position')
def playback_position():
    """Get current playback position (for polling)."""
    return jsonify({
        'position_ms': player.get_position(),
        'duration_ms': STATE["playback"]["duration_ms"],
        'is_paused': STATE["playback"]["is_paused"],
        'is_playing': player.is_playing()
    })


# ============== Library ==============

@api.route('/library')
def get_library():
    """Get all tracks in the library with metadata."""
    lib = library.get_library()
    
    # Convert to list and remove internal fields
    tracks = []
    for filename, meta in lib.items():
        track = {k: v for k, v in meta.items() if not k.startswith('_')}
        tracks.append(track)
    
    # Sort by title
    tracks.sort(key=lambda x: x.get('title', '').lower())
    
    return jsonify(tracks)


@api.route('/library/reload', methods=['POST'])
def reload_library():
    """Rescan the music library."""
    library.scan_library()
    return get_library()


@api.route('/library/cover/<filename>')
def get_cover(filename):
    """Get cover art for a track."""
    track = library.get_track_info(filename)
    
    if track and track.get('cover_path') and os.path.exists(track['cover_path']):
        return send_file(track['cover_path'], mimetype='image/jpeg')
    else:
        # Return placeholder or 404
        return jsonify({'error': 'No cover art'}), 404


# ============== Queue ==============

@api.route('/queue')
def get_queue():
    """Get current queue."""
    queue = playlist.get_queue()
    
    # Add track metadata
    queue_with_meta = {
        'tracks': [],
        'index': queue['index'],
        'shuffle': queue['shuffle'],
        'repeat_mode': queue['repeat_mode']
    }
    
    for filename in queue['tracks']:
        track = library.get_track_info(filename)
        if track:
            queue_with_meta['tracks'].append({
                k: v for k, v in track.items() if not k.startswith('_')
            })
    
    return jsonify(queue_with_meta)


@api.route('/queue/set', methods=['POST'])
def set_queue():
    """Set the play queue."""
    data = request.get_json() or {}
    tracks = data.get('tracks', [])
    start_index = data.get('index', 0)
    
    playlist.set_queue(tracks, start_index)
    
    # Start playing first track
    if tracks:
        player.play(tracks[start_index])
    
    return jsonify({'message': 'Queue set', 'count': len(tracks)})


@api.route('/queue/add', methods=['POST'])
def add_to_queue():
    """Add a track to the queue."""
    data = request.get_json() or {}
    filename = data.get('filename')
    
    if not filename:
        return jsonify({'error': 'filename is required'}), 400
    
    playlist.add_to_queue(filename)
    return jsonify({'message': 'Added to queue', 'filename': filename})


@api.route('/queue/remove', methods=['POST'])
def remove_from_queue():
    """Remove a track from the queue."""
    data = request.get_json() or {}
    index = data.get('index')
    
    if index is None:
        return jsonify({'error': 'index is required'}), 400
    
    if playlist.remove_from_queue(int(index)):
        return jsonify({'message': 'Removed from queue'})
    else:
        return jsonify({'error': 'Invalid index'}), 400


@api.route('/queue/clear', methods=['POST'])
def clear_queue():
    """Clear the queue."""
    playlist.clear_queue()
    player.stop()
    return jsonify({'message': 'Queue cleared'})


@api.route('/queue/shuffle', methods=['POST'])
def toggle_shuffle():
    """Toggle shuffle mode."""
    is_shuffle = playlist.toggle_shuffle()
    return jsonify({'shuffle': is_shuffle})


@api.route('/queue/repeat', methods=['POST'])
def set_repeat():
    """Set or cycle repeat mode."""
    data = request.get_json() or {}
    mode = data.get('mode')
    
    if mode:
        if playlist.set_repeat_mode(mode):
            return jsonify({'repeat_mode': mode})
        else:
            return jsonify({'error': 'Invalid mode'}), 400
    else:
        # Cycle mode
        new_mode = playlist.cycle_repeat_mode()
        return jsonify({'repeat_mode': new_mode})


@api.route('/queue/play-all', methods=['POST'])
def play_all():
    """Play all tracks in library."""
    data = request.get_json() or {}
    shuffle = data.get('shuffle', False)
    
    tracks = playlist.play_all(shuffle)
    
    if tracks:
        player.play(tracks[0])
        return jsonify({'message': 'Playing all', 'count': len(tracks)})
    else:
        return jsonify({'error': 'Library is empty'}), 400


# ============== Saved Playlists ==============

@api.route('/playlists')
def list_playlists():
    """Get list of saved playlists."""
    playlists = playlist.get_saved_playlists()
    return jsonify(playlists)


@api.route('/playlists', methods=['POST'])
def create_playlist():
    """Create/save a playlist."""
    data = request.get_json() or {}
    name = data.get('name')
    tracks = data.get('tracks', [])
    
    if not name:
        return jsonify({'error': 'name is required'}), 400
    
    playlist.save_playlist(name, tracks)
    return jsonify({'message': 'Playlist saved', 'name': name})


@api.route('/playlists/<name>')
def get_playlist(name):
    """Get a saved playlist."""
    pl = playlist.load_playlist(name)
    if pl:
        return jsonify(pl)
    else:
        return jsonify({'error': 'Playlist not found'}), 404


@api.route('/playlists/<name>', methods=['DELETE'])
def delete_playlist(name):
    """Delete a saved playlist."""
    if playlist.delete_playlist(name):
        return jsonify({'message': 'Playlist deleted'})
    else:
        return jsonify({'error': 'Playlist not found'}), 404


@api.route('/playlists/<name>/load', methods=['POST'])
def load_playlist_to_queue(name):
    """Load a saved playlist to the queue and start playing."""
    pl = playlist.load_playlist(name)
    if not pl:
        return jsonify({'error': 'Playlist not found'}), 404
    
    tracks = pl.get('tracks', [])
    if not tracks:
        return jsonify({'error': 'Playlist is empty'}), 400
    
    playlist.set_queue(tracks, 0)
    player.play(tracks[0])
    
    return jsonify({'message': 'Playlist loaded', 'count': len(tracks)})
