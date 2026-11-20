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
    queuePanel: $("panel-queue"),
    libraryPanel: $("panel-library"),
    queueCount: $("queue-count"),
    libraryCount: $("library-count"),
    connection: $("connection"),
    toasts: $("toasts"),
  };

  let state = window.INITIAL_STATE;
  let queueVersion = el.queuePanel.dataset.version;
  let seeking = false;
  let volumeDragging = false;
  let volumeTimer = null;
  let lastVolume = state.playback.volume || 0.5;
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

  async function api(path, body) {
    const options = body === undefined ? {} : {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
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

  function coverUrl(filename) {
    return `/api/library/cover/${encodeURIComponent(filename)}`;
  }

  // ---------- rendering ----------

  function render(next) {
    const prev = state;
    state = next;
    const pb = next.playback;
    const q = next.queue;
    const track = pb.current_track;

    el.title.textContent = track ? track.title : "Nothing playing";
    el.title.title = track ? track.title : "";
    el.artist.textContent = track ? track.artist : "Pick a track from the library";
    document.title = track ? `${track.title} · Headless Player` : "Headless Player";

    const hasCover = Boolean(track && track.has_cover);
    if (hasCover) {
      const src = coverUrl(track.filename);
      if (el.cover.getAttribute("src") !== src) el.cover.src = src;
    }
    show(el.cover, hasCover);
    el.coverFallback.classList.toggle("grid", !hasCover);
    show(el.coverFallback, !hasCover);

    el.seek.disabled = !track;
    el.seek.max = pb.duration_ms || 0;
    if (!seeking) {
      el.seek.value = pb.position_ms;
      el.position.textContent = mmss(pb.position_ms);
    }
    el.duration.textContent = mmss(pb.duration_ms);

    show(el.iconPlay, pb.is_paused);
    show(el.iconPause, !pb.is_paused);
    el.toggle.setAttribute("aria-label", pb.is_paused ? "Play" : "Pause");
    document.body.classList.toggle("is-paused", pb.is_paused);

    el.shuffle.classList.toggle("text-primary", q.shuffle);
    el.shuffle.classList.toggle("text-base-content/50", !q.shuffle);
    el.shuffle.setAttribute("aria-pressed", String(q.shuffle));

    const repeatOn = q.repeat_mode !== "off";
    el.repeat.classList.toggle("text-primary", repeatOn);
    el.repeat.classList.toggle("text-base-content/50", !repeatOn);
    el.repeat.title = el.repeat.ariaLabel = `Repeat: ${q.repeat_mode}`;
    show(el.iconRepeat, q.repeat_mode !== "one");
    show(el.iconRepeatOne, q.repeat_mode === "one");

    if (!volumeDragging) renderVolume(pb.volume);

    if (q.version !== queueVersion) refreshQueue();
    if (!prev || prev.playback.current_file !== pb.current_file) markLibraryCurrent();
  }

  function renderVolume(volume) {
    const pct = Math.round(volume * 100);
    el.volume.value = pct;
    el.volumeLabel.textContent = `${pct}%`;
    show(el.iconVolume, pct > 0);
    show(el.iconMuted, pct === 0);
  }

  function markLibraryCurrent() {
    const current = state.playback.current_file;
    el.libraryPanel.querySelectorAll("li[data-filename]").forEach((li) => {
      li.classList.toggle("is-current", li.dataset.filename === current);
    });
  }

  async function refreshQueue() {
    const version = state.queue.version;
    try {
      el.queuePanel.innerHTML = await fetchHtml("/partials/queue");
      queueVersion = version;
      el.queueCount.textContent = state.queue.tracks.length;
    } catch (e) {
      console.error(e);
    }
  }

  async function refreshLibrary() {
    const query = $("library-search")?.value || "";
    el.libraryPanel.innerHTML = await fetchHtml("/partials/library");
    const list = $("library-list");
    el.libraryCount.textContent = list ? list.dataset.libraryCount : "0";
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
      render(await api("/api/state"));
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

  // ---------- actions ----------

  const actions = {
    toggle: () => api("/api/playback/toggle", {}),
    next: () => api("/api/playback/next", {}),
    prev: () => api("/api/playback/prev", {}),
    shuffle: () => api("/api/queue/shuffle", {}),
    repeat: () => api("/api/queue/repeat", {}),
    play: (btn) => api("/api/playback/play", { filename: btn.dataset.filename }),
    add: async (btn) => {
      const res = await api("/api/queue/add", { filename: btn.dataset.filename });
      toast(res.added ? "Added to queue" : "Already in the queue", res.added ? "success" : "info");
    },
    remove: (btn) => api("/api/queue/remove", { index: Number(btn.dataset.index) }),
    clear: () => api("/api/queue/clear", {}),
    "play-all": () => api("/api/queue/play-all", { shuffle: false }),
    "shuffle-all": () => api("/api/queue/play-all", { shuffle: true }),
    mute: () => setVolume(state.playback.volume > 0 ? 0 : lastVolume),
    rescan: async () => {
      await api("/api/library/reload", {});
      await refreshLibrary();
      toast("Library rescanned", "success");
    },
  };

  document.addEventListener("click", async (event) => {
    const btn = event.target.closest("[data-action]");
    if (!btn || btn.disabled) return;
    const action = actions[btn.dataset.action];
    if (!action) return;

    // Quick toggles stay clickable so fast repeated clicks all count; slow actions lock.
    const locks = SLOW_ACTIONS.has(btn.dataset.action);
    if (locks) btn.disabled = true;
    try {
      await action(btn);
      await poll();
    } catch (e) {
      toast(e.message);
    } finally {
      if (locks) btn.disabled = false;
    }
  });

  // ---------- seek ----------

  el.seek.addEventListener("input", () => {
    seeking = true;
    el.position.textContent = mmss(Number(el.seek.value));
  });

  el.seek.addEventListener("change", async () => {
    try {
      await api("/api/playback/seek", { position_ms: Number(el.seek.value) });
      await poll();
    } catch (e) {
      toast(e.message);
    } finally {
      seeking = false;
    }
  });

  // ---------- volume ----------

  async function setVolume(volume) {
    if (volume > 0) lastVolume = volume;
    renderVolume(volume);
    await api("/api/playback/volume", { volume });
  }

  el.volume.addEventListener("input", () => {
    volumeDragging = true;
    const volume = Number(el.volume.value) / 100;
    renderVolume(volume);
    clearTimeout(volumeTimer);
    volumeTimer = setTimeout(() => setVolume(volume).catch((e) => toast(e.message)), 120);
  });

  el.volume.addEventListener("change", () => {
    // Let the debounced request land before polling may overwrite the slider.
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
      actions.toggle().then(poll).catch((e) => toast(e.message));
    }
  });

  render(state);
  startPolling();
})();
