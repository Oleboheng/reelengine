function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
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

export function createStoryViewer() {
  const overlay = document.createElement("div");
  overlay.className = "story-viewer";
  overlay.hidden = true;
  overlay.setAttribute("aria-hidden", "true");

  overlay.innerHTML = `
    <div class="story-viewer-backdrop" data-story-close></div>

    <section
      class="story-viewer-panel"
      role="dialog"
      aria-modal="true"
      aria-label="Reel viewer"
      tabindex="-1"
    >
      <div class="story-viewer-topbar">
        <div class="story-viewer-progress" aria-hidden="true"></div>

        <button
          type="button"
          class="story-viewer-close"
          data-story-close
          aria-label="Close Reel viewer"
        >
          ×
        </button>
      </div>

      <div class="story-viewer-stage">
        <button
          type="button"
          class="story-viewer-nav story-viewer-nav--previous"
          data-story-previous
          aria-label="Previous Reel"
        >
          ‹
        </button>

        <div class="story-viewer-video-wrap">
          <video
            class="story-viewer-video"
            playsinline
            controls
            preload="metadata"
          ></video>

          <div class="story-viewer-loading" aria-hidden="true">
            <span class="story-viewer-spinner"></span>
            <span>Loading Reel…</span>
          </div>

          <div class="story-viewer-error" hidden>
            <strong>Couldn't play this Reel</strong>
            <span>Try another Reel or close the viewer.</span>
          </div>
        </div>

        <button
          type="button"
          class="story-viewer-nav story-viewer-nav--next"
          data-story-next
          aria-label="Next Reel"
        >
          ›
        </button>
      </div>

      <div class="story-viewer-info">
        <div class="story-viewer-copy">
          <span class="story-viewer-kicker">Your Reel</span>
          <h2 class="story-viewer-title"></h2>
          <span class="story-viewer-meta"></span>
        </div>

        <a
          class="button button-secondary button-small story-viewer-download"
          href="#"
          download
        >
          Download
        </a>
      </div>
    </section>
  `;

  document.body.append(overlay);

  const panel = overlay.querySelector(".story-viewer-panel");
  const video = overlay.querySelector(".story-viewer-video");
  const title = overlay.querySelector(".story-viewer-title");
  const meta = overlay.querySelector(".story-viewer-meta");
  const download = overlay.querySelector(".story-viewer-download");
  const progress = overlay.querySelector(".story-viewer-progress");
  const loading = overlay.querySelector(".story-viewer-loading");
  const error = overlay.querySelector(".story-viewer-error");
  const previous = overlay.querySelector("[data-story-previous]");
  const next = overlay.querySelector("[data-story-next]");

  let items = [];
  let currentIndex = -1;
  let lastFocusedElement = null;
  let touchStartX = 0;
  let touchStartY = 0;

  function completedItems(source) {
    const seen = new Set();

    return source.filter((item) => {
      if (item.status !== "completed" || !item.id || seen.has(item.id)) {
        return false;
      }

      seen.add(item.id);
      return true;
    });
  }

  function updateNavigation() {
    const count = items.length;

    previous.disabled = count <= 1;
    next.disabled = count <= 1;

    previous.hidden = count <= 1;
    next.hidden = count <= 1;

    progress.innerHTML = items
      .map(
        (_, index) => `
          <span
            class="story-viewer-progress-segment ${
              index === currentIndex ? "is-active" : ""
            }"
          ></span>
        `
      )
      .join("");
  }

  function stopVideo() {
    video.pause();
    video.removeAttribute("src");
    video.load();
  }

  function showLoading() {
    loading.hidden = false;
    error.hidden = true;
  }

  function hideLoading() {
    loading.hidden = true;
  }

  function showError() {
    loading.hidden = true;
    error.hidden = false;
  }

  async function showItem(index) {
    if (!items.length) {
      return;
    }

    currentIndex =
      (index + items.length) % items.length;

    const item = items[currentIndex];
    const fileUrl = `/api/file/${encodeURIComponent(item.id)}`;

    stopVideo();
    showLoading();

    title.textContent = item.title || "Instagram Reel";

    const duration = formatDuration(item.duration);
    meta.textContent = duration
      ? duration
      : "Converted Reel";

    download.href = fileUrl;
    download.setAttribute(
      "aria-label",
      `Download ${item.title || "Instagram Reel"}`
    );

    updateNavigation();

    video.src = fileUrl;
    video.load();

    try {
      await video.play();
    } catch {
      // Autoplay can be blocked by the browser.
      // The native controls remain available.
    }
  }

  function close() {
    if (overlay.hidden) {
      return;
    }

    stopVideo();

    overlay.hidden = true;
    overlay.setAttribute("aria-hidden", "true");
    document.body.classList.remove("story-viewer-open");

    if (lastFocusedElement instanceof HTMLElement) {
      lastFocusedElement.focus();
    }

    lastFocusedElement = null;
  }

  function open(sourceItems, itemId) {
    items = completedItems(sourceItems);

    if (!items.length) {
      return;
    }

    const index = items.findIndex((item) => item.id === itemId);

    if (index < 0) {
      return;
    }

    lastFocusedElement = document.activeElement;

    overlay.hidden = false;
    overlay.setAttribute("aria-hidden", "false");
    document.body.classList.add("story-viewer-open");

    panel.focus();
    void showItem(index);
  }

  function goPrevious() {
    if (items.length > 1) {
      void showItem(currentIndex - 1);
    }
  }

  function goNext() {
    if (items.length > 1) {
      void showItem(currentIndex + 1);
    }
  }

  function handleKeydown(event) {
    if (overlay.hidden) {
      return;
    }

    if (event.key === "Escape") {
      event.preventDefault();
      close();
      return;
    }

    if (event.key === "ArrowLeft") {
      event.preventDefault();
      goPrevious();
      return;
    }

    if (event.key === "ArrowRight") {
      event.preventDefault();
      goNext();
    }
  }

  function handleTouchStart(event) {
    const touch = event.changedTouches[0];

    if (!touch) {
      return;
    }

    touchStartX = touch.clientX;
    touchStartY = touch.clientY;
  }

  function handleTouchEnd(event) {
    const touch = event.changedTouches[0];

    if (!touch) {
      return;
    }

    const deltaX = touch.clientX - touchStartX;
    const deltaY = touch.clientY - touchStartY;

    if (Math.abs(deltaX) < 60 || Math.abs(deltaX) <= Math.abs(deltaY)) {
      return;
    }

    if (deltaX > 0) {
      goPrevious();
    } else {
      goNext();
    }
  }

  overlay.addEventListener("click", (event) => {
    if (event.target.closest("[data-story-close]")) {
      close();
    }
  });

  previous.addEventListener("click", goPrevious);
  next.addEventListener("click", goNext);

  video.addEventListener("loadedmetadata", hideLoading);
  video.addEventListener("canplay", hideLoading);
  video.addEventListener("error", showError);

  overlay.addEventListener("keydown", handleKeydown);
  overlay.addEventListener("touchstart", handleTouchStart, {
    passive: true,
  });
  overlay.addEventListener("touchend", handleTouchEnd, {
    passive: true,
  });

  return {
    element: overlay,
    open,
    close,
  };
}
