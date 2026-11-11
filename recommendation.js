(() => {
  const RECIPIENT = "alex@myrus.com";
  const ENDPOINT = "https://formsubmit.co/ajax/" + RECIPIENT;
  const MAX_LENGTH = 1500;
  const MIN_LENGTH = 12;

  const escapeHtml = (value) => String(value).replace(/[&<>"']/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  })[character]);

  function addRecommendationBox() {
    const main = document.querySelector("main") || document.body;
    if (!main || document.getElementById("recommend-a-feature")) return;

    const section = document.createElement("section");
    section.className = "panel recommendation-panel";
    section.id = "recommend-a-feature";
    section.setAttribute("aria-labelledby", "recommendation-title");
    section.innerHTML = `
      <div class="panel-head recommendation-heading">
        <div>
          <div class="eyebrow">Help shape the tracker</div>
          <h2 id="recommendation-title">Recommend a Feature</h2>
        </div>
        <span class="tag">SEND A RECOMMENDATION</span>
      </div>
      <p class="recommendation-copy">Have an idea for a new stat, page, or improvement? Send it directly to Alex.</p>
      <div class="notice recommendation-privacy"><strong>Privacy:</strong> Please don’t include private or sensitive information. Your recommendation is sent through FormSubmit to ${RECIPIENT}.</div>
      <form class="recommendation-form" id="recommendation-form" action="https://formsubmit.co/${RECIPIENT}" method="POST">
        <label for="recommendation-message">Your feature recommendation</label>
        <textarea id="recommendation-message" name="message" minlength="${MIN_LENGTH}" maxlength="${MAX_LENGTH}" rows="5" required placeholder="What would you like to see in the NHL tracker?"></textarea>
        <div class="recommendation-meta"><span>At least ${MIN_LENGTH} characters. Maximum ${MAX_LENGTH}.</span><span id="recommendation-count" aria-live="polite">0 / ${MAX_LENGTH}</span></div>
        <label class="recommendation-trap" aria-hidden="true" tabindex="-1">Leave this field empty<input name="_honey" type="text" tabindex="-1" autocomplete="off"></label>
        <input type="hidden" name="_subject" value="NHL Tracker feature recommendation">
        <input type="hidden" name="_template" value="table">
        <input type="hidden" name="_url" value="">
        <div class="recommendation-actions">
          <button class="primary" type="submit" id="recommendation-send">Send recommendation</button>
          <span class="recommendation-activation">FormSubmit may ask Alex to confirm the address the first time this form is used. Email delivery starts after that one-time activation.</span>
        </div>
        <p class="recommendation-status" id="recommendation-status" role="status" aria-live="polite"></p>
      </form>`;

    const footer = main.querySelector(".foot, footer");
    if (footer) footer.before(section);
    else main.append(section);

    const form = section.querySelector("#recommendation-form");
    const textarea = section.querySelector("#recommendation-message");
    const count = section.querySelector("#recommendation-count");
    const button = section.querySelector("#recommendation-send");
    const status = section.querySelector("#recommendation-status");
    const urlField = form.elements.namedItem("_url");
    urlField.value = window.location.href.split("#")[0];

    textarea.addEventListener("input", () => {
      count.textContent = textarea.value.length + " / " + MAX_LENGTH;
      status.textContent = "";
      status.dataset.state = "";
    });

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const message = textarea.value.trim();
      textarea.value = message;
      count.textContent = message.length + " / " + MAX_LENGTH;
      status.textContent = "";
      status.dataset.state = "";

      if (message.length < MIN_LENGTH) {
        status.textContent = "Please enter at least " + MIN_LENGTH + " characters.";
        status.dataset.state = "error";
        textarea.focus();
        return;
      }
      if (message.length > MAX_LENGTH) {
        status.textContent = "Please keep your recommendation under " + MAX_LENGTH + " characters.";
        status.dataset.state = "error";
        textarea.focus();
        return;
      }
      if (!form.reportValidity()) return;

      button.disabled = true;
      button.textContent = "Sending…";
      status.textContent = "Sending your recommendation securely to the form service…";
      try {
        const payload = Object.fromEntries(new FormData(form).entries());
        payload.message = message;
        const response = await fetch(ENDPOINT, {
          method: "POST",
          headers: { "Content-Type": "application/json", "Accept": "application/json" },
          body: JSON.stringify(payload)
        });
        const bodyText = await response.text();
        let result = {};
        try { result = JSON.parse(bodyText); } catch (_) {}
        if (!response.ok || result.success === false) {
          throw new Error(result.message || "The form service could not accept this recommendation.");
        }
        form.reset();
        count.textContent = "0 / " + MAX_LENGTH;
        urlField.value = window.location.href.split("#")[0];
        status.textContent = "Recommendation accepted by FormSubmit. If this is the first use, Alex must confirm the activation email before regular email delivery begins.";
        status.dataset.state = "success";
      } catch (error) {
        status.textContent = error && error.message
          ? error.message + " Please try again in a moment."
          : "We couldn’t send your recommendation. Please try again in a moment.";
        status.dataset.state = "error";
      } finally {
        button.disabled = false;
        button.textContent = "Send recommendation";
      }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", addRecommendationBox, { once: true });
  } else {
    addRecommendationBox();
  }
})();