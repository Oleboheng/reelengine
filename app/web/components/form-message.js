export function createFormMessage() {
  const element = document.createElement("div");
  element.className = "form-message";
  element.setAttribute("role", "status");
  element.setAttribute("aria-live", "polite");

  return {
    element,

    show(text, type = "info") {
      element.textContent = text || "";
      element.dataset.type = type;
      element.classList.toggle("is-visible", Boolean(text));
    },

    clear() {
      element.textContent = "";
      element.dataset.type = "";
      element.classList.remove("is-visible");
    },
  };
}
