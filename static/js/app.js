// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function $(sel) { return document.querySelector(sel); }
function $$(sel) { return document.querySelectorAll(sel); }

function formatSize(bytes) {
    if (!bytes) return "0 B";
    const units = ["B", "KB", "MB", "GB", "TB"];
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return (bytes / Math.pow(1024, i)).toFixed(1) + " " + units[i];
}

function formatSpeed(bytes) {
    return formatSize(bytes) + "/s";
}

function formatETA(seconds) {
    if (seconds <= 0 || seconds >= 8640000) return "\u221e";
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = seconds % 60;
    if (h > 0) return `${h}h ${m}m`;
    if (m > 0) return `${m}m ${s}s`;
    return `${s}s`;
}

function showToast(msg, isError = false) {
    const toast = $("#toast");
    toast.textContent = msg;
    toast.classList.toggle("error", isError);
    toast.classList.remove("hidden");
    clearTimeout(showToast._t);
    showToast._t = setTimeout(() => toast.classList.add("hidden"), 2500);
}

async function api(path, opts = {}) {
    const resp = await fetch(path, {
        headers: { "Content-Type": "application/json" },
        ...opts,
    });
    return resp.json();
}

// ---------------------------------------------------------------------------
// Tabs
// ---------------------------------------------------------------------------
$$(".tab").forEach(tab => {
    tab.addEventListener("click", () => {
        $$(".tab").forEach(t => t.classList.remove("active"));
        $$(".tab-content").forEach(c => c.classList.remove("active"));
        tab.classList.add("active");
        $(`#tab-${tab.dataset.tab}`).classList.add("active");
        if (tab.dataset.tab === "downloads") refreshDownloads();
    });
});

// ---------------------------------------------------------------------------
// Search
// ---------------------------------------------------------------------------
const searchInput = $("#search-input");
const searchBtn = $("#search-btn");
const searchResults = $("#search-results");

async function doSearch() {
    const query = searchInput.value.trim();
    if (!query) return;

    searchBtn.disabled = true;
    searchResults.innerHTML = '<div class="spinner"></div>';

    try {
        const results = await api(`/api/search?query=${encodeURIComponent(query)}`);
        if (results.length === 0) {
            searchResults.innerHTML = '<div class="empty-state">No results found</div>';
            return;
        }
        searchResults.innerHTML = results.map(renderResult).join("");
    } catch (e) {
        searchResults.innerHTML = '<div class="empty-state">Search failed. Check your Prowlarr connection.</div>';
    } finally {
        searchBtn.disabled = false;
    }
}

function renderResult(r) {
    const url = r.magnetUrl || r.downloadUrl;
    const downloadBtn = url
        ? `<button class="btn-sm btn-download" onclick="addTorrent('${escapeAttr(url)}')">Download</button>`
        : "";
    const infoBtn = r.infoUrl
        ? `<button class="btn-sm btn-info" onclick="window.open('${escapeAttr(r.infoUrl)}', '_blank')">Info</button>`
        : "";

    return `
        <div class="result-card">
            <div class="result-title">${escapeHtml(r.title)}</div>
            <div class="result-meta">
                <span>${formatSize(r.size)}</span>
                <span class="seeders">S: ${r.seeders}</span>
                <span class="leechers">L: ${r.leechers}</span>
                <span>${escapeHtml(r.indexer)}</span>
            </div>
            <div class="result-actions">
                ${downloadBtn}
                ${infoBtn}
            </div>
        </div>`;
}

function escapeHtml(s) {
    const d = document.createElement("div");
    d.textContent = s;
    return d.innerHTML;
}

function escapeAttr(s) {
    return s.replace(/'/g, "\\'").replace(/"/g, "&quot;");
}

async function addTorrent(url) {
    try {
        const body = url.startsWith("magnet:") ? { magnetUrl: url } : { downloadUrl: url };
        const resp = await api("/api/torrents/add", {
            method: "POST",
            body: JSON.stringify(body),
        });
        if (resp.status === "ok") {
            showToast("Torrent added!");
        } else {
            showToast(resp.error || "Failed to add torrent", true);
        }
    } catch {
        showToast("Failed to add torrent", true);
    }
}

searchBtn.addEventListener("click", doSearch);
searchInput.addEventListener("keydown", e => { if (e.key === "Enter") doSearch(); });

// ---------------------------------------------------------------------------
// Downloads
// ---------------------------------------------------------------------------
const downloadsList = $("#downloads-list");
let refreshInterval = null;

function stateClass(state) {
    if (state.includes("paused")) return "paused";
    if (state.includes("stalled")) return "stalled";
    if (state.includes("download")) return "downloading";
    if (state.includes("upload") || state === "seeding") return "seeding";
    if (state.includes("error") || state === "missingFiles") return "error";
    if (state.includes("queued") || state === "checkingDL" || state === "checkingUP") return "queued";
    if (state === "pausedUP" || state === "completed") return "complete";
    return "queued";
}

