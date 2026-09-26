import { api, getAuthProviders } from "../api.js";
import { navigate, getRoutes } from "../router.js";
import { setProviders } from "../state.js";
import { createAuthShell, createDivider, createAuthFooter } from "../components/auth-shell.js";
import { createFormMessage } from "../components/form-message.js";
import { createPasswordField } from "../components/password-field.js";
import { createSocialLogin } from "../components/social-login.js";
import { createOAuthErrorModal } from "../components/oauth-error-modal.js";

export async function renderSignIn({ notice = "" } = {}) {
  const providers = await getAuthProviders();

  const oauthError = new URLSearchParams(window.location.search)
    .get("oauth_error");
  setProviders(providers);

  const content = document.createElement("div");
  content.className = "auth-content";

  const social = createSocialLogin(providers);

  const divider = createDivider();

  const form = document.createElement("form");
  form.className = "auth-form";

  const emailField = createField(
    "sign-in-email",
    "Email address",
    "email",
    "Enter your email address"
  );

  const passwordField = createPasswordField({
    id: "sign-in-password",
    label: "Password",
    autocomplete: "current-password",
  });

  const submit = document.createElement("button");
  submit.type = "submit";
  submit.className = "button button-primary";
  submit.textContent = "Sign in";

  const message = createFormMessage();

  if (notice) {
    message.show(notice, "success");
  }

  if (oauthError) {
    const modal = createOAuthErrorModal({
      message: oauthError,
      providers,
    });

    modal.show();

    const cleanUrl = new URL(window.location.href);
    cleanUrl.searchParams.delete("oauth_error");
    window.history.replaceState({}, "", cleanUrl.pathname + cleanUrl.search);
  }

  form.append(
    emailField.wrapper,
    passwordField.wrapper,
    submit,
    message.element
  );

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    message.clear();
    setLoading(submit, true, "Signing in…");

    try {
      await api("/api/auth/login", {
        method: "POST",
        body: {
          email: emailField.input.value.trim(),
          password: passwordField.input.value,
        },
      });

      navigate(getRoutes().app, { replace: true });
    } catch (error) {
      if (error.status === 429) {
        message.show("Too many attempts. Please wait a moment and try again.", "error");
      } else {
        message.show(error.message, "error");
      }
    } finally {
      setLoading(submit, false, "Sign in");
    }
  });

  content.append(social, divider, form);

  const footer = createAuthFooter(
    "Don't have an account?",
    "Create one",
    getRoutes().createAccount
  );

  return createAuthShell({
    title: "Welcome back",
    description: "Sign in to continue to your private ReelEngine workspace.",
    content,
    footer,
  });
}

function createField(id, label, type, placeholder) {
  const wrapper = document.createElement("div");
  wrapper.className = "field";

  const labelElement = document.createElement("label");
  labelElement.htmlFor = id;
  labelElement.textContent = label;

  const input = document.createElement("input");
  input.id = id;
  input.name = id;
  input.type = type;
  input.placeholder = placeholder;
  input.autocomplete = "email";
  input.required = true;
  input.maxLength = 254;

  wrapper.append(labelElement, input);

  return { wrapper, input };
}

function setLoading(button, loading, text) {
  button.disabled = loading;
  button.textContent = text;
}
