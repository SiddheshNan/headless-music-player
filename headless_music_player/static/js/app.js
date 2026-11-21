// Page behavior for the server-rendered UI. The server renders everything; this script
// sends actions to the JSON API, polls /api/state and swaps in re-rendered partials.
(() => {
  "use strict";

  const POLL_MS = 1000;
  const SLOW_ACTIONS = new Set(["rescan", "play-all", "shuffle-all", "clear"]);
  const $ = (id) => document.getElementById(id);

  const el = {
    title: $("np-title"),
    artist: $("np-artist"),
    cover: $("np-cover"),
    coverFallback: $("np-cover-fallback"),
    seek: $("np-seek"),
    position: $("np-position"),
    duration: $("np-duration"),
    toggle: $("btn-toggle"),
    iconPlay: $("icon-play"),
    iconPause: $("icon-pause"),
    shuffle: $("btn-shuffle"),
    repeat: $("btn-repeat"),
    iconRepeat: $("icon-repeat"),
    iconRepeatOne: $("icon-repeat-one"),
    volume: $("np-volume"),
    volumeLabel: $("np-volume-label"),
    iconVolume: $("icon-volume"),
    iconMuted: $("icon-muted"),
    audioAlert: $("audio-alert"),
    audioError: $("audio-error"),
    queuePanel: $("panel-queue"),
    libraryPanel: $("panel-library"),
    queueCount: $("queue-count"),
    libraryCount: $("library-count"),
    connection: $("connection"),
    toasts: $("toasts"),
  };

  let state = window.INITIAL_STATE;
  let stateReceivedAt = performance.now();
  let queueVersion = Number(el.queuePanel.dataset.version);
  let libraryVersion = Number(el.libraryPanel.dataset.version);
  let seeking = false;
  let volumeDragging = false;
  let volumeTimer = null;
  let lastVolume = state.volume || 0.5;
  let pollTimer = null;
  let polling = false;

  // ---------- helpers ----------

  function mmss(ms) {
    const s = Math.max(0, Math.floor((ms || 0) / 1000));
    const pad = (n) => String(n).padStart(2, "0");
    if (s >= 3600) return `${Math.floor(s / 3600)}:${pad(Math.floor((s % 3600) / 60))}:${pad(s % 60)}`;
    return `${Math.floor(s / 60)}:${pad(s % 60)}`;
  }

  function show(node, visible) {
    node.classList.toggle("hidden", !visible);
  }

  function toast(message, kind = "error") {
    const alert = document.createElement("div");
    alert.className = `alert alert-${kind} alert-soft text-sm shadow-lg`;
    alert.setAttribute("role", "alert");
    alert.textContent = message;
    el.toasts.append(alert);
    setTimeout(() => alert.remove(), 4000);
  }

  async function api(path, body, method = "POST") {
    const options = body === undefined && method === "GET" ? {} : {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body || {}),
    };
    const res = await fetch(path, options);
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || `Request failed (${res.status})`);
    return data;
  }

  async function fetchHtml(path) {
    const res = await fetch(path);
    if (!res.ok) throw new Error(`Request failed (${res.status})`);
    return res.text();
  }

  // ---------- rendering ----------

  function currentPosition() {
    // Between polls, advance the position locally so the bar moves smoothly.
    if (state.status !== "playing" || !state.audio.available) return state.position_ms;
    const elapsed = performance.now() - stateReceivedAt;
    const position = state.position_ms + elapsed;
    return state.duration_ms ? Math.min(position, state.duration_ms) : position;
  }

  function renderProgress() {
    if (seeking) return;
    const position = currentPosition();
    el.seek.value = position;
    el.position.textContent = mmss(position);
  }

  function render(next) {
    const prevTrackId = state.current?.track?.id;
    state = next;
    stateReceivedAt = performance.now();
    const current = next.current;
    const track = current?.track;
    const paused = next.status !== "playing";

    el.title.textContent = track ? track.title : current ? "Missing file" : "Nothing playing";
    el.title.title = track ? track.title : "";
    el.artist.textContent = track ? track.artist || "Unknown artist" : current ? "" : "Pick a track from the library";
    document.title = track ? `${track.title} · Headless Player` : "Headless Player";

    const coverUrl = track?.cover_url;
    if (coverUrl && el.cover.getAttribute("src") !== coverUrl) el.cover.src = coverUrl;
    show(el.cover, Boolean(coverUrl));
    el.coverFallback.classList.toggle("grid", !coverUrl);
    show(el.coverFallback, !coverUrl);

    el.seek.disabled = !current || next.status === "stopped";
    el.seek.max = next.duration_ms || 0;
    el.duration.textContent = mmss(next.duration_ms);
    renderProgress();

    show(el.iconPlay, paused);
    show(el.iconPause, !paused);
    el.toggle.setAttribute("aria-label", paused ? "Play" : "Pause");
    document.body.classList.toggle("is-paused", paused);

    el.shuffle.classList.toggle("text-primary", next.shuffle);
    el.shuffle.classList.toggle("text-base-content/50", !next.shuffle);
    el.shuffle.setAttribute("aria-pressed", String(next.shuffle));

    const repeatOn = next.repeat !== "off";
    el.repeat.classList.toggle("text-primary", repeatOn);
    el.repeat.classList.toggle("text-base-content/50", !repeatOn);
    el.repeat.title = `Repeat: ${next.repeat}`;
    el.repeat.setAttribute("aria-label", `Repeat: ${next.repeat}`);
    show(el.iconRepeat, next.repeat !== "one");
    show(el.iconRepeatOne, next.repeat === "one");

    if (!volumeDragging) renderVolume(next.volume);

    show(el.audioAlert, !next.audio.available);
    el.audioError.textContent = `${next.audio.error || ""} Retrying every few seconds.`;

    if (next.queue_version !== queueVersion) refreshQueue(next.queue_version);
    if (next.library_version !== libraryVersion) refreshLibrary(next.library_version);
    else if (track?.id !== prevTrackId) markLibraryCurrent();
  }

  function renderVolume(volume) {
    const pct = Math.round(volume * 100);
    el.volume.value = pct;
    el.volumeLabel.textContent = `${pct}%`;
    show(el.iconVolume, pct > 0);
    show(el.iconMuted, pct === 0);
  }

  function markLibraryCurrent() {
    const id = state.current?.track?.id;
    el.libraryPanel.querySelectorAll("li[data-track]").forEach((li) => {
      li.classList.toggle("is-current", li.dataset.track === id);
    });
  }

  async function refreshQueue(version) {
    queueVersion = version;
    try {
      el.queuePanel.innerHTML = await fetchHtml("/partials/queue");
      el.queueCount.textContent = state.queue.length;
    } catch (e) {
      queueVersion = null; // try again on the next poll
    }
  }

  async function refreshLibrary(version) {
    libraryVersion = version;
    const query = $("library-search")?.value || "";
    try {
      el.libraryPanel.innerHTML = await fetchHtml("/partials/library");
    } catch (e) {
      libraryVersion = null;
      return;
    }
    const header = el.libraryPanel.querySelector("[data-library-count]");
    el.libraryCount.textContent = header ? header.dataset.libraryCount : "0";
    const search = $("library-search");
    if (search && query) {
      search.value = query;
      filterLibrary(query);
    }
  }

  // ---------- polling ----------

  async function poll() {
    if (polling) return;
    polling = true;
    try {
      render(await api("/api/state", undefined, "GET"));
      show(el.connection, false);
      el.connection.classList.remove("flex");
    } catch (e) {
      show(el.connection, true);
      el.connection.classList.add("flex");
    } finally {
      polling = false;
    }
  }

  function startPolling() {
    stopPolling();
    poll();
    pollTimer = setInterval(poll, POLL_MS);
  }

  function stopPolling() {
    clearInterval(pollTimer);
    pollTimer = null;
  }

  document.addEventListener("visibilitychange", () => {
    if (document.hidden) stopPolling();
    else startPolling();
  });

  setInterval(renderProgress, 250);

  // ---------- actions ----------
  // Most endpoints answer with the new state, which is rendered right away.

  const actions = {
    toggle: () => api("/api/playback/toggle"),
    next: () => api("/api/playback/next"),
    prev: () => api("/api/playback/prev"),
    shuffle: () => api("/api/queue/shuffle"),
    repeat: () => api("/api/queue/repeat"),
    "play-track": (btn) => api("/api/playback/play", { track_id: btn.dataset.track }),
    "play-entry": (btn) => api("/api/playback/play", { entry_id: btn.dataset.entry }),
    "play-next": async (btn) => {
      const res = await api("/api/queue/add", { track_ids: [btn.dataset.track], next: true });
      toast("Playing next", "success");
      return res.state;
    },
    add: async (btn) => {
      const res = await api("/api/queue/add", { track_ids: [btn.dataset.track] });
      toast("Added to the queue", "success");
      return res.state;
    },
    remove: (btn) => api(`/api/queue/${encodeURIComponent(btn.dataset.entry)}`, undefined, "DELETE"),
    clear: () => api("/api/queue/clear"),
    "play-all": () => api("/api/queue/play-all", { shuffle: false }),
    "shuffle-all": () => api("/api/queue/play-all", { shuffle: true }),
    mute: () => setVolume(state.volume > 0 ? 0 : lastVolume),
    rescan: async () => {
      const res = await api("/api/library/rescan");
      toast(`Library rescanned: ${res.total} tracks (${res.added} new, ${res.removed} removed)`, "success");
    },
  };

  async function runAction(name, btn) {
    const action = actions[name];
    if (!action) return;
    // Quick toggles stay clickable so fast repeated clicks all count; slow actions lock.
    const locks = btn && SLOW_ACTIONS.has(name);
    if (locks) btn.disabled = true;
    try {
      const result = await action(btn);
      if (result && result.status) render(result);
      else await poll();
    } catch (e) {
      toast(e.message);
    } finally {
      if (locks) btn.disabled = false;
    }
  }

  document.addEventListener("click", (event) => {
    const btn = event.target.closest("[data-action]");
    if (btn && !btn.disabled) runAction(btn.dataset.action, btn);
  });

  // ---------- seek ----------

  el.seek.addEventListener("input", () => {
    seeking = true;
    el.position.textContent = mmss(Number(el.seek.value));
  });

  el.seek.addEventListener("change", async () => {
    try {
      render(await api("/api/playback/seek", { position_ms: Math.round(Number(el.seek.value)) }));
    } catch (e) {
      toast(e.message);
    } finally {
      seeking = false;
      renderProgress();
    }
  });

  // ---------- volume ----------

  async function setVolume(volume) {
    if (volume > 0) lastVolume = volume;
    renderVolume(volume);
    return api("/api/playback/volume", { volume });
  }

  el.volume.addEventListener("input", () => {
    volumeDragging = true;
    const volume = Number(el.volume.value) / 100;
    renderVolume(volume);
    clearTimeout(volumeTimer);
    volumeTimer = setTimeout(() => setVolume(volume).catch((e) => toast(e.message)), 120);
  });

  el.volume.addEventListener("change", () => {
    // Let the debounced request land before a poll may overwrite the slider.
    setTimeout(() => (volumeDragging = false), 400);
  });

  // ---------- tabs ----------

  const TAB_KEY = "hmp.tab";

  function selectTab(name) {
    document.querySelectorAll("[data-tab]").forEach((tab) => {
      const active = tab.dataset.tab === name;
      tab.classList.toggle("tab-active", active);
      tab.setAttribute("aria-selected", String(active));
    });
    document.querySelectorAll("[data-panel]").forEach((panel) => {
      show(panel, panel.dataset.panel === name);
    });
    try { localStorage.setItem(TAB_KEY, name); } catch (e) { /* private mode */ }
  }

  document.querySelectorAll("[data-tab]").forEach((tab) => {
    tab.addEventListener("click", () => selectTab(tab.dataset.tab));
  });

  let savedTab = null;
  try { savedTab = localStorage.getItem(TAB_KEY); } catch (e) { /* private mode */ }
  selectTab(savedTab === "library" ? "library" : "queue");

  // ---------- library search ----------

  function filterLibrary(query) {
    const words = query.toLowerCase().split(/\s+/).filter(Boolean);
    let shown = 0;
    el.libraryPanel.querySelectorAll("li[data-search]").forEach((li) => {
      const match = words.every((w) => li.dataset.search.includes(w));
      show(li, match);
      if (match) shown += 1;
    });
    const empty = $("library-no-results");
    if (empty) show(empty, shown === 0);
  }

  el.libraryPanel.addEventListener("input", (event) => {
    if (event.target.id === "library-search") filterLibrary(event.target.value);
  });

  // ---------- keyboard ----------

  document.addEventListener("keydown", (event) => {
    if (event.target.closest("input, textarea, button, select")) return;
    if (event.code === "Space") {
      event.preventDefault();
      runAction("toggle");
    }
  });

  render(state);
  startPolling();
})();
