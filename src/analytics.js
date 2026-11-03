/* Consent banner for GA4. The tag itself is injected from the page head,
   and only on the production hostnames. */
(function () {
  var KEY = "igor_consent";

  function hostName() {
    try {
      return String(location.hostname || "").toLowerCase().replace(/^www\./, "");
    } catch (err) {
      return "";
    }
  }

  function tracksAnalytics() {
    var name = hostName();
    return name === "igorpiovezan.com" || name === "igorpiovezan.com.br";
  }

  function readConsent() {
    try {
      var value = localStorage.getItem(KEY);
      if (value === "granted" || value === "denied") return value;
    } catch (err) { /* private mode */ }
    return "";
  }

  function writeConsent(choice) {
    try {
      localStorage.setItem(KEY, choice);
    } catch (err) { /* ignore */ }
  }

  function consentState(choice) {
    var value = choice === "granted" ? "granted" : "denied";
    return {
      ad_storage: value,
      ad_user_data: value,
      ad_personalization: value,
      analytics_storage: value
    };
  }

  function start() {
    if (!tracksAnalytics()) return;
    var bar = document.getElementById("igor-consent");
    if (!bar || readConsent()) return;
    bar.hidden = false;
    bar.setAttribute("role", "dialog");
    bar.setAttribute("aria-labelledby", "igor-consent-title");
    bar.addEventListener("click", function (event) {
      var target = event.target;
      if (!target || !target.closest) return;
      var button = target.closest("button[data-consent]");
      if (!button) return;
      var choice = button.getAttribute("data-consent") === "granted" ? "granted" : "denied";
      writeConsent(choice);
      if (typeof window.gtag === "function") {
        window.gtag("consent", "update", consentState(choice));
      }
      bar.hidden = true;
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})();
