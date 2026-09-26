export function createAppHeader({ user, usage, onLogout }) {
  const header = document.createElement("header");
  header.className = "app-header";

  const brand = document.createElement("div");
  brand.className = "app-brand";
  brand.innerHTML = `
    <div class="app-logo">
      <img src="/assets/soflas-logo.png" alt="Soflas" />
    </div>
    <div>
      <strong>Soflas Reel Engine</strong>
      <span>Private reel conversion</span>
    </div>
  `;

  const account = document.createElement("div");
  account.className = "app-account";

  const email = document.createElement("span");
  email.className = "app-email";
  email.textContent = user.email;

  const logout = document.createElement("button");
  logout.className = "button button-secondary button-small";
  logout.type = "button";
  logout.textContent = "Log out";
  logout.addEventListener("click", onLogout);

  account.append(email, logout);
  header.append(brand, account);

  return header;
}
