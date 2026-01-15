<script>
  import { onMount } from 'svelte';
  import { initPlayer, playerState, fetchPlaylists } from './stores/player.js';
  import NowPlaying from './components/NowPlaying.svelte';
  import Queue from './components/Queue.svelte';
  import Library from './components/Library.svelte';
  import PlaylistModal from './components/PlaylistModal.svelte';

  // Navigation tabs
  const tabs = [
    { id: 'now', label: 'Now Playing', icon: '🎵' },
    { id: 'library', label: 'Library', icon: '📚' },
    { id: 'queue', label: 'Queue', icon: '📋' }
  ];

  let activeTab = 'now';
  let showPlaylistModal = false;
  let isInitialized = false;

  onMount(async () => {
    await initPlayer();
    isInitialized = true;
  });

  function openPlaylists() {
    fetchPlaylists();
    showPlaylistModal = true;
  }
</script>

<div class="min-h-screen flex flex-col">
  <!-- Header -->
  <header class="flex items-center justify-between px-4 py-3 border-b border-player-border bg-player-card/50 backdrop-blur-lg sticky top-0 z-40">
    <div class="flex items-center gap-2">
      <span class="text-2xl">🎵</span>
      <h1 class="text-lg font-bold hidden sm:block">Music Player</h1>
    </div>
    
    <button 
      class="btn-control flex items-center gap-2 px-3 py-2 bg-player-hover rounded-lg"
      on:click={openPlaylists}
    >
      <span>📋</span>
      <span class="hidden sm:inline text-sm">Playlists</span>
    </button>
  </header>

  <!-- Main Content -->
  <main class="flex-1 overflow-y-auto pb-20">
    {#if !isInitialized}
      <!-- Loading state -->
      <div class="flex items-center justify-center h-64">
        <div class="text-center">
          <div class="text-4xl mb-4 animate-pulse">🎵</div>
          <p class="text-player-text-muted">Loading...</p>
        </div>
      </div>
    {:else}
      <!-- Desktop: Side by side layout -->
      <div class="hidden lg:grid lg:grid-cols-2 gap-6 p-6 max-w-6xl mx-auto">
        <div class="space-y-6">
          <div class="card p-6">
            <NowPlaying />
          </div>
          <div class="card p-6">
            <Queue maxItems={5} />
          </div>
        </div>
        <div class="card p-6">
          <Library />
        </div>
      </div>

      <!-- Mobile/Tablet: Tabbed layout -->
      <div class="lg:hidden p-4">
        {#if activeTab === 'now'}
          <NowPlaying />
          <div class="mt-6 card p-4">
            <Queue maxItems={3} />
          </div>
        {:else if activeTab === 'library'}
          <Library />
        {:else if activeTab === 'queue'}
          <div class="card p-4">
            <h3 class="text-lg font-semibold mb-4">Full Queue</h3>
            <Queue maxItems={20} />
          </div>
        {/if}
      </div>
    {/if}
  </main>

  <!-- Mobile Bottom Navigation -->
  <nav class="lg:hidden fixed bottom-0 left-0 right-0 bg-player-card/95 backdrop-blur-lg 
              border-t border-player-border safe-area-bottom z-40">
    <div class="flex justify-around">
      {#each tabs as tab}
        <button 
          class="flex-1 flex flex-col items-center py-3 px-4 transition-colors
                 {activeTab === tab.id ? 'text-player-accent' : 'text-player-text-muted'}"
          on:click={() => activeTab = tab.id}
        >
          <span class="text-xl mb-1">{tab.icon}</span>
          <span class="text-xs font-medium">{tab.label}</span>
        </button>
      {/each}
    </div>
  </nav>
</div>

<!-- Playlist Modal -->
<PlaylistModal bind:isOpen={showPlaylistModal} />

<style>
  /* Safe area for iOS */
  .safe-area-bottom {
    padding-bottom: env(safe-area-inset-bottom, 0);
  }
</style>
