<script>
  import { 
    playerState, 
    play,
    formatTime,
    getCoverUrl
  } from '../stores/player.js';

  export let maxItems = 5;

  $: queue = $playerState.queue;
  $: currentIndex = queue.index;
  $: tracks = queue.tracks || [];
  
  // Get upcoming tracks (after current)
  $: upcomingTracks = tracks.slice(currentIndex + 1, currentIndex + 1 + maxItems);

  function handlePlayTrack(index) {
    const actualIndex = currentIndex + 1 + index;
    const filename = tracks[actualIndex];
    if (filename) {
      play(filename);
    }
  }

  // Default cover placeholder
  const defaultCover = 'data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0iIzY0NzQ4YiI+PHBhdGggZD0iTTEyIDN2MTAuNTVjLS41OS0uMzQtMS4yNy0uNTUtMi0uNTUtMi4yMSAwLTQgMS43OS00IDRzMS43OSA0IDQgNCA0LTEuNzkgNC00VjdoNFYzaC02eiIvPjwvc3ZnPg==';
</script>

<div class="w-full">
  <h3 class="text-lg font-semibold mb-3 text-player-text-muted">Up Next</h3>
  
  {#if upcomingTracks.length === 0}
    <p class="text-player-text-muted text-sm py-4 text-center">
      {tracks.length === 0 ? 'Queue is empty' : 'No more tracks in queue'}
    </p>
  {:else}
    <div class="space-y-1">
      {#each upcomingTracks as filename, i}
        <!-- svelte-ignore a11y-click-events-have-key-events -->
        <div 
          class="track-item group"
          on:click={() => handlePlayTrack(i)}
          role="button"
          tabindex="0"
        >
          <!-- Thumbnail -->
          <div class="w-10 h-10 rounded-lg overflow-hidden flex-shrink-0 bg-player-hover">
            <img 
              src={getCoverUrl(filename)} 
              alt=""
              class="w-full h-full object-cover"
              on:error={(e) => e.target.src = defaultCover}
            />
          </div>
          
          <!-- Track info -->
          <div class="flex-1 min-w-0">
            <p class="font-medium truncate text-sm">
              {filename.replace(/\.[^/.]+$/, '')}
            </p>
          </div>
          
          <!-- Queue position -->
          <span class="text-player-text-muted text-sm opacity-0 group-hover:opacity-100 transition-opacity">
            #{i + 1}
          </span>
        </div>
      {/each}
    </div>
    
    {#if tracks.length > currentIndex + 1 + maxItems}
      <p class="text-player-text-muted text-xs text-center mt-2">
        +{tracks.length - currentIndex - 1 - maxItems} more
      </p>
    {/if}
  {/if}
</div>
