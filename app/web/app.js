import { getCurrentUser } from "./api.js";
import { normalizePath, navigate, getRoutes } from "./router.js";
import { renderSignIn } from "./pages/sign-in.js";
import { renderCreateAccount } from "./pages/create-account.js";
import { renderDashboard } from "./pages/dashboard.js";
import { renderPrivacy } from "./pages/privacy.js";
import { renderDataDeletion } from "./pages/data-deletion.js";

const root = document.getElementById("app");

window.addEventListener("popstate", render);

async function render() {
  root.innerHTML = "";
  root.classList.add("is-loading");

  try {
    const path = normalizePath();

    if (path === getRoutes().privacy) {
      root.append(await renderPrivacy());
      return;
    }

    if (path === getRoutes().dataDeletion) {
      root.append(await renderDataDeletion());
      return;
    }

    const me = await getCurrentUser();

    if (me && (path === getRoutes().signIn || path === getRoutes().createAccount || path === "/")) {
      navigate(getRoutes().app, { replace: true });
      return;
    }

    if (!me && (path === "/" || path === getRoutes().app)) {
      navigate(getRoutes().signIn, { replace: true });
      return;
    }

    if (path === getRoutes().createAccount) {
      root.append(await renderCreateAccount());
      return;
    }

    if (path === getRoutes().app) {
      root.append(await renderDashboard(me));
      return;
    }

    const params = new URLSearchParams(window.location.search);
    const notice = params.get("created") === "1"
      ? "Your account has been created. Sign in to continue."
      : "";

    if (path === getRoutes().signIn || path === "/") {
      root.append(await renderSignIn({ notice }));
      return;
    }

    navigate(me ? getRoutes().app : getRoutes().signIn, { replace: true });
  } catch (error) {
    root.innerHTML = `
      <main class="error-page">
        <div>
          <h1>Something went wrong</h1>
          <p>${escapeHtml(error.message)}</p>
          <button class="button button-primary" id="retry">Try again</button>
        </div>
      </main>
    `;

    document.getElementById("retry").addEventListener("click", render);
  } finally {
    root.classList.remove("is-loading");
  }
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

render();
