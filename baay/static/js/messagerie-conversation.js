(function () {
    "use strict";

    /**
     * Initialise (or re-initialise) the conversation chat UI for the partial
     * currently rendered into the page (or drawer). Closes any previous active
     * instance to avoid duplicate WebSocket connections when navigating
     * between conversations inside the drawer.
     *
     * opts: {
     *   currentProfileId, conversationId, csrfToken, syncUrlTemplate,
     *   container?: HTMLElement   // default: document
     * }
     */
    function initMessagerieConversation(opts) {
        var cfg = opts || window.chatConfig || {};
        var root = cfg.container || document;
        var box = root.getElementById ? root.getElementById("chatBox") : root.querySelector("#chatBox");
        if (!box) return null;

        var currentProfileId = String(cfg.currentProfileId || "");
        var convId = cfg.conversationId;
        var csrfToken = cfg.csrfToken;
        var syncUrl = cfg.syncUrlTemplate;
        if (!convId || !csrfToken || !currentProfileId) return null;

        // Tear down previous instance (if any).
        if (window.__messagerieConvInstance && typeof window.__messagerieConvInstance.dispose === "function") {
            try { window.__messagerieConvInstance.dispose(); } catch (_) { /* noop */ }
        }

        box.scrollTop = box.scrollHeight;

        var wsProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";
        var wsUrl = wsProtocol + "//" + window.location.host + "/ws/messagerie/conversation/" + convId + "/";
        var ws = null;
        var typingTimer = null;
        var isTyping = false;
        var reconnectDelayMs = 1500;
        var TYPING_DEBOUNCE = 2000;
        var disposed = false;

        var messagesById = new Map();
        var orderedIds = [];
        var pendingByClientId = new Map();
        var lastSeenIso = null;

        function recordSeen(message) {
            if (message && message.date_envoi_iso && (!lastSeenIso || message.date_envoi_iso > lastSeenIso)) {
                lastSeenIso = message.date_envoi_iso;
            }
        }

        function sortOrderedIds() {
            orderedIds.sort(function (a, b) {
                var ma = messagesById.get(a);
                var mb = messagesById.get(b);
                var ta = (ma && ma.date_envoi_iso) || "";
                var tb = (mb && mb.date_envoi_iso) || "";
                if (ta !== tb) return ta.localeCompare(tb);
                return String(a).localeCompare(String(b));
            });
        }

        function upsertMessage(message) {
            var messageId = String(message.message_id || message.id || "");
            if (!messageId) return false;
            var exists = messagesById.has(messageId);
            messagesById.set(messageId, message);
            if (!exists) {
                orderedIds.push(messageId);
                sortOrderedIds();
            }
            recordSeen(message);
            return !exists;
        }

        function escapeHtml(text) {
            var d = document.createElement("div");
            d.textContent = text || "";
            return d.innerHTML;
        }

        function renderMessage(message) {
            var isOwn = String(message.sender_id) === currentProfileId;
            var div = document.createElement("div");
            var bubbleClass = isOwn ? "msg-bubble-own" : "msg-bubble-other";
            var senderLine = isOwn
                ? ""
                : '<div class="fw-bold mb-1" style="font-size: 0.78rem; color: var(--accent-dark);">' + escapeHtml(message.sender_name) + '</div>';
            var messageId = String(message.message_id || message.id);
            var checkMark = isOwn
                ? '<i class="fas fa-check-double ms-1 checkmark-icon' + (message.is_lu_par_tous ? " text-success" : "") + '" id="check-' + messageId + '"></i>'
                : "";
            div.className = "d-flex mb-3 " + (isOwn ? "justify-content-end" : "justify-content-start");
            div.setAttribute("data-message-id", messageId);
            div.innerHTML =
                '<div class="d-flex flex-column ' + (isOwn ? "align-items-end" : "align-items-start") + '" style="max-width: 75%;">' +
                '<div class="' + bubbleClass + ' rounded-4">' + senderLine +
                '<div style="white-space: pre-wrap;">' + escapeHtml(message.contenu) + '</div>' +
                '<div class="' + (isOwn ? "text-end" : "") + ' mt-1" style="font-size: 0.68rem; opacity: 0.85;">' + (message.date_envoi || "") + checkMark + '</div></div></div>';
            return div;
        }

        function rerenderMessages() {
            box.querySelectorAll("[data-message-id]").forEach(function (el) { el.remove(); });
            orderedIds.forEach(function (id) { box.appendChild(renderMessage(messagesById.get(id))); });
            box.scrollTop = box.scrollHeight;
        }

        function appendMessage(data) {
            var wasNew = upsertMessage(data);
            if (data.client_message_id && pendingByClientId.has(data.client_message_id)) {
                pendingByClientId.delete(data.client_message_id);
            }
            if (wasNew) rerenderMessages();
        }

        function updateReactionPills(messageId, reactions) {
            var pills = root.querySelectorAll('button[data-reaction-pill="1"][data-message-id="' + messageId + '"]');
            pills.forEach(function (pill) {
                var emoji = pill.getAttribute("data-emoji");
                var count = Number((reactions || {})[emoji] || 0);
                if (count > 0) {
                    pill.textContent = emoji + " " + count;
                    pill.style.display = "";
                } else {
                    pill.style.display = "none";
                }
            });
        }

        function syncMissedMessages() {
            if (!syncUrl) return Promise.resolve();
            var url = syncUrl;
            if (lastSeenIso) {
                url += (url.indexOf("?") !== -1 ? "&" : "?") + "since=" + encodeURIComponent(lastSeenIso);
            }
            return fetch(url, { headers: { Accept: "application/json" } })
                .then(function (response) { return response.ok ? response.json() : null; })
                .then(function (payload) {
                    if (!payload) return;
                    (payload.messages || []).forEach(function (m) { upsertMessage(m); });
                    rerenderMessages();
                });
        }

        function connect() {
            if (disposed) return;
            ws = new WebSocket(wsUrl);
            ws.onopen = function () {
                reconnectDelayMs = 1500;
                syncMissedMessages().catch(function () { /* noop */ });
            };
            ws.onmessage = function (e) {
                var data;
                try { data = JSON.parse(e.data); } catch (_) { return; }
                if (data.type === "chat_message_v1") {
                    appendMessage(data);
                } else if (data.type === "chat_typing_v1" && String(data.sender_id) !== currentProfileId) {
                    showTyping();
                } else if (data.type === "chat_stop_typing_v1") {
                    hideTyping();
                } else if (data.type === "chat_read_receipt_v1") {
                    var checkIcon = root.querySelector("#check-" + data.message_id);
                    if (checkIcon) checkIcon.style.color = "#064e3b";
                } else if (data.type === "reaction_updated_v1") {
                    updateReactionPills(String(data.message_id), data.reactions || {});
                }
            };
            ws.onclose = function () {
                if (disposed) return;
                setTimeout(connect, reconnectDelayMs);
                reconnectDelayMs = Math.min(reconnectDelayMs * 2, 10000);
            };
        }

        var typingIndicator = root.querySelector("#typingIndicator");
        if (!typingIndicator) {
            typingIndicator = document.createElement("div");
            typingIndicator.id = "typingIndicator";
            typingIndicator.className = "typing-indicator";
            typingIndicator.innerHTML = '<div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div>';
            box.appendChild(typingIndicator);
        }
        function showTyping() {
            typingIndicator.classList.add("show");
            box.scrollTop = box.scrollHeight;
        }
        function hideTyping() {
            typingIndicator.classList.remove("show");
        }

        var form = root.querySelector('form#msgForm') || root.querySelector('form[action*="conversation"]');
        var textarea = form ? form.querySelector('textarea[name="contenu"]') : null;
        var submitHandler = null;
        var keydownHandler = null;
        if (form && textarea) {
            submitHandler = function (e) {
                e.preventDefault();
                var contenu = textarea.value.trim();
                if (!contenu) return;
                var clientMessageId = (window.crypto && crypto.randomUUID) ? crypto.randomUUID() : String(Date.now()) + "-" + Math.random();
                pendingByClientId.set(clientMessageId, Date.now());
                var payload = new FormData(form);
                payload.append("client_message_id", clientMessageId);
                fetch(form.action, {
                    method: "POST",
                    headers: {
                        "X-CSRFToken": csrfToken,
                        "X-Requested-With": "XMLHttpRequest",
                        "Accept": "application/json",
                    },
                    body: payload,
                })
                    .then(function (r) { return r.json(); })
                    .then(function (data) {
                        appendMessage(data);
                        textarea.value = "";
                        textarea.style.height = "";
                        if (window.clearReply) window.clearReply();
                        if (window.clearFile) window.clearFile();
                    })
                    .catch(function () {
                        pendingByClientId.delete(clientMessageId);
                    });
            };
            keydownHandler = function () {
                if (!isTyping) {
                    isTyping = true;
                    if (ws && ws.readyState === WebSocket.OPEN) {
                        ws.send(JSON.stringify({ type: "chat_typing_v1" }));
                    }
                }
                clearTimeout(typingTimer);
                typingTimer = setTimeout(function () {
                    isTyping = false;
                    if (ws && ws.readyState === WebSocket.OPEN) {
                        ws.send(JSON.stringify({ type: "chat_stop_typing_v1" }));
                    }
                }, TYPING_DEBOUNCE);
            };
            form.addEventListener("submit", submitHandler);
            textarea.addEventListener("keydown", keydownHandler);
        }

        window.toggleReaction = function (messageId, emoji) {
            var url = "/api/messages/" + messageId + "/reaction/";
            var data = new FormData();
            data.append("emoji", emoji);
            data.append("csrfmiddlewaretoken", csrfToken);
            fetch(url, {
                method: "POST",
                headers: { "X-CSRFToken": csrfToken },
                body: data,
            })
                .then(function (r) { return r.json(); })
                .then(function (d) {
                    if (d.reactions) updateReactionPills(String(messageId), d.reactions);
                });
        };

        connect();

        var instance = {
            conversationId: convId,
            dispose: function () {
                disposed = true;
                if (ws) {
                    try { ws.onclose = null; ws.close(); } catch (_) { /* noop */ }
                    ws = null;
                }
                clearTimeout(typingTimer);
                if (form && submitHandler) form.removeEventListener("submit", submitHandler);
                if (textarea && keydownHandler) textarea.removeEventListener("keydown", keydownHandler);
            },
        };
        window.__messagerieConvInstance = instance;
        return instance;
    }

    window.initMessagerieConversation = initMessagerieConversation;

    // Auto-init when chatConfig is already set (full-page render path).
    if (window.chatConfig && document.getElementById("chatBox")) {
        initMessagerieConversation(window.chatConfig);
    }
})();
