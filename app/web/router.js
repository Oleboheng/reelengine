const routes = {
  signIn: "/auth/sign-in",
  createAccount: "/auth/create-account",
  app: "/app",
  privacy: "/privacy",
  dataDeletion: "/data-deletion",
};

export function normalizePath() {
  const path = window.location.pathname.replace(/\/+$/, "");
  return path || "/";
}

export function navigate(path, { replace = false } = {}) {
  if (normalizePath() === path) {
    window.dispatchEvent(new PopStateEvent("popstate"));
    return;
  }

  if (replace) {
    window.history.replaceState({}, "", path);
  } else {
    window.history.pushState({}, "", path);
  }

  window.dispatchEvent(new PopStateEvent("popstate"));
}

export function getRoutes() {
  return routes;
}

export function isAuthRoute(path) {
  return path === routes.signIn || path === routes.createAccount;
}
