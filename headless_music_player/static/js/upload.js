// Upload modal: collect songs (drop or browse, adding up across drops), then upload them
// one at a time with per-file progress. Uses window.hmp (toast, refresh) from app.js.
(() => {
  "use strict";

  const modal = document.getElementById("upload-modal");
  if (!modal) return;

  const $ = (id) => document.getElementById(id);
  const dropzone = $("upload-dropzone");
  const input = $("upload-input");
  const list = $("upload-list");
  const rowTemplate = $("upload-row");
  const summary = $("upload-summary");
  const submit = $("upload-submit");
  const submitLabel = $("upload-submit-label");
  const spinner = $("upload-spinner");
  const queueButton = $("upload-queue");
  const openButton = $("upload-open");
  const headerBadge = $("upload-badge");
  const headerIcon = $("upload-icon");

  const MAX_BYTES = Number(modal.dataset.maxBytes) || Infinity;
  const EXTENSIONS = modal.dataset.extensions.split(",");

  /** @type {{id:number, file:File, status:string, progress:number, message:string, trackId:string|null, row:HTMLElement}[]} */
  let items = [];
  let nextId = 1;
  let uploading = false;

  // ---------- helpers ----------

  function formatSize(bytes) {
    if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`;
    if (bytes < 1024 * 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
    return `${(bytes / 1024 / 1024 / 1024).toFixed(2)} GB`;
  }

  function extensionOf(name) {
    const dot = name.lastIndexOf(".");
    return dot === -1 ? "" : name.slice(dot).toLowerCase();
  }

  function plural(n, word) {
    return `${n} ${word}${n === 1 ? "" : "s"}`;
  }

  const STATUS_TEXT = {
    ready: () => "Ready",
    uploading: (item) => (item.progress >= 100 ? "Processing…" : `Uploading… ${item.progress}%`),
    done: () => "Added to the library",
    duplicate: () => "Already in your library",
    error: (item) => item.message,
  };

  // ---------- adding files ----------

  function addFiles(files) {
    let skipped = 0;
    for (const file of files) {
      const already = items.some(
        (i) => i.file.name === file.name && i.file.size === file.size && i.file.lastModified === file.lastModified,
      );
      if (already) {
        skipped += 1;
        continue;
      }
      const item = { id: nextId++, file, status: "ready", progress: 0, message: "", trackId: null };
      if (!EXTENSIONS.includes(extensionOf(file.name))) {
        item.status = "error";
        item.message = "Unsupported file type";
      } else if (file.size > MAX_BYTES) {
        item.status = "error";
        item.message = `Larger than ${formatSize(MAX_BYTES)}`;
      } else if (file.size === 0) {
        item.status = "error";
        item.message = "The file is empty";
      }
      item.row = createRow(item);
      items.push(item);
      list.append(item.row);
    }
    if (skipped) window.hmp.toast(`${plural(skipped, "file")} already in the list`, "info");
    update();
  }

  function createRow(item) {
    const row = rowTemplate.content.firstElementChild.cloneNode(true);
    row.dataset.id = item.id;
    row.querySelector(".upload-name").textContent = item.file.name;
    row.querySelector(".upload-name").title = item.file.name;
    row.querySelector(".upload-size").textContent = formatSize(item.file.size);
    row.querySelector(".upload-remove").addEventListener("click", () => removeItem(item.id));
    renderRow(item, row);
    return row;
  }

  function renderRow(item, row = item.row) {
    row.dataset.status = item.status;
    row.querySelectorAll("[data-show]").forEach((node) => {
      node.classList.toggle("hidden", !node.dataset.show.split(" ").includes(item.status));
    });
    const status = row.querySelector(".upload-status");
    status.textContent = STATUS_TEXT[item.status](item);
    status.title = status.textContent;
    status.classList.toggle("text-error", item.status === "error");
    status.classList.toggle("text-success", item.status === "done");

    const icon = row.querySelector(".upload-icon");
    icon.classList.toggle("bg-success/15", item.status === "done" || item.status === "duplicate");
    icon.classList.toggle("bg-error/15", item.status === "error");
    icon.classList.toggle("bg-primary/10", item.status === "uploading");

    const progress = row.querySelector(".upload-progress");
    progress.classList.toggle("hidden", item.status !== "uploading");
    progress.value = item.progress;
  }

  function removeItem(id) {
    const item = items.find((i) => i.id === id);
    if (!item || item.status === "uploading") return;
    item.row.remove();
    items = items.filter((i) => i.id !== id);
    update();
  }

  // ---------- footer and header ----------

  function update() {
    const ready = items.filter((i) => i.status === "ready");
    const finished = items.filter((i) => i.status === "done" || i.status === "duplicate");
    const failed = items.filter((i) => i.status === "error");
    const current = items.find((i) => i.status === "uploading");

    if (items.length) dropzone.dataset.compact = "";
    else delete dropzone.dataset.compact;

    if (!items.length) {
      summary.textContent = "No songs added yet";
    } else {
      const parts = [];
      if (ready.length) parts.push(`${plural(ready.length, "song")} · ${formatSize(ready.reduce((n, i) => n + i.file.size, 0))}`);
      if (finished.length) parts.push(`${finished.length} uploaded`);
      if (failed.length) parts.push(`${failed.length} can't be uploaded`);
      summary.textContent = parts.join(" · ");
    }

    spinner.classList.toggle("hidden", !uploading);
    if (uploading) {
      const total = items.filter((i) => i.status !== "error" || i.attempted).length;
      const position = items.filter((i) => i.attempted).length;
      submitLabel.textContent = `Uploading ${position} of ${total}`;
      submit.disabled = true;
    } else if (ready.length) {
      submitLabel.textContent = `Upload ${plural(ready.length, "song")}`;
      submit.disabled = false;
    } else if (finished.length) {
      submitLabel.textContent = "Done";
      submit.disabled = false;
    } else {
      submitLabel.textContent = "Upload";
      submit.disabled = true;
    }

    queueButton.classList.toggle("hidden", uploading || !finished.some((i) => i.trackId));
    headerBadge.classList.toggle("hidden", !uploading);
    headerIcon.classList.toggle("hidden", uploading);
    openButton.title = uploading ? `Uploading ${current ? current.file.name : ""}` : "Upload songs";
  }

  // ---------- uploading ----------

  function uploadOne(item) {
    return new Promise((resolve) => {
      const xhr = new XMLHttpRequest();
      const form = new FormData();
      form.append("file", item.file, item.file.name);

      xhr.upload.addEventListener("progress", (event) => {
        if (!event.lengthComputable) return;
        item.progress = Math.min(100, Math.round((event.loaded / event.total) * 100));
        renderRow(item);
      });
      xhr.addEventListener("load", () => {
        let data = {};
        try { data = JSON.parse(xhr.responseText); } catch (e) { /* not JSON */ }
        if (xhr.status >= 200 && xhr.status < 300) {
          item.status = data.duplicate ? "duplicate" : "done";
          item.trackId = data.track ? data.track.id : null;
        } else {
          item.status = "error";
          item.message = data.error || `Upload failed (${xhr.status})`;
        }
        resolve();
      });
      xhr.addEventListener("error", () => {
        item.status = "error";
        item.message = "Connection lost";
        resolve();
      });
      xhr.open("POST", "/api/library/upload");
      xhr.send(form);
    });
  }

  async function uploadAll() {
    if (uploading) return;
    uploading = true;
    items.forEach((i) => { i.attempted = false; });
    const batch = items.filter((i) => i.status === "ready");
    for (const item of batch) {
      if (!items.includes(item)) continue;
      item.status = "uploading";
      item.progress = 0;
      item.attempted = true;
      renderRow(item);
      update();
      await uploadOne(item);
      renderRow(item);
      update();
    }
    uploading = false;
    update();

    const added = batch.filter((i) => i.status === "done").length;
    const failed = batch.filter((i) => i.status === "error").length;
    if (added) window.hmp.toast(`Added ${plural(added, "song")} to the library`, "success");
    if (failed) window.hmp.toast(`${plural(failed, "song")} couldn't be uploaded`);
    window.hmp.refresh();
  }

  submit.addEventListener("click", () => {
    if (items.some((i) => i.status === "ready")) {
      uploadAll();
    } else {
      // "Done": clear what finished and close.
      items.filter((i) => i.status !== "error").forEach((i) => removeItem(i.id));
      modal.close();
    }
  });

  queueButton.addEventListener("click", async () => {
    const trackIds = items.filter((i) => i.trackId).map((i) => i.trackId);
    try {
      const res = await fetch("/api/queue/add", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ track_ids: trackIds }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Couldn't add to the queue");
      window.hmp.toast(`Queued ${plural(trackIds.length, "song")}`, "success");
      items.filter((i) => i.trackId).forEach((i) => removeItem(i.id));
      window.hmp.refresh();
    } catch (e) {
      window.hmp.toast(e.message);
    }
  });

  // ---------- opening, browsing, dropping ----------

  function open() {
    if (!modal.open) modal.showModal();
  }

  openButton.addEventListener("click", open);

  input.addEventListener("change", () => {
    addFiles(input.files);
    input.value = "";
  });

  const hasFiles = (event) => Array.from(event.dataTransfer?.types || []).includes("Files");
  let dragDepth = 0;

  // Dragging songs anywhere over the page opens the modal; dropping anywhere adds them.
  window.addEventListener("dragenter", (event) => {
    if (!hasFiles(event)) return;
    event.preventDefault();
    dragDepth += 1;
    open();
    dropzone.dataset.dragging = "";
  });
  window.addEventListener("dragover", (event) => {
    if (!hasFiles(event)) return;
    event.preventDefault();
    event.dataTransfer.dropEffect = "copy";
  });
  window.addEventListener("dragleave", (event) => {
    if (!hasFiles(event)) return;
    dragDepth = Math.max(0, dragDepth - 1);
    if (dragDepth === 0) delete dropzone.dataset.dragging;
  });
  window.addEventListener("drop", (event) => {
    if (!hasFiles(event)) return;
    event.preventDefault();
    dragDepth = 0;
    delete dropzone.dataset.dragging;
    addFiles(event.dataTransfer.files);
  });

  window.addEventListener("beforeunload", (event) => {
    if (uploading) event.preventDefault();
  });

  update();
})();
