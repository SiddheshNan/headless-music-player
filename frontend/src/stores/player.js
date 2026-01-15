// Player store - centralized state management
import { writable, derived } from 'svelte/store';

// API base URL - empty for same-origin
export const IS_PROD_ENV = !(!process.env.NODE_ENV || process.env.NODE_ENV === "development");
const BASE_URL = IS_PROD_ENV ? '' : 'http://127.0.0.1:8000';

// Create stores
export const playerState = writable({
  playback: {
    is_paused: true,
    current_file: '',
    volume: 0.5,
    position_ms: 0,
    duration_ms: 0,
    current_track: null
  },
  queue: {
    tracks: [],
    index: 0,
    shuffle: false,
    repeat_mode: 'off',
    upcoming: []
  }
});

export const library = writable([]);
export const playlists = writable([]);
export const isLoading = writable(false);
export const error = writable(null);

// Derived stores
export const currentTrack = derived(playerState, $state => $state.playback.current_track);
export const isPlaying = derived(playerState, $state => !$state.playback.is_paused);
export const progress = derived(playerState, $state => {
  const { position_ms, duration_ms } = $state.playback;
  if (!duration_ms) return 0;
  return (position_ms / duration_ms) * 100;
});

// Position polling interval
let positionInterval = null;

// API helpers
async function apiGet(endpoint) {
  const response = await fetch(`${BASE_URL}${endpoint}`);
  if (!response.ok) throw new Error(`API error: ${response.status}`);
  return response.json();
}

