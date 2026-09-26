import { api } from "../../api.js";
import { createStoryViewer } from "./story-viewer.js";

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function formatDate(value) {
  if (!value) {
    return "Unknown date";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "Unknown date";
  }

  return date.toLocaleDateString(undefined, {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

function formatDuration(seconds) {
  if (!Number.isFinite(Number(seconds)) || Number(seconds) < 0) {
    return "";
  }

  const total = Math.round(Number(seconds));
  const minutes = Math.floor(total / 60);
  const remaining = total % 60;

  return `${minutes}:${String(remaining).padStart(2, "0")}`;
}

function formatFilesize(bytes) {
  if (!Number.isFinite(Number(bytes)) || Number(bytes) <= 0) {
    return "";
  }

  const value = Number(bytes);

  if (value < 1024 * 1024) {
    return `${Math.round(value / 1024)} KB`;
  }

  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}

function statusLabel(status) {
  return {
    completed: "Ready",
    processing: "Processing",
    queued: "Queued",
    failed: "Failed",
  }[status] || "Unknown";
}

function statusClass(status) {
  return String(status || "unknown").replace(/[^a-z0-9_-]/gi, "");
}

function renderMeta(item) {
  const parts = [
    formatDuration(item.duration),
    formatFilesize(item.filesize),
  ].filter(Boolean);

  return parts.length
    ? `<span class="reel-card-meta">${parts.map(escapeHtml).join(" · ")}</span>`
    : "";
}

function renderCompletedMedia(item) {
  return `
    <button
      type="button"
      class="reel-card-media reel-card-media--video reel-card-media-trigger"
      data-story-open-id="${escapeHtml(item.id)}"
      aria-label="Open ${escapeHtml(item.title || "Instagram Reel")} in Reel viewer"
    >
      <video
        class="reel-card-video"
        src="/api/file/${encodeURIComponent(item.id)}"
        preload="metadata"
        muted
        playsinline
        tabindex="-1"
        aria-hidden="true"
      ></video>
      <span class="reel-card-play" aria-hidden="true">▶</span>
      <span class="reel-card-open-label">Open Reel</span>
    </button>
  `;
}

function renderPendingMedia(item) {
  const isFailed = item.status === "failed";

  return `
    <div class="reel-card-media reel-card-media--state ${isFailed ? "is-failed" : ""}">
      <span class="reel-card-state-icon" aria-hidden="true">
        ${isFailed ? "!" : "…"}
      </span>
      <span class="reel-card-state-label">
        ${escapeHtml(statusLabel(item.status))}
      </span>
    </div>
  `;
}

function renderReelCard(item, variant = "grid") {
  const title = escapeHtml(item.title || "Instagram Reel");
  const status = escapeHtml(item.status || "unknown");
  const statusText = escapeHtml(statusLabel(item.status));
  const date = escapeHtml(formatDate(item.created_at));
  const error = item.error_message
    ? `<p class="reel-card-error">${escapeHtml(item.error_message)}</p>`
    : "";

  const media =
    item.status === "completed"
      ? renderCompletedMedia(item)
      : renderPendingMedia(item);

  const actions =
    item.status === "completed"
      ? `
        <div class="reel-card-actions">
          <a
            class="button button-secondary button-small"
            href="/api/file/${encodeURIComponent(item.id)}"
            download
          >
            Download
          </a>
          <button
            type="button"
            class="button button-danger button-small"
            data-delete-id="${escapeHtml(item.id)}"
          >
            Delete
          </button>
        </div>
      `
      : `
        <div class="reel-card-actions">
          <button
            type="button"
            class="button button-danger button-small"
            data-delete-id="${escapeHtml(item.id)}"
          >
            Delete
          </button>
        </div>
      `;

  return `
    <article
      class="reel-card reel-card--${escapeHtml(variant)} reel-card--${statusClass(status)}"
      data-reel-id="${escapeHtml(item.id)}"
    >
      ${media}

      <div class="reel-card-body">
        <div class="reel-card-heading">
          <div>
            <span class="reel-card-kicker">${statusText}</span>
            <h3 title="${title}">${title}</h3>
          </div>
          <time datetime="${escapeHtml(item.created_at || "")}">
            ${date}
          </time>
        </div>

        ${renderMeta(item)}
        ${error}
        ${actions}
      </div>
    </article>
  `;
}

export function createHistoryCard() {
  const card = document.createElement("section");
  card.className = "workspace-card history-workspace";

  const storyViewer = createStoryViewer();
  card.append(storyViewer.element);

  const heading = document.createElement("div");
  heading.className = "workspace-section-heading";

  const copy = document.createElement("div");
  copy.innerHTML = `
    <span class="workspace-kicker">Your library</span>
    <h2>Your Reels</h2>
  `;

  const refresh = document.createElement("button");
  refresh.type = "button";
  refresh.className = "button button-ghost button-small history-refresh";
  refresh.setAttribute("aria-label", "Refresh Reel library");
  refresh.innerHTML = `
    <span class="refresh-symbol" aria-hidden="true">↻</span>
    <span>Refresh</span>
  `;

  heading.append(copy, refresh);

  const history = document.createElement("div");
  history.className = "history-list";

  card.append(heading, history);
  history._storyViewer = storyViewer;

  return {
    card,
    history,
    refresh,
    storyViewer,
  };
}

export async function refreshHistory(workspace) {
  workspace.refresh.disabled = true;
  workspace.refresh.classList.add("is-refreshing");

  try {
    await loadHistory(workspace.history);
  } finally {
    workspace.refresh.disabled = false;
    workspace.refresh.classList.remove("is-refreshing");
  }
}

export async function loadHistory(container) {
  try {
    const items = await api("/api/history");
    container._historyItems = items;

    if (!items.length) {
      container.innerHTML = `
        <div class="empty-state reel-library-empty">
          <div class="empty-state__icon" aria-hidden="true">▶</div>
          <strong>No Reels yet</strong>
          <p>Your converted Reels will appear here. Start by pasting a Reel link above.</p>
        </div>
      `;
      return;
    }

    const recentItems = items.slice(0, 4);

    container.innerHTML = `
      <section class="reel-library-section reel-library-recent">
        <div class="reel-library-section-heading">
          <div>
            <span class="workspace-kicker">Latest</span>
            <h2>Recent Reels</h2>
          </div>
          <span class="reel-library-count">${items.length} saved</span>
        </div>

        <div class="reel-recent-strip">
          ${recentItems
            .map((item) => renderReelCard(item, "recent"))
            .join("")}
        </div>
      </section>

      <section class="reel-library-section reel-library-all">
        <div class="reel-library-section-heading">
          <div>
            <span class="workspace-kicker">Library</span>
            <h2>All Converted Reels</h2>
          </div>
        </div>

        <div class="reel-grid">
          ${items.map((item) => renderReelCard(item, "grid")).join("")}
        </div>
      </section>
    `;

    bindStoryViewerButtons(container);
    bindDeleteButtons(container);
  } catch (error) {
    container.innerHTML = `
      <div class="history-error-state">
        <strong>Couldn't load your library</strong>
        <p>${escapeHtml(error.message)}</p>
      </div>
    `;
  }
}

function bindStoryViewerButtons(container) {
  const viewer = container._storyViewer;

  if (!viewer) {
    return;
  }

  const completedItems = Array.from(
    container.querySelectorAll("[data-reel-id]")
  )
    .map((card) => {
      const id = card.dataset.reelId;

      return id
        ? {
            id,
            status: "completed",
          }
        : null;
    })
    .filter(Boolean);

  const historyItems = container._historyItems || [];

  container.querySelectorAll("[data-story-open-id]").forEach((button) => {
    button.addEventListener("click", () => {
      const id = button.dataset.storyOpenId;

      if (!id) {
        return;
      }

      viewer.open(
        historyItems.length ? historyItems : completedItems,
        id
      );
    });
  });
}

function bindDeleteButtons(container) {
  container.querySelectorAll("[data-delete-id]").forEach((button) => {
    button.addEventListener("click", async () => {
      const downloadId = button.dataset.deleteId;

      if (!downloadId) {
        return;
      }

      if (button.dataset.confirming !== "true") {
        button.dataset.confirming = "true";
        button.textContent = "Confirm delete";
        button.classList.add("is-confirming");

        window.setTimeout(() => {
          if (button.isConnected && button.dataset.confirming === "true") {
            button.dataset.confirming = "false";
            button.textContent = "Delete";
            button.classList.remove("is-confirming");
          }
        }, 4000);

        return;
      }

      button.disabled = true;
      button.textContent = "Deleting…";

      try {
        await api(`/api/history/${encodeURIComponent(downloadId)}`, {
          method: "DELETE",
        });

        await loadHistory(container);
      } catch (error) {
        button.disabled = false;
        button.dataset.confirming = "false";
        button.textContent = "Delete";
        button.classList.remove("is-confirming");

        const errorMessage = document.createElement("p");
        errorMessage.className = "inline-error";
        errorMessage.textContent = error.message;
        container.prepend(errorMessage);
      }
    });
  });
}
