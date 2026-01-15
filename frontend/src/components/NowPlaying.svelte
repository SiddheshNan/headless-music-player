<script>
  import { 
    playerState, 
    currentTrack, 
    isPlaying,
    togglePlayPause, 
    nextTrack, 
    prevTrack,
    seek,
    setVolume,
    toggleShuffle,
    cycleRepeat,
    formatTime,
    getCoverUrl
  } from '../stores/player.js';

  // Reactive state
  $: playback = $playerState.playback;
  $: queue = $playerState.queue;
  $: track = $currentTrack;
  $: position = playback.position_ms;
  $: duration = playback.duration_ms;
  $: progress = duration ? (position / duration) * 100 : 0;

  // Local state for seeking
  let isSeeking = false;
  let seekPosition = 0;

  // Handle seek
  function handleSeekStart() {
    isSeeking = true;
    seekPosition = position;
  }

  function handleSeekInput(e) {
    seekPosition = parseFloat(e.target.value);
  }

  function handleSeekEnd() {
    seek(seekPosition);
    isSeeking = false;
  }

  // Handle volume
  function handleVolumeChange(e) {
    setVolume(parseFloat(e.target.value));
  }

  // Get repeat icon
  function getRepeatIcon(mode) {
    switch (mode) {
      case 'one': return '🔂';
      case 'all': return '🔁';
      default: return '🔁';
    }
  }

  // Default cover image (base64 music icon)
  const defaultCover = 'data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0iIzRhNWU4MCIgd2lkdGg9IjI0MCIgaGVpZ2h0PSIyNDAiPjxyZWN0IHdpZHRoPSIyNCIgaGVpZ2h0PSIyNCIgZmlsbD0iIzFmMjkzNyIvPjxwYXRoIGQ9Ik0xMiAzdjEwLjU1Yy0uNTktLjM0LTEuMjctLjU1LTItLjU1LTIuMjEgMC00IDEuNzktNCA0czEuNzkgNCA0IDQgNC0xLjc5IDQtNFY3aDRWM2gtNnoiLz48L3N2Zz4=';
</script>

<div class="flex flex-col items-center w-full max-w-md mx-auto px-4 py-6">
  <!-- Cover Art -->
  <div class="relative w-64 h-64 sm:w-72 sm:h-72 mb-6">
    <div class="w-full h-full rounded-2xl overflow-hidden shadow-2xl shadow-player-accent/20">
      {#if track && track.has_cover}
        <img 
          src={getCoverUrl(track.filename)} 
          alt={track.title}
          class="w-full h-full object-cover"
          on:error={(e) => e.target.src = defaultCover}
        />
      {:else}
        <div class="w-full h-full bg-gradient-to-br from-player-card to-player-hover flex items-center justify-center">
          <svg class="w-24 h-24 text-player-text-muted" fill="currentColor" viewBox="0 0 24 24">
            <path d="M12 3v10.55c-.59-.34-1.27-.55-2-.55-2.21 0-4 1.79-4 4s1.79 4 4 4 4-1.79 4-4V7h4V3h-6z"/>
          </svg>
        </div>
      {/if}
    </div>
    
    <!-- Playing indicator -->
    {#if $isPlaying}
      <div class="absolute -bottom-2 left-1/2 -translate-x-1/2 flex gap-1">
        <span class="w-1 h-4 bg-player-accent rounded-full animate-pulse"></span>
        <span class="w-1 h-3 bg-player-accent rounded-full animate-pulse delay-75"></span>
        <span class="w-1 h-5 bg-player-accent rounded-full animate-pulse delay-150"></span>
        <span class="w-1 h-3 bg-player-accent rounded-full animate-pulse delay-75"></span>
        <span class="w-1 h-4 bg-player-accent rounded-full animate-pulse"></span>
      </div>
    {/if}
  </div>

  <!-- Track Info -->
  <div class="text-center mb-6 w-full">
    <h2 class="text-xl sm:text-2xl font-bold truncate mb-1">
      {track?.title || 'No track selected'}
    </h2>
    <p class="text-player-text-muted truncate">
      {track?.artist || 'Select a song to play'}
    </p>
  </div>

  <!-- Seek Bar -->
  <div class="w-full mb-6">
    <input
      type="range"
      min="0"
      max={duration || 100}
      value={isSeeking ? seekPosition : position}
      on:mousedown={handleSeekStart}
      on:touchstart={handleSeekStart}
      on:input={handleSeekInput}
      on:mouseup={handleSeekEnd}
      on:touchend={handleSeekEnd}
      class="w-full seek-slider"
      style="--progress: {progress}%"
      disabled={!track}
    />
    <div class="flex justify-between text-sm text-player-text-muted mt-1">
      <span>{formatTime(isSeeking ? seekPosition : position)}</span>
      <span>{formatTime(duration)}</span>
    </div>
  </div>

  <!-- Playback Controls -->
  <div class="flex items-center justify-center gap-2 mb-6">
    <!-- Shuffle -->
    <button 
      class="btn-control text-xl {queue.shuffle ? 'btn-control-active' : 'text-player-text-muted'}"
      on:click={toggleShuffle}
      title="Shuffle"
    >
      🔀
    </button>

    <!-- Previous -->
    <button 
      class="btn-control text-2xl"
      on:click={prevTrack}
      disabled={!track}
    >
      ⏮️
    </button>

    <!-- Play/Pause -->
    <button 
      class="w-16 h-16 rounded-full bg-player-accent hover:bg-player-accent-hover 
             flex items-center justify-center text-3xl transition-all duration-200
             active:scale-95 disabled:opacity-50"
      on:click={togglePlayPause}
      disabled={!track && !queue.tracks?.length}
    >
      {$isPlaying ? '⏸️' : '▶️'}
    </button>

    <!-- Next -->
    <button 
      class="btn-control text-2xl"
      on:click={nextTrack}
      disabled={!track}
    >
      ⏭️
    </button>

    <!-- Repeat -->
    <button 
      class="btn-control text-xl {queue.repeat_mode !== 'off' ? 'btn-control-active' : 'text-player-text-muted'}"
      on:click={cycleRepeat}
      title="Repeat: {queue.repeat_mode}"
    >
      {getRepeatIcon(queue.repeat_mode)}
      {#if queue.repeat_mode === 'one'}
        <span class="absolute text-xs font-bold">1</span>
      {/if}
    </button>
  </div>

  <!-- Volume -->
  <div class="flex items-center gap-3 w-full max-w-xs">
    <span class="text-player-text-muted">🔈</span>
    <input
      type="range"
      min="0"
      max="1"
      step="0.01"
      value={playback.volume}
      on:input={handleVolumeChange}
      class="flex-1"
    />
    <span class="text-player-text-muted">🔊</span>
  </div>
</div>

<style>
  /* Add delay classes for animation */
  .delay-75 { animation-delay: 75ms; }
  .delay-150 { animation-delay: 150ms; }
</style>