async function apiPost(endpoint, data = {}) {
  const response = await fetch(`${BASE_URL}${endpoint}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.error || `API error: ${response.status}`);
  }
  return response.json();
}

async function apiDelete(endpoint) {
  const response = await fetch(`${BASE_URL}${endpoint}`, { method: 'DELETE' });
  if (!response.ok) throw new Error(`API error: ${response.status}`);
  return response.json();
}

// State actions
export async function fetchState() {
  try {
    const state = await apiGet('/api/state');
    playerState.set(state);
    return state;
  } catch (e) {
    error.set(e.message);
    console.error('Failed to fetch state:', e);
  }
}

export async function fetchLibrary() {
  try {
    isLoading.set(true);
    const tracks = await apiGet('/api/library');
    library.set(tracks);
    return tracks;
  } catch (e) {
    error.set(e.message);
    console.error('Failed to fetch library:', e);
  } finally {
    isLoading.set(false);
  }
}

export async function reloadLibrary() {
  try {
    isLoading.set(true);
    const tracks = await apiPost('/api/library/reload');
    library.set(tracks);
    return tracks;
  } catch (e) {
    error.set(e.message);
  } finally {
    isLoading.set(false);
  }
}

export async function fetchPlaylists() {
  try {
    const list = await apiGet('/api/playlists');
    playlists.set(list);
    return list;
  } catch (e) {
    error.set(e.message);
  }
}

// Playback actions
export async function play(filename) {
  try {
    await apiPost('/api/playback/play', { filename });
    await fetchState();
    startPositionPolling();
  } catch (e) {
    error.set(e.message);
  }
}

export async function togglePlayPause() {
  try {
    const result = await apiPost('/api/playback/toggle');
    playerState.update(s => {
      s.playback.is_paused = result.is_paused;
      return s;
    });
    
    if (result.is_paused) {
      stopPositionPolling();
    } else {
      startPositionPolling();
    }
  } catch (e) {
    error.set(e.message);
  }
}

export async function pause() {
  try {
    await apiPost('/api/playback/pause');
    playerState.update(s => { s.playback.is_paused = true; return s; });
    stopPositionPolling();
  } catch (e) {
    error.set(e.message);
  }
}

export async function resume() {
  try {
    await apiPost('/api/playback/resume');
    playerState.update(s => { s.playback.is_paused = false; return s; });
    startPositionPolling();
  } catch (e) {
    error.set(e.message);
  }
}

export async function stop() {
  try {
    await apiPost('/api/playback/stop');
    await fetchState();
    stopPositionPolling();
  } catch (e) {
    error.set(e.message);
  }
}

export async function seek(position_ms) {
  try {
    await apiPost('/api/playback/seek', { position_ms: Math.floor(position_ms) });
    playerState.update(s => { s.playback.position_ms = position_ms; return s; });
  } catch (e) {
    error.set(e.message);
  }
}

export async function setVolume(volume) {
  try {
    await apiPost('/api/playback/volume', { volume });
    playerState.update(s => { s.playback.volume = volume; return s; });
  } catch (e) {
    error.set(e.message);
  }
}

export async function nextTrack() {
  try {
    await apiPost('/api/playback/next');
    await fetchState();
    startPositionPolling();
  } catch (e) {
    error.set(e.message);
  }
}

export async function prevTrack() {
  try {
    await apiPost('/api/playback/prev');
    await fetchState();
    startPositionPolling();
  } catch (e) {
    error.set(e.message);
  }
}

// Queue actions
export async function setQueue(tracks, index = 0) {
  try {
    await apiPost('/api/queue/set', { tracks, index });
    await fetchState();
    startPositionPolling();
  } catch (e) {
    error.set(e.message);
  }
}

export async function addToQueue(filename) {
  try {
    await apiPost('/api/queue/add', { filename });
    await fetchState();
  } catch (e) {
    error.set(e.message);
  }
}

export async function clearQueue() {
  try {
    await apiPost('/api/queue/clear');
    await fetchState();
    stopPositionPolling();
  } catch (e) {
    error.set(e.message);
  }
}

export async function toggleShuffle() {
  try {
    const result = await apiPost('/api/queue/shuffle');
    playerState.update(s => { s.queue.shuffle = result.shuffle; return s; });
  } catch (e) {
    error.set(e.message);
  }
}

export async function cycleRepeat() {
  try {
    const result = await apiPost('/api/queue/repeat');
    playerState.update(s => { s.queue.repeat_mode = result.repeat_mode; return s; });
  } catch (e) {
    error.set(e.message);
  }
}

export async function playAll(shuffle = false) {
  try {
    await apiPost('/api/queue/play-all', { shuffle });
    await fetchState();
    startPositionPolling();
  } catch (e) {
    error.set(e.message);
  }
}

// Playlist actions
export async function savePlaylist(name, tracks) {
  try {
    await apiPost('/api/playlists', { name, tracks });
    await fetchPlaylists();
  } catch (e) {
    error.set(e.message);
  }
}

export async function loadPlaylist(name) {
  try {
    await apiPost(`/api/playlists/${encodeURIComponent(name)}/load`);
    await fetchState();
    startPositionPolling();
  } catch (e) {
    error.set(e.message);
  }
}

export async function deletePlaylist(name) {
  try {
    await apiDelete(`/api/playlists/${encodeURIComponent(name)}`);
    await fetchPlaylists();
  } catch (e) {
    error.set(e.message);
  }
}

// Position polling for seek bar updates
async function updatePosition() {
  try {
    const data = await apiGet('/api/playback/position');
    playerState.update(s => {
      s.playback.position_ms = data.position_ms;
      s.playback.is_paused = data.is_paused;
      
      // Check if track ended
      if (!data.is_playing && !data.is_paused && s.playback.current_file) {
        // Track might have ended, fetch full state
        fetchState();
      }
      
      return s;
    });
  } catch (e) {
    console.error('Position update failed:', e);
  }
}

export function startPositionPolling() {
  if (positionInterval) return;
  positionInterval = setInterval(updatePosition, 500);
}

export function stopPositionPolling() {
  if (positionInterval) {
    clearInterval(positionInterval);
    positionInterval = null;
  }
}

// Helper functions
export function formatTime(ms) {
  if (!ms || ms < 0) return '0:00';
  const totalSeconds = Math.floor(ms / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${minutes}:${seconds.toString().padStart(2, '0')}`;
}

export function getCoverUrl(filename) {
  if (!filename) return null;
  return `${BASE_URL}/api/library/cover/${encodeURIComponent(filename)}`;
}

// Initialize
export async function initPlayer() {
  await Promise.all([
    fetchState(),
    fetchLibrary(),
    fetchPlaylists()
  ]);
  
  // Start polling if playing
  let state;
  playerState.subscribe(s => state = s)();
  if (state && !state.playback.is_paused) {
    startPositionPolling();
  }
}
