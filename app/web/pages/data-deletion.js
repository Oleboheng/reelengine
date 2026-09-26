export async function renderDataDeletion() {
  const page = document.createElement("main");
  page.className = "public-page";

  page.innerHTML = `
    <article class="public-page__content">
      <header class="public-page__header">
        <p class="public-page__eyebrow">ReelEngine</p>
        <h1>User Data Deletion</h1>
        <p class="public-page__updated">Last updated: 25 September 2026</p>
      </header>

      <section>
        <h2>Delete your account</h2>
        <p>
          If you are signed in, you can permanently delete your ReelEngine
          account and the data associated with it here.
        </p>

        <form id="account-deletion-form">
          <label for="deletion-reason">Why are you deleting your account?</label>
          <select id="deletion-reason" required>
            <option value="">Select a reason</option>
          </select>

          <label for="deletion-detail">Additional feedback (optional)</label>
          <textarea
            id="deletion-detail"
            maxlength="1000"
            rows="5"
            placeholder="Tell us anything that may help us understand your decision."
          ></textarea>

          <button type="submit">Delete my account</button>
          <p id="deletion-status" role="status"></p>
        </form>
      </section>

      <section>
        <h2>What will be deleted?</h2>
        <p>
          Account information, authentication identities, sessions, conversion
          history, usage records, and conversion files stored for your account
          will be deleted.
        </p>
        <p>
          Existing legacy records that are not associated with an individual
          account are not part of this account-deletion process.
        </p>
      </section>

      <section>
        <h2>What happens after you submit?</h2>
        <p>
          New conversions are stopped while the deletion is processed.
          If a conversion is already running, the deletion waits for it to
          finish before removing the account and its files.
        </p>
        <p>
          Once deletion is complete, your account can no longer be used to
          sign in.
        </p>
      </section>

      <section>
        <h2>Questions</h2>
        <p>
          For privacy or deletion questions, contact:
        </p>
        <p class="public-page__contact">
          <a href="mailto:admin@soflasdevelopments.co.za">
            admin@soflasdevelopments.co.za
          </a>
        </p>
      </section>

      <footer class="public-page__footer">
        <a href="/" data-route-link>Return to ReelEngine</a>
        <a href="/privacy" data-route-link>Privacy Policy</a>
      </footer>
    </article>
  `;

  const form = page.querySelector("#account-deletion-form");
  const reasonSelect = page.querySelector("#deletion-reason");
  const detail = page.querySelector("#deletion-detail");
  const status = page.querySelector("#deletion-status");

  try {
    const response = await fetch("/api/account/deletion/reasons", {
      credentials: "same-origin",
    });

    if (!response.ok) {
      throw new Error("Unable to load deletion reasons");
    }

    const data = await response.json();

    for (const reason of data.reasons) {
      const option = document.createElement("option");
      option.value = reason.code;
      option.textContent = reason.label;
      reasonSelect.append(option);
    }
  } catch {
    status.textContent = "Unable to load the deletion form. Please try again.";
    form.querySelector("button").disabled = true;
    return page;
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();

    const confirmed = window.confirm(
      "This permanently deletes your ReelEngine account and associated account data. Continue?"
    );

    if (!confirmed) {
      return;
    }

    const button = form.querySelector("button");
    button.disabled = true;
    status.textContent = "Processing account deletion…";

    try {
      const response = await fetch("/api/account/deletion", {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          reason_code: reasonSelect.value,
          reason_detail: detail.value.trim() || null,
        }),
      });

      const data = await response.json().catch(() => ({}));

      if (response.status === 401) {
        status.textContent =
          "Please sign in to delete your ReelEngine account.";
        button.disabled = false;
        return;
      }

      if (!response.ok) {
        throw new Error(data.detail || "Account deletion could not be started.");
      }

      status.textContent =
        "Your account deletion has started. You will be signed out when the account is removed.";

      setTimeout(() => {
        window.location.href = "/";
      }, 3000);
    } catch (error) {
      status.textContent = error.message;
      button.disabled = false;
    }
  });

  return page;
}
