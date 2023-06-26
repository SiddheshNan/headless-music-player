<script>
  import { onMount } from "svelte";
  import { random_bg_color, BASE_URL, send_state_value } from "./helpers.js";
  import Fa from "svelte-fa/src/fa.svelte";
  import {
    faStepBackward,
    faStepForward,
    faPlayCircle,
    faPauseCircle,
    faMusic,
    faVolumeDown,
    faVolumeUp,
  } from "@fortawesome/free-solid-svg-icons";

  let music_list = [];
  let musicName = "";
  let isPaused = false;

  let volume = 0;

  const getMusicListFromServer = () => {
    fetch(`${BASE_URL}/music_list`)
      .then((response) => response.json())
      .then((data) => {
        music_list = data;
        console.log("Got music_list from server:", data);
      });
  };

  const getStateFromServer = () => {
    fetch(`${BASE_URL}/state`)
      .then((response) => response.json())
      .then((data) => {
        musicName = data.fileName;
        isPaused = data.isPaused;
        volume = data.volume;
        console.log("Got state from server", data);
      });
  };

  const reloadLists = () => {
    fetch(`${BASE_URL}/reload_music_list`)
      .then((response) => response.json())
      .then((data) => {
        getMusicListFromServer();
        getStateFromServer();
      });
  };

  const playPause = () => {
    isPaused = !isPaused;

    isPaused
      ? send_state_value({ pause: true })
      : send_state_value({ resume: true });
  };
  const playSelectedMusic = (name) => {
    random_bg_color();
    musicName = name;
    send_state_value({
      play: name,
    });
    isPaused = false;
  };

  const onVolumeChange = (event) => {
    let vol = event.target.value;
    send_state_value({
      volume: parseFloat(vol),
    });
  };

  const changeTrack = (kind) => {
    const currentIndex = music_list.indexOf(musicName);
    if (kind == "next") {
      if (currentIndex == music_list.length - 1) {
        playSelectedMusic(music_list[0]);
      } else {
        playSelectedMusic(music_list[currentIndex + 1]);
      }
    } else {
      if (currentIndex == 0) {
        playSelectedMusic(music_list[music_list.length - 1]);
      } else {
        playSelectedMusic(music_list[currentIndex - 1]);
      }
    }
  };

  onMount(() => {
    getMusicListFromServer();
    getStateFromServer();
  });
</script>

<div class="player">
  <div class="songs-list">
    <!-- svelte-ignore a11y-click-events-have-key-events -->
    <h2 style="font-size: 2rem;" class="main-heading" on:click={reloadLists}>
      <Fa icon={faMusic} style="font-size: 1.8rem;" /> Music Player
    </h2>

    <ol>
      {#each music_list as music}
        <li>
          <button
            class="song-list-item"
            on:click={() => playSelectedMusic(music)}
            >{music.substring(0, Math.max(0, music.length - 4))}</button
          >
        </li>
      {/each}
    </ol>
  </div>

  <div class="details">
    <!-- <div class="track-art" /> -->
    <div
      class="track-name text-center"
      style="text-align: center;  font-weight: 500;"
    >
      {musicName.substring(0, Math.max(0, musicName.length - 4))}
    </div>
    <!-- <div class="track-artist">Track Artist</div> -->
  </div>

  <!-- Define the section for displaying track buttons -->
  <div class="buttons">
    <!-- svelte-ignore a11y-click-events-have-key-events -->
    <div class="prev-track" on:click={() => changeTrack("prev")}>
      <Fa icon={faStepBackward} class="fa fa-step-backward fa-2x" size="2x" />
    </div>
    <!-- svelte-ignore a11y-click-events-have-key-events -->
    <div class="playpause-track" on:click={playPause}>
      {#if isPaused}
        <Fa icon={faPlayCircle} class="fa fa-play-circle fa-5x" size="5x" />
      {:else}
        <Fa icon={faPauseCircle} class="fa fa-pause-circle fa-5x" size="5x" />
      {/if}
    </div>
    <!-- svelte-ignore a11y-click-events-have-key-events -->
    <div class="next-track" on:click={() => changeTrack("next")}>
      <Fa icon={faStepForward} class="fa fa-step-backward fa-2x" size="2x" />
    </div>
  </div>

  <div class="slider_container">
    <Fa icon={faVolumeDown} class="fa fa-volume-down" size="2.2x" />

    <input
      type="range"
      min="0.00"
      max="1.00"
      step="0.01"
      class="volume_slider"
      on:change={onVolumeChange}
      value={volume}
    />

    <Fa icon={faVolumeUp} class="fa fa-volume-up" size="2.2x" />
  </div>
</div>
