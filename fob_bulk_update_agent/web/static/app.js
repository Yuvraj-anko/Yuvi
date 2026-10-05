const form = document.getElementById("form");
const fileInput = document.getElementById("file");
const drop = document.getElementById("drop");
const fileName = document.getElementById("file-name");
const submit = document.getElementById("submit");
const statusEl = document.getElementById("status");

function setStatus(message, kind) {
  statusEl.hidden = !message;
  statusEl.textContent = message || "";
  statusEl.classList.remove("error", "ok");
  if (kind) statusEl.classList.add(kind);
}

fileInput.addEventListener("change", () => {
  const file = fileInput.files && fileInput.files[0];
  submit.disabled = !file;
  fileName.textContent = file
    ? file.name
    : "Accepts PO Number / CASE PACK ID / FOB";
  setStatus("");
});

["dragenter", "dragover"].forEach((evt) => {
  drop.addEventListener(evt, (e) => {
    e.preventDefault();
    drop.classList.add("dragover");
  });
});

["dragleave", "drop"].forEach((evt) => {
  drop.addEventListener(evt, (e) => {
    e.preventDefault();
    drop.classList.remove("dragover");
  });
});

drop.addEventListener("drop", (e) => {
  const files = e.dataTransfer && e.dataTransfer.files;
  if (!files || !files.length) return;
  fileInput.files = files;
  fileInput.dispatchEvent(new Event("change"));
});

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const file = fileInput.files && fileInput.files[0];
  if (!file) return;

  submit.disabled = true;
  setStatus("Cleaning…");

  try {
    const body = new FormData();
    body.append("file", file, file.name);
    const res = await fetch("/clean", { method: "POST", body });
    if (!res.ok) {
      let detail = "Clean failed";
      try {
        const data = await res.json();
        detail = data.detail || detail;
      } catch (_) {
        detail = (await res.text()) || detail;
      }
      throw new Error(detail);
    }

    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = file.name;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);

    const rows = res.headers.get("X-FOB-Row-Count") || "?";
    const pos = res.headers.get("X-FOB-PO-Count") || "?";
    setStatus(`Downloaded ${file.name} — ${rows} rows, ${pos} POs`, "ok");
  } catch (err) {
    setStatus(err.message || String(err), "error");
  } finally {
    submit.disabled = !(fileInput.files && fileInput.files[0]);
  }
});
