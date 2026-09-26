import { getRoutes } from "../router.js";

export function createOAuthErrorModal({
  message,
  providers = {},
}) {
  const backdrop = document.createElement("div");
  backdrop.className = "oauth-error-modal";

  const dialog = document.createElement("section");
  dialog.className = "oauth-error-modal__dialog";
  dialog.setAttribute("role", "dialog");
  dialog.setAttribute("aria-modal", "true");
  dialog.setAttribute("aria-labelledby", "oauth-error-title");

  const close = document.createElement("button");
  close.type = "button";
  close.className = "oauth-error-modal__close";
  close.setAttribute("aria-label", "Close");
  close.textContent = "×";

  const title = document.createElement("h2");
  title.id = "oauth-error-title";
  title.textContent = "Sign-in couldn't be completed";

  const description = document.createElement("p");
  description.className = "oauth-error-modal__message";
  description.textContent =
    message ||
    "The selected sign-in method could not be completed. Please choose another way to continue.";

  const actions = document.createElement("div");
  actions.className = "oauth-error-modal__actions";

  if (providers.google) {
    actions.append(
      createAction(
        "Continue with Google",
        "button button-primary",
        () => {
          cleanup();
          window.location.assign("/api/auth/google/start");
        }
      )
    );
  }

  const emailButton = createAction(
    "Sign in with email",
    "button button-secondary",
    () => {
      closeModal();
      window.requestAnimationFrame(() => {
        document.querySelector("#sign-in-email")?.focus();
      });
    }
  );

  const accountButton = createAction(
    "Create an account",
    "button button-ghost",
    () => {
      cleanup();
      window.location.assign(getRoutes().createAccount);
    }
  );

  actions.append(emailButton, accountButton);
  dialog.append(close, title, description, actions);
  backdrop.append(dialog);

  function cleanup() {
    document.removeEventListener("keydown", handleEscape);
    backdrop.remove();
  }

  function closeModal() {
    cleanup();
  }

  close.addEventListener("click", closeModal);

  backdrop.addEventListener("click", (event) => {
    if (event.target === backdrop) {
      closeModal();
    }
  });

  document.addEventListener("keydown", handleEscape);

  function handleEscape(event) {
    if (event.key === "Escape") {
      closeModal();
    }
  }

  return {
    element: backdrop,
    show() {
      document.body.append(backdrop);
      close.focus();
    },
  };
}

function createAction(label, className, onClick) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = className;
  button.textContent = label;
  button.addEventListener("click", onClick);
  return button;
}
