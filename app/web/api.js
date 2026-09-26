export async function api(url, options = {}) {
  const headers = new Headers(options.headers || {});

  if (options.body && typeof options.body !== "string") {
    headers.set("Content-Type", "application/json");
    options = {
      ...options,
      body: JSON.stringify(options.body),
    };
  }

  const response = await fetch(url, {
    ...options,
    headers,
    credentials: "same-origin",
  });

  let data = {};
  try {
    data = await response.json();
  } catch (_) {
    // Some responses intentionally contain no JSON body.
  }

  if (!response.ok) {
    const error = new Error(data.detail || "Something went wrong.");
    error.status = response.status;
    throw error;
  }

  return data;
}

export async function getCurrentUser() {
  const data = await api("/api/auth/me");
  return data.authenticated ? data : null;
}

export async function getAuthProviders() {
  return api("/api/auth/providers");
}
