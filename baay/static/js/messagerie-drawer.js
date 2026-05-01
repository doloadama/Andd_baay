(function () {
    "use strict";

    var drawer = document.getElementById("messagerieDrawer");
    if (!drawer) return;

    var body = document.getElementById("messagerieDrawerBody");
    var titleEl = document.getElementById("msgDrawerTitle");
    var backBtn = drawer.querySelector(".msg-drawer-back");
    var panel = drawer.querySelector(".msg-drawer-panel");

    var cfg = window.messagerieDrawerConfig || {};
    var DESKTOP_BP = "(min-width: 992px)";

    // Navigation history within the drawer (push 'inbox' or {type:'conversation', id}).
    var stack = [];
    var lastTriggerEl = null;

    function isDesktop() {
        return window.matchMedia(DESKTOP_BP).matches;
    }

    function isOpen() {
        return drawer.classList.contains("open");
    }

    function setLoading() {
        if (!body) return;
        body.innerHTML =
            '<div class="msg-drawer-loading text-center py-5 text-muted">' +
            '<i class="fas fa-circle-notch fa-spin fs-3"></i>' +
            '<p class="small mt-2 mb-0">Chargement…</p></div>';
    }

    function executeInjectedScripts(container) {
        // innerHTML does not execute <script> tags. Re-create them so the
        // partial's inline init code (window.chatConfig, initMessagerieX) runs.
        var scripts = container.querySelectorAll("script");
        scripts.forEach(function (oldScript) {
            var newScript = document.createElement("script");
            for (var i = 0; i < oldScript.attributes.length; i++) {
                var attr = oldScript.attributes[i];
                newScript.setAttribute(attr.name, attr.value);
            }
            newScript.text = oldScript.text;
            oldScript.parentNode.replaceChild(newScript, oldScript);
        });
    }

    async function loadFragment(url) {
        // Tear down any active conversation WS before swapping the DOM, so we
        // don't leak background sockets when navigating drawer views.
        if (window.__messagerieConvInstance && typeof window.__messagerieConvInstance.dispose === "function") {
            try { window.__messagerieConvInstance.dispose(); } catch (_) { /* noop */ }
            window.__messagerieConvInstance = null;
        }
        setLoading();
        try {
            var resp = await fetch(url, {
                headers: { "Accept": "text/html", "X-Requested-With": "XMLHttpRequest" },
                credentials: "same-origin",
            });
            if (!resp.ok) throw new Error("HTTP " + resp.status);
            var html = await resp.text();
            if (!body) return;
            body.innerHTML = html;
            executeInjectedScripts(body);
        } catch (err) {
            if (body) {
                body.innerHTML =
                    '<div class="text-center py-5 text-danger">' +
                    '<i class="fas fa-triangle-exclamation fs-3"></i>' +
                    '<p class="small mt-2 mb-0">Impossible de charger le contenu.</p>' +
                    '</div>';
            }
        }
    }

    function updateBackButton() {
        if (!backBtn) return;
        if (stack.length > 1) {
            backBtn.hidden = false;
        } else {
            backBtn.hidden = true;
        }
    }

    function setTitle(text) {
        if (titleEl) titleEl.textContent = text || "Messages";
    }

    function pushView(view) {
        stack.push(view);
        renderTop();
    }

    function popView() {
        if (stack.length <= 1) {
            close();
            return;
        }
        stack.pop();
        renderTop();
    }

    function renderTop() {
        var top = stack[stack.length - 1];
        if (!top) return;
        if (top === "inbox") {
            setTitle("Messages");
            loadFragment(cfg.inboxUrl);
        } else if (top && top.type === "conversation") {
            setTitle(top.title || "Conversation");
            var url = (cfg.conversationUrlTemplate || "").replace(
                "00000000-0000-0000-0000-000000000000",
                top.id
            );
            loadFragment(url);
        }
        updateBackButton();
    }

    function open(view) {
        if (!isDesktop()) return;
        stack = [];
        if (!view || view === "inbox") {
            stack.push("inbox");
        } else {
            stack.push(view);
        }
        drawer.classList.add("open");
        drawer.setAttribute("aria-hidden", "false");
        document.body.classList.add("msg-drawer-open");
        renderTop();
        // Focus management
        setTimeout(function () {
            if (panel) panel.focus();
        }, 80);
    }

    function close() {
        if (!isOpen()) return;
        drawer.classList.remove("open");
        drawer.setAttribute("aria-hidden", "true");
        document.body.classList.remove("msg-drawer-open");
        if (lastTriggerEl && typeof lastTriggerEl.focus === "function") {
            try { lastTriggerEl.focus(); } catch (_) { /* noop */ }
        }
    }

    function openInbox() {
        open("inbox");
    }

    function openConversation(id, title) {
        open({ type: "conversation", id: String(id), title: title || "Conversation" });
    }

    function pushConversation(id, title) {
        if (!isOpen()) {
            openConversation(id, title);
            return;
        }
        pushView({ type: "conversation", id: String(id), title: title || "Conversation" });
    }

    // Click delegation on triggers
    document.addEventListener("click", function (e) {
        // Internal: back / close buttons and conversation pick from list
        var backTarget = e.target.closest("[data-drawer-back]");
        if (backTarget && drawer.contains(backTarget)) {
            e.preventDefault();
            popView();
            return;
        }
        var closeTarget = e.target.closest("[data-drawer-close]");
        if (closeTarget && drawer.contains(closeTarget)) {
            e.preventDefault();
            close();
            return;
        }
        var convPick = e.target.closest("[data-drawer-conversation-id]");
        if (convPick && drawer.contains(convPick)) {
            // From inbox list inside the drawer -> push conversation view
            if (isDesktop()) {
                e.preventDefault();
                var id = convPick.getAttribute("data-drawer-conversation-id");
                var title = (convPick.querySelector(".conv-title")?.textContent || "Conversation").trim();
                lastTriggerEl = convPick;
                pushConversation(id, title);
            }
            return;
        }
        // External: trigger toggles from base.html
        var toggle = e.target.closest("[data-drawer-toggle='messagerie']");
        if (toggle) {
            if (!isDesktop()) return; // mobile uses normal navigation
            e.preventDefault();
            lastTriggerEl = toggle;
            openInbox();
            return;
        }
        var convDeep = e.target.closest("[data-drawer-deep-conversation-id]");
        if (convDeep) {
            if (!isDesktop()) return;
            e.preventDefault();
            var deepId = convDeep.getAttribute("data-drawer-deep-conversation-id");
            var deepTitle = convDeep.getAttribute("data-drawer-deep-conversation-title") || "Conversation";
            lastTriggerEl = convDeep;
            openConversation(deepId, deepTitle);
            return;
        }
    });

    // Escape closes
    document.addEventListener("keydown", function (e) {
        if (e.key === "Escape" && isOpen()) {
            close();
        }
    });

    // 'g' then 'm' shortcut toggles drawer (skip if focus is in input/textarea/contentEditable)
    var lastG = 0;
    document.addEventListener("keydown", function (e) {
        if (!isDesktop()) return;
        var t = e.target;
        var tag = t && t.tagName;
        if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
        if (t && t.isContentEditable) return;
        if (e.metaKey || e.ctrlKey || e.altKey) return;
        if (e.key === "g") {
            lastG = Date.now();
        } else if (e.key === "m" && Date.now() - lastG < 1000) {
            e.preventDefault();
            if (isOpen()) close(); else openInbox();
            lastG = 0;
        }
    });

    // Resize guard: if user shrinks the window below desktop while drawer is open, close it.
    var mql = window.matchMedia(DESKTOP_BP);
    var handleMqlChange = function (ev) {
        if (!ev.matches && isOpen()) {
            close();
        }
    };
    if (typeof mql.addEventListener === "function") {
        mql.addEventListener("change", handleMqlChange);
    } else if (typeof mql.addListener === "function") {
        mql.addListener(handleMqlChange);
    }

    // Public API for other scripts (e.g. notif dropdown).
    window.MessagerieDrawer = {
        open: openInbox,
        openConversation: openConversation,
        close: close,
        isOpen: isOpen,
        isDesktop: isDesktop,
    };
})();
