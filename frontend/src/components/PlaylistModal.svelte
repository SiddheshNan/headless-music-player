<script>
  import { createEventDispatcher } from 'svelte';
  import { 
    playlists,
    playerState,
    savePlaylist,
    loadPlaylist,
    deletePlaylist,
    fetchPlaylists
  } from '../stores/player.js';

  const dispatch = createEventDispatcher();

  export let isOpen = false;

  let newPlaylistName = '';
  let showCreateForm = false;

  $: queueTracks = $playerState.queue.tracks || [];

  function close() {
    isOpen = false;
    showCreateForm = false;
    newPlaylistName = '';
    dispatch('close');
  }

  async function handleCreate() {
    if (!newPlaylistName.trim()) return;
    await savePlaylist(newPlaylistName.trim(), queueTracks);
    newPlaylistName = '';
    showCreateForm = false;
  }

  async function handleLoad(name) {
    await loadPlaylist(name);
    close();
  }

  async function handleDelete(e, name) {
    e.stopPropagation();
    if (confirm(`Delete playlist "${name}"?`)) {
      await deletePlaylist(name);
    }
  }

  function handleBackdropClick(e) {
    if (e.target === e.currentTarget) {
      close();
    }
  }

  function handleKeydown(e) {
    if (e.key === 'Escape') {
      close();
    }
  }
</script>

<svelte:window on:keydown={handleKeydown} />

{#if isOpen}
  <!-- Backdrop -->
  <!-- svelte-ignore a11y-click-events-have-key-events -->
  <div 
    class="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-end sm:items-center justify-center"
    on:click={handleBackdropClick}
    role="dialog"
    aria-modal="true"
  >
    <!-- Modal -->
    <div class="bg-player-card w-full max-w-md rounded-t-2xl sm:rounded-2xl 
                max-h-[80vh] overflow-hidden flex flex-col animate-slide-up">
      <!-- Header -->
      <div class="flex items-center justify-between p-4 border-b border-player-border">
        <h2 class="text-xl font-bold">Playlists</h2>
        <button 
          class="p-2 hover:bg-player-hover rounded-lg transition-colors"
          on:click={close}
        >
          ✕
        </button>
      </div>

      <!-- Content -->
      <div class="flex-1 overflow-y-auto p-4">
        <!-- Create new playlist -->
        {#if showCreateForm}
          <div class="mb-4 p-4 bg-player-hover rounded-xl">
            <input
              type="text"
              placeholder="Playlist name"
              bind:value={newPlaylistName}
              class="w-full bg-player-card border border-player-border rounded-lg px-3 py-2
                     text-player-text placeholder-player-text-muted mb-3
                     focus:outline-none focus:border-player-accent"
              autofocus
            />
            <div class="flex gap-2">
              <button 
                class="flex-1 bg-player-accent hover:bg-player-accent-hover 
                       text-white rounded-lg py-2 font-medium transition-colors"
                on:click={handleCreate}
                disabled={!newPlaylistName.trim()}
              >
                Save ({queueTracks.length} tracks)
              </button>
              <button 
                class="px-4 hover:bg-player-card rounded-lg transition-colors"
                on:click={() => showCreateForm = false}
              >
                Cancel
              </button>
            </div>
          </div>
        {:else}
          <button 
            class="w-full mb-4 border-2 border-dashed border-player-border 
                   hover:border-player-accent rounded-xl py-4 text-player-text-muted
                   hover:text-player-accent transition-colors"
            on:click={() => showCreateForm = true}
            disabled={queueTracks.length === 0}
          >
            ➕ Save current queue as playlist
          </button>
        {/if}

        <!-- Playlist list -->
        {#if $playlists.length === 0}
          <p class="text-player-text-muted text-center py-8">
            No saved playlists yet
          </p>
        {:else}
          <div class="space-y-2">
            {#each $playlists as name}
              <!-- svelte-ignore a11y-click-events-have-key-events -->
              <div 
                class="track-item group"
                on:click={() => handleLoad(name)}
                role="button"
                tabindex="0"
              >
                <span class="text-2xl">📋</span>
                <span class="flex-1 font-medium">{name}</span>
                <button 
                  class="p-2 opacity-0 group-hover:opacity-100 hover:bg-red-500/20 
                         rounded-lg transition-all text-red-400"
                  on:click={(e) => handleDelete(e, name)}
                  title="Delete playlist"
                >
                  🗑️
                </button>
              </div>
            {/each}
          </div>
        {/if}
      </div>
    </div>
  </div>
{/if}

<style>
  @keyframes slide-up {
    from {
      transform: translateY(100%);
      opacity: 0;
    }
    to {
      transform: translateY(0);
      opacity: 1;
    }
  }
  
  .animate-slide-up {
    animation: slide-up 0.3s ease-out;
  }
  
  @media (min-width: 640px) {
    @keyframes slide-up {
      from {
        transform: scale(0.95);
        opacity: 0;
      }
      to {
        transform: scale(1);
        opacity: 1;
      }
    }
  }
</style>
