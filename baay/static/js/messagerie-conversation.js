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

        // Tear down previous instance (if any) and null the global immediately
        // so that a partial init failure below cannot leave a stale reference.
        if (window.__messagerieConvInstance && typeof window.__messagerieConvInstance.dispose === "function") {
            try { window.__messagerieConvInstance.dispose(); } catch (_) { /* noop */ }
        }
        window.__messagerieConvInstance = null;

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

        function isoToDay(iso) {
            if (!iso) return "";
            return String(iso).slice(0, 10);
        }

        function lectureStatutClass(message) {
            var ls = message.lecture_statut;
            if (!ls && message.is_lu_par_tous) ls = "recu";
            if (ls === "recu") return " read";
            if (ls === "recu_partiel") return " delivered";
            return "";
        }

        function renderMessage(message) {
            var isOwn = String(message.sender_id) === currentProfileId;
            var messageId = String(message.message_id || message.id);
            var senderName = message.sender_name || "";
            var initial = (senderName.charAt(0) || "?").toUpperCase();
            var day = isoToDay(message.date_envoi_iso);
            var div = document.createElement("div");
            div.className = "msg-row " + (isOwn ? "msg-row-own" : "msg-row-other");
            div.setAttribute("data-message-id", messageId);
            div.setAttribute("data-author", isOwn ? "own" : "other");
            if (!isOwn && message.sender_id) div.setAttribute("data-author-id", String(message.sender_id));
            if (day) div.setAttribute("data-day", day);

            var readLabel = message.lecture_statut_label || "";
            var safeLabel = escapeHtml(readLabel).replace(/"/g, "&quot;");
            var titleAttr = readLabel ? ' title="' + safeLabel + '"' : "";
            var ariaAttr = readLabel ? ' aria-label="' + safeLabel + '"' : "";
            var checkMark = isOwn
                ? '<i class="fas fa-check-double checkmark-icon' + lectureStatutClass(message) + '" id="check-' + messageId + '"' + titleAttr + ariaAttr + "></i>"
                : "";
            var senderHeader = isOwn
                ? ""
                : '<div class="msg-sender-name">' + escapeHtml(senderName) + '</div>';
            var avatarCol = isOwn
                ? ""
                : '<div class="msg-avatar-col"><div class="msg-avatar">' + escapeHtml(initial) + '</div></div>';

            div.innerHTML =
                avatarCol +
                '<div class="msg-stack">' +
                    senderHeader +
                    '<div class="msg-bubble ' + (isOwn ? "msg-bubble-own" : "msg-bubble-other") + '">' +
                        '<div class="msg-text">' + escapeHtml(message.contenu) + '</div>' +
                        '<div class="msg-meta ' + (isOwn ? "msg-meta-own" : "msg-meta-other") + '">' +
                            '<span class="msg-time">' + (message.date_envoi || "") + '</span>' +
                            checkMark +
                        '</div>' +
                    '</div>' +
                '</div>';
            return div;
        }

        function hydrateMessagesFromDom() {
            var inner = box.querySelector(".chat-messages-inner") || box;
            inner.querySelectorAll(".msg-row[data-message-id]").forEach(function (el) {
                var id = el.getAttribute("data-message-id");
                if (!id || messagesById.has(id)) return;
                var isOwn = el.getAttribute("data-author") === "own";
                var authorId = el.getAttribute("data-author-id");
                var day = el.getAttribute("data-day") || "";
                var textEl = el.querySelector(".msg-text");
                var timeEl = el.querySelector(".msg-time");
                var contenu = textEl ? textEl.innerText : "";
                var dateEnvoi = timeEl ? timeEl.textContent.trim() : "";
                var chk = el.querySelector(".checkmark-icon");
                var lecture_statut = "envoye";
                if (chk && chk.classList.contains("read")) lecture_statut = "recu";
                else if (chk && chk.classList.contains("delivered")) lecture_statut = "recu_partiel";
                var labelEl = chk && chk.getAttribute("aria-label");
                var lecture_statut_label = labelEl || "";
                var iso = day ? day + "T12:00:00" : "";
                messagesById.set(id, {
                    message_id: id,
                    sender_id: isOwn ? currentProfileId : (authorId || ""),
                    contenu: contenu,
                    date_envoi: dateEnvoi,
                    date_envoi_iso: iso,
                    lecture_statut: lecture_statut,
                    lecture_statut_label: lecture_statut_label,
                    is_lu_par_tous: lecture_statut === "recu",
                });
                orderedIds.push(id);
            });
            sortOrderedIds();
        }

        function rerenderMessages() {
            hydrateMessagesFromDom();
            // Rebuild only the inner container so the date separators stay simple.
            var inner = box.querySelector(".chat-messages-inner") || box;
            inner.querySelectorAll(".msg-row, [data-message-id]").forEach(function (el) { el.remove(); });
            inner.querySelectorAll(".msg-date-sep").forEach(function (el) { el.remove(); });
            var lastDay = null;
            orderedIds.forEach(function (id) {
                var msg = messagesById.get(id);
                var day = isoToDay(msg.date_envoi_iso);
                if (day && day !== lastDay) {
                    var sep = document.createElement("div");
                    sep.className = "msg-date-sep";
                    sep.innerHTML = '<span class="msg-date-pill">' + escapeHtml(formatDayLabel(day)) + '</span>';
                    inner.appendChild(sep);
                    lastDay = day;
                }
                inner.appendChild(renderMessage(msg));
            });
            if (typeof window.regroupMessagerieMessages === "function") {
                window.regroupMessagerieMessages();
            }
            box.scrollTop = box.scrollHeight;
        }

        function formatDayLabel(day) {
            try {
                var today = new Date();
                var ydToday = today.toISOString().slice(0, 10);
                if (day === ydToday) return "Aujourd'hui";
                var d = new Date(day + "T00:00:00");
                if (isNaN(d.getTime())) return day;
                return d.toLocaleDateString("fr-FR", { weekday: "long", day: "2-digit", month: "long", year: "numeric" });
            } catch (_) {
                return day;
            }
        }

        function appendMessage(data) {
            var wasNew = upsertMessage(data);
            if (data.client_message_id && pendingByClientId.has(data.client_message_id)) {
                pendingByClientId.delete(data.client_message_id);
            }
            if (wasNew) rerenderMessages();
        }

        // Read-receipt UI update: locate the message row via its canonical
        // data-message-id attribute (decoupled from any specific id="check-..."
        // format) and toggle the .read class so the styling stays consistent
        // with the server-rendered template and our CSS.
        function markMessageAsRead(rawMessageId, lectureStatut) {
            if (rawMessageId === undefined || rawMessageId === null) return;
            var msgId = String(rawMessageId);
            var stored = messagesById.get(msgId);
            var st = lectureStatut || "recu";
            if (stored) {
                stored.lecture_statut = st;
                stored.is_lu_par_tous = st === "recu";
            }
            var safeId = (window.CSS && typeof CSS.escape === "function") ? CSS.escape(msgId) : msgId.replace(/"/g, '\\"');
            var row = document.querySelector('[data-message-id="' + safeId + '"]');
            if (!row) return;
            var icons = row.querySelectorAll(".checkmark-icon");
            for (var i = 0; i < icons.length; i++) {
                icons[i].classList.remove("read", "delivered");
                if (st === "recu") icons[i].classList.add("read");
                else if (st === "recu_partiel") icons[i].classList.add("delivered");
            }
        }

        function updateReactionPills(messageId, reactions) {
            var pills = document.querySelectorAll('button[data-reaction-pill="1"][data-message-id="' + messageId + '"]');
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
                    markMessageAsRead(data.message_id, data.lecture_statut);
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

        var typingIndicator = document.getElementById("typingIndicator");
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

        var form = document.querySelector('form#msgForm') || document.querySelector('form[action*="conversation"]');
        var textarea = form ? form.querySelector('textarea[name="contenu"]') : null;
        var submitHandler = null;
        var keydownHandler = null;
        var formInflight = false;
        if (form && textarea) {
            submitHandler = function (e) {
                e.preventDefault();
                if (formInflight) return;
                var contenu = textarea.value.trim();
                if (!contenu) return;
                formInflight = true;
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
                    })
                    .finally(function () {
                        formInflight = false;
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
                if (disposed) return;
                disposed = true;
                if (ws) {
                    try { ws.onclose = null; ws.close(); } catch (_) { /* noop */ }
                    ws = null;
                }
                clearTimeout(typingTimer);
                if (form && submitHandler) form.removeEventListener("submit", submitHandler);
                if (textarea && keydownHandler) textarea.removeEventListener("keydown", keydownHandler);
                // Self-clear the global slot if we still own it. Prevents stale
                // references when callers dispose without subsequently calling init.
                if (window.__messagerieConvInstance === instance) {
                    window.__messagerieConvInstance = null;
                }
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