function stateLabel(state) {
    const map = {
        downloading: "DL", uploading: "UL", stalledDL: "Stalled",
        stalledUP: "Seeding", pausedDL: "Paused", pausedUP: "Done",
        queuedDL: "Queued", queuedUP: "Queued", checkingDL: "Checking",
        checkingUP: "Checking", missingFiles: "Error", error: "Error",
        seeding: "Seeding", completed: "Done",
    };
    return map[state] || state;
}

function renderDownload(t) {
    const pct = (t.progress * 100).toFixed(1);
    const sc = stateClass(t.state);
    const isPaused = t.state.includes("paused");
    const isActive = t.state.includes("download") || t.state.includes("stalled");

    return `
        <div class="download-card" data-hash="${t.hash}">
            <div class="download-name">${escapeHtml(t.name)}</div>
            <div class="download-stats">
                <span class="state-badge state-${sc}">${stateLabel(t.state)}</span>
                <span>${pct}%</span>
                <span>${formatSize(t.size)}</span>
                ${isActive ? `<span>\u2193 ${formatSpeed(t.dlspeed)}</span>` : ""}
                ${t.upspeed > 0 ? `<span>\u2191 ${formatSpeed(t.upspeed)}</span>` : ""}
                ${isActive ? `<span>ETA: ${formatETA(t.eta)}</span>` : ""}
            </div>
            <div class="progress-bar">
                <div class="progress-fill ${pct >= 100 ? "complete" : sc === "stalled" ? "stalled" : ""}" style="width:${pct}%"></div>
            </div>
            <div class="download-actions">
                ${isPaused
                    ? `<button class="btn-sm btn-resume" onclick="resumeTorrent('${t.hash}')">Resume</button>`
                    : `<button class="btn-sm btn-pause" onclick="pauseTorrent('${t.hash}')">Pause</button>`
                }
                <button class="btn-sm btn-delete" onclick="confirmDelete('${t.hash}', '${escapeAttr(t.name)}')">Delete</button>
            </div>
        </div>`;
}

async function refreshDownloads() {
    try {
        const torrents = await api("/api/torrents");
        if (torrents.length === 0) {
            downloadsList.innerHTML = '<div class="empty-state">No active downloads</div>';
        } else {
            downloadsList.innerHTML = torrents.map(renderDownload).join("");
        }
    } catch {
        downloadsList.innerHTML = '<div class="empty-state">Failed to connect to qBittorrent</div>';
    }
}

async function pauseTorrent(hash) {
    await api("/api/torrents/pause", { method: "POST", body: JSON.stringify({ hash }) });
    showToast("Torrent paused");
    refreshDownloads();
}

async function resumeTorrent(hash) {
    await api("/api/torrents/resume", { method: "POST", body: JSON.stringify({ hash }) });
    showToast("Torrent resumed");
    refreshDownloads();
}

// Delete confirmation
let pendingDeleteHash = null;
const modalOverlay = $("#modal-overlay");
const modalMessage = $("#modal-message");

function confirmDelete(hash, name) {
    pendingDeleteHash = hash;
    modalMessage.innerHTML = `
        Delete <strong>${name}</strong>?
        <div class="checkbox-row">
            <input type="checkbox" id="delete-files"> <label for="delete-files">Also delete files from disk</label>
        </div>`;
    modalOverlay.classList.remove("hidden");
}

$("#modal-cancel").addEventListener("click", () => {
    modalOverlay.classList.add("hidden");
    pendingDeleteHash = null;
});

$("#modal-confirm").addEventListener("click", async () => {
    if (!pendingDeleteHash) return;
    const deleteFiles = $("#delete-files")?.checked || false;
    await api("/api/torrents/delete", {
        method: "POST",
        body: JSON.stringify({ hash: pendingDeleteHash, deleteFiles }),
    });
    modalOverlay.classList.add("hidden");
    pendingDeleteHash = null;
    showToast("Torrent deleted");
    refreshDownloads();
});

// Auto-refresh when downloads tab is visible
const observer = new MutationObserver(() => {
    const active = $("#tab-downloads").classList.contains("active");
    if (active && !refreshInterval) {
        refreshDownloads();
        refreshInterval = setInterval(refreshDownloads, 3000);
    } else if (!active && refreshInterval) {
        clearInterval(refreshInterval);
        refreshInterval = null;
    }
});
observer.observe($("#tab-downloads"), { attributes: true, attributeFilter: ["class"] });

$("#refresh-btn").addEventListener("click", refreshDownloads);

// ---------------------------------------------------------------------------
// Move Files
// ---------------------------------------------------------------------------
async function moveFiles(type) {
    const label = type === "movie" ? "Movies" : "TV Shows";
    if (!confirm(`Move all files from Torrents to ${label}?`)) return;

    try {
        const resp = await api("/api/files/move", {
            method: "POST",
            body: JSON.stringify({ type }),
        });
        if (resp.status === "ok") {
            showToast(`Moved ${resp.moved} item(s) to ${label}`);
        } else if (resp.status === "partial") {
            showToast(`Moved ${resp.moved}, ${resp.errors.length} failed`, true);
        } else {
            showToast(resp.error || "Move failed", true);
        }
    } catch {
        showToast("Failed to move files", true);
    }
}
