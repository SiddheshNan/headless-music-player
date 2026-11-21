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

  const output = $("setting-output");
  const outputStatus = $("output-status");
  let switching = false;

  const label = (name) => name.replace(/\n/g, " · ");

  function renderOutputStatus(audio) {
    outputStatus.replaceChildren();
    const dot = document.createElement("span");
    const text = document.createElement("span");
    if (switching) {
      dot.className = "loading loading-spinner loading-xs text-primary";
      text.className = "text-base-content/60";
      text.textContent = "Switching output…";
    } else if (audio.available) {
      dot.className = "status status-success";
      text.className = "text-base-content/60";
      text.textContent = `Playing through ${label(audio.output || "the system default")}`;
    } else {
      dot.className = "status status-warning";
      text.className = "text-warning";
      text.textContent = `${audio.error || "Output unavailable"}. Retrying every few seconds.`;
    }
    outputStatus.append(dot, text);
  }

  function renderOutputs(devices, selected) {
    const options = [new Option("System default", "", false, !selected)];
    devices.forEach((d) => options.push(new Option(label(d), d, false, d === selected)));
    if (selected && !devices.includes(selected)) {
      options.push(new Option(`${label(selected)} (not connected)`, selected, false, true));
    }
    output.replaceChildren(...options);
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

    if (!switching) output.value = settings.audio.output || "";
    renderOutputStatus(settings.audio);
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

  output.addEventListener("change", async () => {
    switching = true;
    output.disabled = true;
    renderOutputStatus({});
    try {
      const settings = await request("/api/settings", { output: output.value || null });
      switching = false;
      render(settings);
      toast("Output changed", "success");
    } catch (e) {
      switching = false;
      toast(e.message);
      refresh();
    } finally {
      output.disabled = false;
    }
  });

  $("refresh-outputs").addEventListener("click", async (event) => {
    const button = event.currentTarget;
    button.disabled = true;
    try {
      const res = await request("/api/audio/outputs");
      renderOutputs(res.devices, res.selected);
      toast(`${res.devices.length} output${res.devices.length === 1 ? "" : "s"} found`, "info");
    } catch (e) {
      toast(e.message);
    } finally {
      button.disabled = false;
    }
  });
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
