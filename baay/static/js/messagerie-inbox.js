(function () {
    const list = document.getElementById("conversationList");
    if (!list) return;

    const wsProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = wsProtocol + "//" + window.location.host + "/ws/messagerie/inbox/";
    const unreadApiUrl = window.inboxConfig?.unreadApiUrl;
    let ws;
    let reconnectDelayMs = 1500;

    function getOrCreateUnreadBadge(item) {
        let badge = item.querySelector(".conv-unread");
        if (badge) return badge;
        badge = document.createElement("span");
        badge.className = "badge rounded-pill unread-badge ms-1 conv-unread";
        const title = item.querySelector(".conv-title");
        if (title) {
            title.appendChild(badge);
        }
        return badge;
    }

    function updateConversationItem(event) {
        const item = list.querySelector(`.conv-item[data-conversation-id="${event.conversation_id}"]`);
        if (!item) return;

        const previewEl = item.querySelector(".conv-preview");
        const timeEl = item.querySelector(".conv-time");
        const avatarEl = item.querySelector(".avatar-pill");

        if (previewEl) {
            previewEl.textContent = event.preview || "Aucun message";
            previewEl.classList.toggle("preview-unread", Number(event.unread_count) > 0);
            previewEl.classList.toggle("text-muted", Number(event.unread_count) <= 0);
        }
        if (timeEl) {
            timeEl.textContent = event.date_envoi || "";
        }
        if (avatarEl) {
            avatarEl.classList.toggle("online", Boolean(event.is_online));
        }

        const unreadCount = Number(event.unread_count || 0);
        const badge = getOrCreateUnreadBadge(item);
        if (unreadCount > 0) {
            badge.textContent = String(unreadCount);
            badge.style.display = "";
            item.classList.add("unread");
        } else {
            badge.style.display = "none";
            item.classList.remove("unread");
        }

        if (event.move_to_top !== false) {
            list.prepend(item);
        }
    }

    function updateGlobalUnreadCount(nonLusTotal) {
        const navBadge = document.querySelector("#notif-badge, .notif-badge");
        if (!navBadge) return;
        const total = Number(nonLusTotal || 0);
        navBadge.textContent = String(total);
        navBadge.style.display = total > 0 ? "" : "none";
    }

    async function pollFallback() {
        if (!unreadApiUrl) return;
        try {
            const response = await fetch(unreadApiUrl, { headers: { Accept: "application/json" } });
            if (!response.ok) return;
            const data = await response.json();
            updateGlobalUnreadCount(data.non_lus);
        } catch (_) {
            // Silent fallback poll errors.
        }
    }

    function connect() {
        ws = new WebSocket(wsUrl);
        ws.onopen = function () {
            reconnectDelayMs = 1500;
        };
        ws.onmessage = function (e) {
            const data = JSON.parse(e.data);
            if (data.type === "inbox_update_v1") {
                updateConversationItem(data);
            } else if (data.type === "unread_count_v1") {
                updateGlobalUnreadCount(data.non_lus_total);
            }
        };
        ws.onclose = function () {
            setTimeout(connect, reconnectDelayMs);
            reconnectDelayMs = Math.min(reconnectDelayMs * 2, 10000);
        };
    }

    connect();
    window.setInterval(pollFallback, 30000);
})();
