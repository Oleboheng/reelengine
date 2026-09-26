import { api } from "../api.js";
import { clearAuth, setAuth } from "../state.js";
import { navigate, getRoutes } from "../router.js";
import { createAppHeader } from "../components/app-header.js";
import { createFormMessage } from "../components/form-message.js";
import { createConverterWorkspace } from "../components/converter/converter-workspace.js";
import { createAccountCard } from "../components/account/account-card.js";
import {
  createHistoryCard,
  loadHistory,
  refreshHistory,
} from "../components/reels/reel-library.js";

export async function renderDashboard(me) {
  setAuth(me);

  const root = document.createElement("main");
  root.className = "dashboard-page";

  const shell = document.createElement("div");
  shell.className = "dashboard-shell";

  const header = createAppHeader({
    user: me.user,
    usage: me.usage,
    onLogout: async () => {
      await api("/api/auth/logout", { method: "POST" });
      clearAuth();
      navigate(getRoutes().signIn, { replace: true });
    },
  });

  const welcome = document.createElement("section");
  welcome.className = "dashboard-welcome";

  const firstName = escapeHtml(me.user.first_name || "there");

  welcome.innerHTML = `
    <div class="dashboard-welcome__copy">
      <span class="dashboard-eyebrow">ReelEngine workspace</span>
      <h1>Ready when you are,<br><span>${firstName}.</span></h1>
      <p>Turn an Instagram Reel link into a private video file in a few seconds.</p>
    </div>
  `;

  const converter = createConverterWorkspace(me);
  const historyCard = createHistoryCard();
  const accountCard = document.createElement("div");

  let providers = {
    email: true,
    google: false,
    facebook: false,
  };

  try {
    providers = await api("/api/auth/providers");
  } catch {
    // Provider capability discovery is optional to the main workspace.
  }

  accountCard.append(createAccountCard(me, providers));

  shell.append(
    header,
    welcome,
    converter.card,
    historyCard.card,
    accountCard
  );

  root.append(shell);

  handleOAuthMessage();

  converter.form.addEventListener("submit", async (event) => {
    event.preventDefault();

    converter.message.clear();
    converter.button.disabled = true;
    converter.button.classList.add("is-loading");
    converter.button.innerHTML = `
      <span class="button-spinner" aria-hidden="true"></span>
      <span>Preparing…</span>
    `;

    try {
      const data = await api("/api/download", {
        method: "POST",
        body: { url: converter.input.value.trim() },
      });

      converter.input.value = "";
      converter.message.show(
        "Conversion started. We're preparing your file.",
        "success"
      );

      await pollDownload(
        data.download_id,
        historyCard.history,
        converter.message,
        converter
      );
    } catch (error) {
      converter.message.show(error.message, "error");
    } finally {
      converter.button.disabled = false;
      converter.button.classList.remove("is-loading");
      converter.button.innerHTML = `
        <span>Convert reel</span>
        <span class="converter-button-arrow" aria-hidden="true">→</span>
      `;
      converter.input.focus();
    }
  });

  historyCard.refresh.addEventListener("click", async () => {
    await refreshHistory(historyCard);
  });

  await refreshHistory(historyCard);

  return root;
}

function handleOAuthMessage() {
  const params = new URLSearchParams(window.location.search);
  const success = params.get("oauth_success");
  const error = params.get("oauth_error");

  if (!success && !error) {
    return;
  }

  const message = createFormMessage();
  message.show(success || error, success ? "success" : "error");

  const hero = document.querySelector(".dashboard-welcome");

  if (hero) {
    hero.insertAdjacentElement("afterend", message.element);
  }

  window.history.replaceState(
    {},
    document.title,
    window.location.pathname
  );
}

async function pollDownload(id, history, message, converter) {
  for (let i = 0; i < 180; i++) {
    try {
      const item = await api(`/api/download/${encodeURIComponent(id)}`);

      if (item.status === "completed") {
        message.show("Conversion complete. Your file is ready.", "success");
        await refreshWorkspace(history, converter);
        return;
      }

      if (item.status === "failed") {
        message.show(item.error_message || "Conversion failed.", "error");
        await refreshWorkspace(history, converter);
        return;
      }
    } catch (error) {
      message.show(error.message, "error");
      return;
    }

    await new Promise((resolve) => setTimeout(resolve, 2000));
  }

  message.show(
    "The conversion is still processing. Refresh shortly.",
    "info"
  );

  await refreshWorkspace(history, converter);
}

async function refreshWorkspace(history, converter) {
  const me = await api("/api/auth/me");
  setAuth(me);
  converter.updateUsage(me.usage);
  await loadHistory(history);
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
