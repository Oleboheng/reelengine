export function createAuthShell({
  eyebrow = "Soflas ReelEngine",
  title,
  description,
  content,
  footer,
}) {
  const shell = document.createElement("main");
  shell.className = "auth-page";

  const container = document.createElement("section");
  container.className = "auth-container";

  const brand = document.createElement("a");
  brand.className = "auth-brand";
  brand.href = "/auth/sign-in";
  brand.innerHTML = `
    <img src="/assets/soflas-logo.png" alt="Soflas" />
    <span>ReelEngine</span>
  `;

  const panel = document.createElement("div");
  panel.className = "auth-panel";

  const heading = document.createElement("div");
  heading.className = "auth-heading";

  const eyebrowElement = document.createElement("div");
  eyebrowElement.className = "auth-eyebrow";
  eyebrowElement.textContent = eyebrow;

  const titleElement = document.createElement("h1");
  titleElement.textContent = title;

  const descriptionElement = document.createElement("p");
  descriptionElement.textContent = description;

  heading.append(eyebrowElement, titleElement, descriptionElement);
  panel.append(heading, content, footer);
  container.append(brand, panel);
  shell.append(container);

  return shell;
}

export function createDivider() {
  const divider = document.createElement("div");
  divider.className = "auth-divider";
  divider.innerHTML = "<span>or continue with email</span>";
  return divider;
}

export function createAuthFooter(text, linkText, href) {
  const footer = document.createElement("p");
  footer.className = "auth-footer";

  const prefix = document.createTextNode(text + " ");
  const link = document.createElement("a");
  link.href = href;
  link.textContent = linkText;

  footer.append(prefix, link);
  return footer;
}
