/* Copilote vocal contextuel « Andd Baay » — capture locale (Web Speech API),
   conscience de l'écran, et pont de commande HTMX (HX-Redirect / HX-Trigger).
   FR. Zéro coût STT (transcription navigateur). Dégrade proprement si non supporté. */
(function () {
  "use strict";

  var SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  var btn = document.getElementById("ab-vui-mic");
  var preview = document.getElementById("ab-vui-transcript");
  if (!btn) { return; }

  // CSRF : injecte le token (cookie) dans les requêtes htmx (aucune config globale existante).
  document.body.addEventListener("htmx:configRequest", function (e) {
    if (e.detail.headers["X-CSRFToken"]) { return; }
    var m = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
    if (m) { e.detail.headers["X-CSRFToken"] = decodeURIComponent(m[1]); }
  });

  var synth = window.speechSynthesis;
  function speak(text) {
    if (!synth || !text) { return; }
    var u = new SpeechSynthesisUtterance(text);
    u.lang = "fr-FR";
    try { synth.cancel(); synth.speak(u); } catch (_) {}
  }
  function setState(s) { btn.setAttribute("data-state", s); }
  function setPreview(t) { if (preview) { preview.textContent = t; } }

  // Web Speech API absente (Firefox/iOS ancien) : on désactive proprement.
  if (!SR) {
    setState("unsupported");
    btn.title = "Commande vocale non supportée par ce navigateur";
    return;
  }

  // ── Conscience de l'écran : snapshot du DOM courant ───────────────────────
  function captureScreenContext() {
    var fields = [];
    document
      .querySelectorAll("form input:not([type=hidden]), form select, form textarea")
      .forEach(function (el) {
        if (el.offsetParent === null) { return; } // ignore invisibles
        var label = (el.labels && el.labels[0] && el.labels[0].innerText) || el.name || el.id || "";
        fields.push({
          id: el.id,
          name: el.name,
          type: (el.type || el.tagName).toLowerCase(),
          label: label.trim().slice(0, 60),
          filled: !!(el.value && String(el.value).trim()),
        });
      });
    return {
      url: window.location.pathname,
      title: document.title,
      focused_id: (document.activeElement && document.activeElement.id) || null,
      fields: fields,
    };
  }

  // ── Envoi via htmx (pour que HX-Redirect / HX-Trigger soient traités) ─────
  function sendCommand(transcript) {
    setState("loading");
    window.htmx.ajax("POST", "/vocal/command/", {
      swap: "none",
      values: { transcript: transcript, context: JSON.stringify(captureScreenContext()) },
    }).then(function () { setState("idle"); })
      .catch(function () { setState("error"); });
  }

  // ── Reconnaissance vocale ─────────────────────────────────────────────────
  var recog = new SR();
  recog.lang = "fr-FR";
  recog.continuous = false;
  recog.interimResults = false;
  recog.maxAlternatives = 1;
  var listening = false;

  recog.onresult = function (e) {
    var t = (e.results[0][0].transcript || "").trim();
    setPreview(t);
    if (t) { sendCommand(t); }
  };
  recog.onerror = function (e) { setState("error"); console.warn("[VUI]", e.error); };
  recog.onend = function () { listening = false; if (btn.getAttribute("data-state") === "listening") { setState("idle"); } };

  btn.addEventListener("click", function () {
    if (listening) { try { recog.stop(); } catch (_) {} listening = false; return; }
    try { recog.start(); listening = true; setState("listening"); setPreview("…"); }
    catch (_) { /* déjà démarré */ }
  });

  // ── Pont HTMX → actions UI ────────────────────────────────────────────────
  function nextEmptyField(currentId) {
    var all = Array.prototype.slice.call(
      document.querySelectorAll("form input:not([type=hidden]), form select, form textarea")
    ).filter(function (el) { return el.offsetParent !== null; });
    var idx = all.findIndex(function (el) { return el.id === currentId; });
    for (var i = idx + 1; i < all.length; i++) {
      if (!(all[i].value && String(all[i].value).trim())) { return all[i]; }
    }
    return null;
  }

  document.body.addEventListener("vuiFillField", function (e) {
    var d = e.detail || {};
    var el = document.getElementById(d.field_id);
    if (!el) { speak("Champ introuvable."); return; }
    el.value = d.value || "";
    // Notifier Django/Alpine/validation que la valeur a changé.
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
    el.classList.add("ab-vui-filled");
    var next = nextEmptyField(d.field_id);
    if (next) { next.focus(); }
    if (d.say) { speak(d.say); }
  });

  document.body.addEventListener("vuiSpeak", function (e) {
    speak((e.detail && e.detail.say) || "");
  });

  document.body.addEventListener("vuiSubmit", function (e) {
    if (e.detail && e.detail.say) { speak(e.detail.say); }
    var form = document.querySelector("form");
    if (form && form.requestSubmit) { form.requestSubmit(); }
  });

  window.ABVUI = { speak: speak, captureScreenContext: captureScreenContext };
})();
