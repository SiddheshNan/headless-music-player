<script>
  import { 
    library, 
    playerState,
    play,
    addToQueue,
    setQueue,
    playAll,
    reloadLibrary,
    isLoading,
    formatTime,
    getCoverUrl
  } from '../stores/player.js';

  let searchQuery = '';
  
  $: currentFile = $playerState.playback.current_file;
  $: tracks = $library;
  
  // Filter tracks by search
  $: filteredTracks = searchQuery 
    ? tracks.filter(t => 
        t.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        t.artist.toLowerCase().includes(searchQuery.toLowerCase())
      )
    : tracks;

  function handlePlay(filename) {
    // Set queue to all tracks starting from this one
    const filenames = tracks.map(t => t.filename);
    const index = filenames.indexOf(filename);
    setQueue(filenames, index);
  }

  function handleAddToQueue(e, filename) {
    e.stopPropagation();
    addToQueue(filename);
  }

  function handlePlayAll(shuffle = false) {
    playAll(shuffle);
  }

  // Default cover placeholder
  const defaultCover = 'data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0iIzY0NzQ4YiI+PHBhdGggZD0iTTEyIDN2MTAuNTVjLS41OS0uMzQtMS4yNy0uNTUtMi0uNTUtMi4yMSAwLTQgMS43OS00IDRzMS43OSA0IDQgNCA0LTEuNzkgNC00VjdoNFYzaC02eiIvPjwvc3ZnPg==';
</script>

<div class="w-full">
  <!-- Header -->
  <div class="flex items-center justify-between mb-4">
    <h3 class="text-lg font-semibold">Library</h3>
    <div class="flex items-center gap-2">
      <span class="text-sm text-player-text-muted">{tracks.length} tracks</span>
      <button 
        class="btn-control p-2"
        on:click={reloadLibrary}
        disabled={$isLoading}
        title="Refresh library"
      >
        <span class={$isLoading ? 'animate-spin inline-block' : ''}>🔄</span>
      </button>
    </div>
  </div>

  <!-- Search -->
  <div class="relative mb-4">
    <input
      type="text"
      placeholder="Search tracks..."
      bind:value={searchQuery}
      class="w-full bg-player-card border border-player-border rounded-xl px-4 py-3 pl-10
             text-player-text placeholder-player-text-muted
             focus:outline-none focus:border-player-accent transition-colors"
    />
    <span class="absolute left-3 top-1/2 -translate-y-1/2 text-player-text-muted">🔍</span>
  </div>

  <!-- Play All Buttons -->
  <div class="flex gap-2 mb-4">
    <button 
      class="flex-1 bg-player-accent hover:bg-player-accent-hover text-white 
             rounded-xl py-2.5 px-4 font-medium transition-colors text-sm
             active:scale-[0.98]"
      on:click={() => handlePlayAll(false)}
      disabled={tracks.length === 0}
    >
      ▶️ Play All
    </button>
    <button 
      class="flex-1 bg-player-card hover:bg-player-hover border border-player-border
             rounded-xl py-2.5 px-4 font-medium transition-colors text-sm
             active:scale-[0.98]"
      on:click={() => handlePlayAll(true)}
      disabled={tracks.length === 0}
    >
      🔀 Shuffle All
    </button>
  </div>

  <!-- Track List -->
  <div class="space-y-1 max-h-[50vh] overflow-y-auto">
    {#if filteredTracks.length === 0}
      <p class="text-player-text-muted text-center py-8">
        {searchQuery ? 'No tracks found' : 'No music in library'}
      </p>
    {:else}
      {#each filteredTracks as track}
        <!-- svelte-ignore a11y-click-events-have-key-events -->
        <div 
          class="track-item group {currentFile === track.filename ? 'track-item-active' : ''}"
          on:click={() => handlePlay(track.filename)}
          role="button"
          tabindex="0"
        >
          <!-- Thumbnail -->
          <div class="w-12 h-12 rounded-lg overflow-hidden flex-shrink-0 bg-player-hover">
            {#if track.has_cover}
              <img 
                src={getCoverUrl(track.filename)} 
                alt=""
                class="w-full h-full object-cover"
                on:error={(e) => e?.target?.src = defaultCover}
              />
            {:else}
              <div class="w-full h-full flex items-center justify-center bg-player-hover">
                <span class="text-xl">🎵</span>
              </div>
            {/if}
          </div>
          
          <!-- Track info -->
          <div class="flex-1 min-w-0">
            <p class="font-medium truncate {currentFile === track.filename ? 'text-player-accent' : ''}">
              {track.title}
            </p>
            <p class="text-sm text-player-text-muted truncate">
              {track.artist}
            </p>
          </div>
          
          <!-- Duration -->
          <span class="text-player-text-muted text-sm hidden sm:block">
            {formatTime(track.duration_ms)}
          </span>
          
          <!-- Actions -->
          <div class="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
            <button 
              class="p-2 hover:bg-player-accent/20 rounded-lg transition-colors"
              on:click={(e) => handleAddToQueue(e, track.filename)}
              title="Add to queue"
            >
              ➕
            </button>
          </div>
        </div>
      {/each}
    {/if}
  </div>
</div>
