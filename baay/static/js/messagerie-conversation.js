(function () {
    const box = document.getElementById("chatBox");
    if (box) {
        box.scrollTop = box.scrollHeight;
    }

    const currentProfileId = String(window.chatConfig?.currentProfileId || "");
    const convId = window.chatConfig?.conversationId;
    const csrfToken = window.chatConfig?.csrfToken;
    if (!box || !convId || !csrfToken || !currentProfileId) {
        return;
    }

    const wsProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = wsProtocol + "//" + window.location.host + "/ws/messagerie/conversation/" + convId + "/";
    const syncUrl = window.chatConfig?.syncUrlTemplate;
    let ws;
    let typingTimer;
    let isTyping = false;
    let reconnectDelayMs = 1500;
    const TYPING_DEBOUNCE = 2000;
    const messagesById = new Map();
    const orderedIds = [];
    const pendingByClientId = new Map();
    let lastSeenIso = null;

    function recordSeen(message) {
        if (message?.date_envoi_iso && (!lastSeenIso || message.date_envoi_iso > lastSeenIso)) {
            lastSeenIso = message.date_envoi_iso;
        }
    }

    function sortOrderedIds() {
        orderedIds.sort((a, b) => {
            const ma = messagesById.get(a);
            const mb = messagesById.get(b);
            const ta = ma?.date_envoi_iso || "";
            const tb = mb?.date_envoi_iso || "";
            if (ta !== tb) return ta.localeCompare(tb);
            return String(a).localeCompare(String(b));
        });
    }

    function upsertMessage(message) {
        const messageId = String(message.message_id || message.id || "");
        if (!messageId) return false;
        const exists = messagesById.has(messageId);
        messagesById.set(messageId, message);
        if (!exists) {
            orderedIds.push(messageId);
            sortOrderedIds();
        }
        recordSeen(message);
        return !exists;
    }

    function escapeHtml(text) {
        const d = document.createElement("div");
        d.textContent = text || "";
        return d.innerHTML;
    }

    function renderReplyPreview(message, isOwn) {
        if (!message.reply_preview) return "";
        const background = isOwn ? "rgba(0,0,0,0.15)" : "var(--bg-main)";
        const color = isOwn ? "inherit" : "var(--text-muted)";
        return `<div class="mb-1 px-2 py-1 rounded-2" style="background: ${background}; font-size: 0.78rem; color: ${color};"><i class="fas fa-reply me-1"></i> ${escapeHtml(message.reply_preview)}</div>`;
    }

    function isImageAttachment(url) {
        const path = String(url || "").split("?")[0].toLowerCase();
        return [".jpg", ".jpeg", ".png", ".gif", ".webp"].some((extension) => path.endsWith(extension));
    }

    function renderAttachment(message, isOwn) {
        if (!message.piece_jointe_url) return "";
        const url = escapeHtml(message.piece_jointe_url);
        const name = escapeHtml(message.piece_jointe_name || "Pièce jointe");
        if (isImageAttachment(message.piece_jointe_url)) {
            return `<a href="${url}" target="_blank" rel="noopener noreferrer"><img src="${url}" alt="${name}" class="rounded-3 mb-1" style="max-width: 220px; max-height: 160px; object-fit: cover; display: block;"></a>`;
        }
        const background = isOwn ? "rgba(0,0,0,0.15)" : "var(--bg-main)";
        const color = isOwn ? "inherit" : "var(--text-main)";
        return `<a href="${url}" target="_blank" rel="noopener noreferrer" class="d-inline-flex align-items-center gap-2 mb-1 px-2 py-1 rounded-2 text-decoration-none" style="background: ${background}; color: ${color};"><i class="fas fa-paperclip"></i> <span style="font-size: 0.78rem;">${name}</span></a>`;
    }

    function renderMessage(message) {
        const isOwn = String(message.sender_id) === currentProfileId;
        const div = document.createElement("div");
        const bubbleClass = isOwn ? "msg-bubble-own" : "msg-bubble-other";
        const senderLine = isOwn ? "" : `<div class="fw-bold mb-1" style="font-size: 0.78rem; color: var(--accent-dark);">${escapeHtml(message.sender_name)}</div>`;
        const replyPreview = renderReplyPreview(message, isOwn);
        const attachment = renderAttachment(message, isOwn);
        const content = message.contenu ? `<div style="white-space: pre-wrap;">${escapeHtml(message.contenu)}</div>` : "";
        const messageId = String(message.message_id || message.id);
        const checkMark = isOwn
            ? `<i class="fas fa-check-double ms-1 checkmark-icon${message.is_lu_par_tous ? " text-success" : ""}" id="check-${messageId}"></i>`
            : "";
        div.className = "d-flex mb-3 " + (isOwn ? "justify-content-end" : "justify-content-start");
        div.setAttribute("data-message-id", messageId);
        div.innerHTML = `<div class="d-flex flex-column ${isOwn ? "align-items-end" : "align-items-start"}" style="max-width: 75%;"><div class="${bubbleClass} rounded-4">${senderLine}${replyPreview}${attachment}${content}<div class="${isOwn ? "text-end" : ""} mt-1" style="font-size: 0.68rem; opacity: 0.85;">${message.date_envoi || ""}${checkMark}</div></div></div>`;
        return div;
    }

    function rerenderMessages() {
        box.querySelectorAll("[data-message-id]").forEach((el) => el.remove());
        orderedIds.forEach((id) => {
            box.appendChild(renderMessage(messagesById.get(id)));
        });
        box.scrollTop = box.scrollHeight;
    }

    function appendMessage(data, force = false) {
        if (!force && String(data.sender_id) === currentProfileId) return;
        const wasNew = upsertMessage(data);
        if (data.client_message_id && pendingByClientId.has(data.client_message_id)) {
            pendingByClientId.delete(data.client_message_id);
        }
        if (wasNew) {
            rerenderMessages();
        }
    }

    async function syncMissedMessages() {
        if (!syncUrl) return;
        let url = syncUrl;
        if (lastSeenIso) {
            url += (url.includes("?") ? "&" : "?") + "since=" + encodeURIComponent(lastSeenIso);
        }
        const response = await fetch(url, {
            headers: { Accept: "application/json" },
        });
        if (!response.ok) return;
        const payload = await response.json();
        (payload.messages || []).forEach((message) => upsertMessage(message));
        rerenderMessages();
    }

    function connect() {
        ws = new WebSocket(wsUrl);
        ws.onopen = function () {
            reconnectDelayMs = 1500;
            syncMissedMessages().catch(() => {});
        };
        ws.onmessage = function (e) {
            const data = JSON.parse(e.data);
            if (data.type === "chat_message_v1" || data.type === "chat_message") {
                appendMessage(data);
            } else if ((data.type === "chat_typing_v1" || data.type === "chat_typing") && String(data.sender_id) !== String(currentProfileId)) {
                showTyping();
            } else if (data.type === "chat_stop_typing_v1" || data.type === "chat_stop_typing") {
                hideTyping();
            } else if (data.type === "chat_read_receipt_v1" || data.type === "chat_read_receipt") {
                const checkIcon = document.getElementById("check-" + data.message_id);
                if (checkIcon) {
                    checkIcon.style.color = "#064e3b";
                }
            }
        };
        ws.onclose = function () {
            setTimeout(connect, reconnectDelayMs);
            reconnectDelayMs = Math.min(reconnectDelayMs * 2, 10000);
        };
    }
    connect();

    let typingIndicator = document.getElementById("typingIndicator");
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

    const form = document.querySelector('form[action*="conversation"]');
    if (!form) return;
    const textarea = form.querySelector('textarea[name="contenu"]');
    if (!textarea) return;

    form.addEventListener("submit", function (e) {
        e.preventDefault();
        const contenu = textarea.value.trim();
        const fileInput = form.querySelector('input[type="file"][name="piece_jointe"]');
        const hasFile = Boolean(fileInput?.files?.length);
        if (!contenu && !hasFile) return;
        const clientMessageId = crypto.randomUUID();
        pendingByClientId.set(clientMessageId, Date.now());
        const payload = new FormData(form);
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
            .then((r) => r.json())
            .then((data) => {
                appendMessage(data, true);
                textarea.value = "";
                textarea.style.height = "";
                window.clearReply?.();
                window.clearFile?.();
            })
            .catch(() => {
                pendingByClientId.delete(clientMessageId);
            });
    });

    textarea?.addEventListener("keydown", function () {
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
    });

    window.toggleReaction = function (messageId, emoji) {
        const url = "/api/messages/" + messageId + "/reaction/";
        const data = new FormData();
        data.append("emoji", emoji);
        data.append("csrfmiddlewaretoken", csrfToken);
        fetch(url, {
            method: "POST",
            headers: { "X-CSRFToken": csrfToken },
            body: data,
        })
            .then((r) => r.json())
            .then((d) => {
                if (d.reactions) {
                    const reactionButtons = document.querySelectorAll(`button[onclick*="${messageId}"]`);
                    reactionButtons.forEach((btn) => {
                        const txt = btn.textContent.trim();
                        const key = txt.split(" ")[0];
                        if (d.reactions[key]) {
                            btn.textContent = `${key} ${d.reactions[key]}`;
                        }
                    });
                }
            });
    };
})();
