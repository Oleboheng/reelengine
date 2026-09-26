import { createFormMessage } from "../form-message.js";

export function createConverterWorkspace(me) {
  const card = document.createElement("section");
  card.className = "workspace-card converter-workspace";

  const heading = document.createElement("div");
  heading.className = "workspace-heading";
  heading.innerHTML = `
    <div>
      <span class="workspace-kicker">New conversion</span>
      <h2>Convert an Instagram Reel</h2>
      <p>Paste the Reel link below and we'll prepare the video for your account.</p>
    </div>
  `;

  const usage = document.createElement("div");
  usage.className = "usage-summary";
  usage.setAttribute("aria-label", "Daily conversion usage");

  const usageCount = document.createElement("strong");
  usageCount.dataset.usageCount = "";
  usageCount.textContent =
    `${me.usage.accepted_today} / ${me.usage.daily_limit}`;

  const usageLabel = document.createElement("span");
  usageLabel.textContent = "today";

  const usageRing = document.createElement("div");
  usageRing.className = "usage-ring";
  usageRing.append(usageCount, usageLabel);

  const usageTrack = document.createElement("div");
  usageTrack.className = "usage-track";

  const usageFill = document.createElement("span");
  usageFill.dataset.usageFill = "";
  usageTrack.append(usageFill);

  usage.append(usageRing, usageTrack);

  const form = document.createElement("form");
  form.className = "converter-workspace__form";

  const fieldLabel = document.createElement("label");
  fieldLabel.htmlFor = "reel-url";
  fieldLabel.textContent = "Instagram Reel URL";

  const inputWrap = document.createElement("div");
  inputWrap.className = "converter-input-wrap";

  const input = document.createElement("input");
  input.id = "reel-url";
  input.type = "url";
  input.placeholder = "https://www.instagram.com/reel/...";
  input.required = true;
  input.maxLength = 2048;
  input.autocomplete = "url";
  input.spellcheck = false;
  input.setAttribute("aria-describedby", "converter-help");

  const button = document.createElement("button");
  button.type = "submit";
  button.className = "button button-primary converter-button";
  button.innerHTML = `
    <span>Convert reel</span>
    <span class="converter-button-arrow" aria-hidden="true">→</span>
  `;

  inputWrap.append(input, button);

  const message = createFormMessage();

  const help = document.createElement("p");
  help.id = "converter-help";
  help.className = "converter-help";
  help.innerHTML = `
    <span class="help-check" aria-hidden="true">✓</span>
    <span>Your conversions are private and tied to your account.</span>
  `;

  form.append(fieldLabel, inputWrap, message.element, help);

  const top = document.createElement("div");
  top.className = "workspace-top";
  top.append(heading, usage);

  card.append(top, form);

  const updateUsage = (usageData) => {
    const accepted = Number(usageData?.accepted_today || 0);
    const limit = Number(usageData?.daily_limit || 0);
    const count = usageData?.accepted_today !== undefined
      ? `${accepted} / ${limit}`
      : "—";

    usageCount.textContent = count;

    const percent = limit > 0
      ? Math.min(100, Math.round((accepted / limit) * 100))
      : 0;

    usageFill.style.width = `${percent}%`;

    usage.classList.toggle(
      "is-near-limit",
      limit > 0 && accepted >= limit * 0.8
    );
    usage.classList.toggle(
      "is-at-limit",
      limit > 0 && accepted >= limit
    );
  };

  // Initialize the usage indicator immediately on first render.
  if (me?.usage) {
    updateUsage(me.usage);
  }

  return {
    card,
    form,
    input,
    button,
    message,
    updateUsage,
  };
}
