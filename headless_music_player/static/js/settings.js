// Settings page: save each change as it's made, and follow the loudness analysis.
(() => {
  "use strict";

  const $ = (id) => document.getElementById(id);
  const normalize = $("setting-normalize");
  const targetRow = $("target-row");
  const targets = document.querySelectorAll('input[name="loudness_target"]');
  const toasts = $("toasts");
  let pollTimer = null;

  function toast(message, kind = "error") {
    const alert = document.createElement("div");
    alert.className = `alert alert-${kind} alert-soft text-sm shadow-lg`;
    alert.setAttribute("role", "alert");
    alert.textContent = message;
    toasts.append(alert);
    setTimeout(() => alert.remove(), 3000);
  }

  async function request(path, body) {
    const res = await fetch(path, body === undefined ? {} : {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || `Request failed (${res.status})`);
    return data;
  }

  function render(settings) {
    normalize.checked = settings.normalize;
    targetRow.disabled = !settings.normalize;
    targetRow.classList.toggle("opacity-50", !settings.normalize);
    targets.forEach((input) => { input.checked = input.value === settings.loudness_target; });

    const { analyzed, total } = settings.analysis;
    const done = total > 0 && analyzed >= total;
    $("analysis-text").textContent = total === 0
      ? "No songs yet."
      : done
        ? `All ${total} songs measured.`
        : `Measuring loudness in the background: ${analyzed} of ${total} songs.`;
    $("analysis-done").classList.toggle("hidden", !done);
    $("analysis-busy").classList.toggle("hidden", done || !total);
    const progress = $("analysis-progress");
    progress.max = total || 1;
    progress.value = analyzed;
    progress.classList.toggle("hidden", !total || done);
    $("library-tracks").textContent = `${total} songs`;
  }

  async function save(change) {
    try {
      render(await request("/api/settings", change));
      toast("Saved", "success");
    } catch (e) {
      toast(e.message);
      refresh();
    }
  }

  async function refresh() {
    try {
      render(await request("/api/settings"));
    } catch (e) { /* try again on the next poll */ }
  }

  normalize.addEventListener("change", () => save({ normalize: normalize.checked }));
  targets.forEach((input) => input.addEventListener("change", () => save({ loudness_target: input.value })));

  $("rescan").addEventListener("click", async (event) => {
    const button = event.currentTarget;
    button.disabled = true;
    try {
      const res = await request("/api/library/rescan", {});
      toast(`Library rescanned: ${res.total} songs (${res.added} new, ${res.removed} removed)`, "success");
      refresh();
    } catch (e) {
      toast(e.message);
    } finally {
      button.disabled = false;
    }
  });

  function startPolling() {
    clearInterval(pollTimer);
    pollTimer = setInterval(refresh, 2000);
  }
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) clearInterval(pollTimer);
    else { refresh(); startPolling(); }
  });
  startPolling();
})();
