import { api, getAuthProviders } from "../api.js";
import { navigate, getRoutes } from "../router.js";
import { setProviders } from "../state.js";
import { createAuthShell, createDivider, createAuthFooter } from "../components/auth-shell.js";
import { createFormMessage } from "../components/form-message.js";
import { createPasswordField } from "../components/password-field.js";
import { createSocialLogin } from "../components/social-login.js";

export async function renderCreateAccount() {
  const providers = await getAuthProviders();
  setProviders(providers);

  const content = document.createElement("div");
  content.className = "auth-content";

  const social = createSocialLogin(providers);

  const divider = createDivider();

  const form = document.createElement("form");
  form.className = "auth-form";

  const firstNameField = createNameField(
    "create-first-name",
    "First name",
    "Oleboheng"
  );

  const lastNameField = createNameField(
    "create-last-name",
    "Last name",
    "Tladie"
  );

  const emailField = createEmailField();

  const passwordField = createPasswordField({
    id: "create-password",
    label: "Password",
    autocomplete: "new-password",
    hint: "Use at least 10 characters.",
  });

  const confirmField = createPasswordField({
    id: "create-password-confirm",
    label: "Confirm password",
    autocomplete: "new-password",
  });

  const submit = document.createElement("button");
  submit.type = "submit";
  submit.className = "button button-primary";
  submit.textContent = "Create account";

  const message = createFormMessage();

  form.append(
    firstNameField.wrapper,
    lastNameField.wrapper,
    emailField.wrapper,
    passwordField.wrapper,
    confirmField.wrapper,
    submit,
    message.element
  );

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    message.clear();

    if (passwordField.input.value !== confirmField.input.value) {
      message.show("Your passwords do not match.", "error");
      confirmField.input.focus();
      return;
    }

    setLoading(submit, true, "Creating account…");

    try {
      await api("/api/auth/register", {
        method: "POST",
        body: {
          first_name: firstNameField.input.value.trim(),
          last_name: lastNameField.input.value.trim(),
          email: emailField.input.value.trim(),
          password: passwordField.input.value,
        },
      });

      navigate(
        `${getRoutes().signIn}?created=1`,
        { replace: true }
      );
    } catch (error) {
      if (error.status === 429) {
        message.show("Too many attempts. Please wait a moment and try again.", "error");
      } else {
        message.show(error.message, "error");
      }
    } finally {
      setLoading(submit, false, "Create account");
    }
  });

  content.append(social, divider, form);

  const footer = createAuthFooter(
    "Already have an account?",
    "Sign in",
    getRoutes().signIn
  );

  return createAuthShell({
    title: "Create your account",
    description: "Set up your private ReelEngine workspace in a few seconds.",
    content,
    footer,
  });
}

function createNameField(id, labelText, placeholder) {
  const wrapper = document.createElement("div");
  wrapper.className = "field";

  const label = document.createElement("label");
  label.htmlFor = id;
  label.textContent = labelText;

  const input = document.createElement("input");
  input.id = id;
  input.name = id;
  input.type = "text";
  input.placeholder = placeholder;
  input.autocomplete = id === "create-first-name" ? "given-name" : "family-name";
  input.required = true;
  input.maxLength = 80;

  wrapper.append(label, input);
  return { wrapper, input };
}

function createEmailField() {
  const wrapper = document.createElement("div");
  wrapper.className = "field";

  const label = document.createElement("label");
  label.htmlFor = "create-email";
  label.textContent = "Email address";

  const input = document.createElement("input");
  input.id = "create-email";
  input.name = "email";
  input.type = "email";
  input.placeholder = "you@example.com";
  input.autocomplete = "email";
  input.required = true;
  input.maxLength = 254;

  wrapper.append(label, input);
  return { wrapper, input };
}

function setLoading(button, loading, text) {
  button.disabled = loading;
  button.textContent = text;
}
