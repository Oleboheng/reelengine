function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

export function createAccountCard(me, providers) {
  const card = document.createElement("section");
  card.className = "workspace-card account-workspace";

  const name = [me.user.first_name, me.user.last_name]
    .filter(Boolean)
    .join(" ");

  const identityProviders = new Set(
    (me.identities || []).map((identity) => identity.provider)
  );

  card.innerHTML = `
    <div class="account-summary">
      <div class="account-avatar" aria-hidden="true">
        ${escapeHtml(
          (me.user.first_name || me.user.email || "R")
            .slice(0, 1)
            .toUpperCase()
        )}
      </div>
      <div class="account-summary__copy">
        <span class="workspace-kicker">Account</span>
        <strong>${escapeHtml(name || "ReelEngine user")}</strong>
        <span>${escapeHtml(me.user.email)}</span>
      </div>
    </div>
    <div class="account-signins">
      <div class="account-signins__heading">
        <strong>Connected sign-ins</strong>
        <span>Use these methods to access your account.</span>
      </div>
      <div class="account-provider-list"></div>
      <p class="account-note">
        Connecting another sign-in method does not create a second ReelEngine account.
      </p>
    </div>
  `;

  const providerList = card.querySelector(".account-provider-list");

  providerList.append(
    createProviderRow(
      "Email & password",
      me.user.has_password
        ? "Password sign-in enabled"
        : "No password sign-in",
      me.user.has_password,
      false,
      true
    ),
    createProviderRow(
      "Google",
      identityProviders.has("google")
        ? "Connected"
        : providers.google
          ? "Available to connect"
          : "Not available",
      identityProviders.has("google"),
      false,
      providers.google
    ),
    createProviderRow(
      "Facebook",
      identityProviders.has("facebook")
        ? "Connected"
        : providers.facebook
          ? "Available to connect"
          : "Not available",
      identityProviders.has("facebook"),
      providers.facebook,
      providers.facebook
    )
  );

  return card;
}

function createProviderRow(
  label,
  description,
  connected,
  actionable,
  available
) {
  const row = document.createElement("div");
  row.className = "account-provider-row";

  const copy = document.createElement("div");
  copy.className = "account-provider-copy";
  copy.innerHTML = `
    <strong>${escapeHtml(label)}</strong>
    <span>${escapeHtml(description)}</span>
  `;

  row.append(copy);

  if (connected) {
    const badge = document.createElement("span");
    badge.className = "account-provider-badge";
    badge.textContent = "Connected";
    row.append(badge);
  } else if (actionable && available && label === "Facebook") {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "button button-secondary button-small";
    button.textContent = "Connect";
    button.addEventListener("click", () => {
      window.location.assign("/api/auth/facebook/link/start");
    });
    row.append(button);
  } else if (!available) {
    const badge = document.createElement("span");
    badge.className = "account-provider-badge account-provider-badge-muted";
    badge.textContent = "Unavailable";
    row.append(badge);
  }

  return row;
}
