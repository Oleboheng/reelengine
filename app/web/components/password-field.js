export function createPasswordField({
  id,
  label,
  autocomplete,
  hint = "",
}) {
  const wrapper = document.createElement("div");
  wrapper.className = "field";

  const labelElement = document.createElement("label");
  labelElement.htmlFor = id;
  labelElement.textContent = label;

  const control = document.createElement("div");
  control.className = "password-control";

  const input = document.createElement("input");
  input.id = id;
  input.name = id;
  input.type = "password";
  input.autocomplete = autocomplete;
  input.required = true;
  input.minLength = 10;
  input.maxLength = 128;
  input.placeholder = "Enter your password";

  const toggle = document.createElement("button");
  toggle.type = "button";
  toggle.className = "password-toggle";
  toggle.textContent = "Show";
  toggle.setAttribute("aria-label", `Show ${label.toLowerCase()}`);

  toggle.addEventListener("click", () => {
    const visible = input.type === "text";
    input.type = visible ? "password" : "text";
    toggle.textContent = visible ? "Show" : "Hide";
    toggle.setAttribute(
      "aria-label",
      `${visible ? "Show" : "Hide"} ${label.toLowerCase()}`
    );
  });

  control.append(input, toggle);
  wrapper.append(labelElement, control);

  if (hint) {
    const hintElement = document.createElement("div");
    hintElement.className = "field-hint";
    hintElement.textContent = hint;
    wrapper.append(hintElement);
  }

  return {
    wrapper,
    input,
  };
}
