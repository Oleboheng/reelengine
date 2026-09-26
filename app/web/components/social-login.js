export function createSocialLogin(providers) {
  const section = document.createElement("div");
  section.className = "social-login";

  section.append(
    createButton(
      "Google",
      "Continue with Google",
      providers.google,
      "/api/auth/google/start"
    ),
    createButton(
      "Facebook",
      "Continue with Facebook",
      providers.facebook,
      "/api/auth/facebook/start"
    )
  );

  return section;
}

function createButton(provider, label, enabled, href) {
  const button = document.createElement("button");

  button.type = "button";
  button.className = "social-button";
  button.disabled = !enabled;

  button.innerHTML = `
    <span class="social-icon">${provider === "Google" ? "G" : "f"}</span>
    <span>${label}</span>
    ${enabled ? "" : '<span class="coming-soon">Soon</span>'}
  `;

  if (enabled) {
    button.addEventListener("click", () => {
      window.location.assign(href);
    });
  }

  return button;
}
