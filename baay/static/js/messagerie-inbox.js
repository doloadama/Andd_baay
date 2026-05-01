(function () {
    "use strict";

    var wsProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    var wsUrl = wsProtocol + "//" + window.location.host + "/ws/messagerie/inbox/";
    var ws = null;
    var connected = false;
    var reconnectDelayMs = 1500;
    var pollIntervalId = null;

    function getList() {
        return document.getElementById("conversationList");
    }

    function getOrCreateUnreadBadge(item) {
        var badge = item.querySelector(".conv-unread");
        if (badge) return badge;
        badge = document.createElement("span");
        badge.className = "badge rounded-pill unread-badge ms-1 conv-unread";
        var title = item.querySelector(".conv-title");
        if (title) title.appendChild(badge);
        return badge;
    }

    function updateConversationItem(event) {
        var list = getList();
        if (!list) return;
        var item = list.querySelector('.conv-item[data-conversation-id="' + event.conversation_id + '"]');
        if (!item) return;

        var previewEl = item.querySelector(".conv-preview");
        var timeEl = item.querySelector(".conv-time");
        var avatarEl = item.querySelector(".avatar-pill");

        if (previewEl) {
            previewEl.textContent = event.preview || "Aucun message";
            previewEl.classList.toggle("preview-unread", Number(event.unread_count) > 0);
            previewEl.classList.toggle("text-muted", Number(event.unread_count) <= 0);
        }
        if (timeEl) timeEl.textContent = event.date_envoi || "";
        if (avatarEl) avatarEl.classList.toggle("online", Boolean(event.is_online));

        var unreadCount = Number(event.unread_count || 0);
        var badge = getOrCreateUnreadBadge(item);
        if (unreadCount > 0) {
            badge.textContent = String(unreadCount);
            badge.style.display = "";
            item.classList.add("unread");
        } else {
            badge.style.display = "none";
            item.classList.remove("unread");
        }

        list.prepend(item);
    }

    function updateGlobalUnreadCount(nonLusTotal) {
        var total = Number(nonLusTotal || 0);
        var displayCount = total > 9 ? "9+" : String(total);

        var navBadge = document.getElementById("navUnreadBadge");
        if (navBadge) {
            if (total > 0) {
                navBadge.textContent = displayCount;
                navBadge.style.display = "inline-flex";
            } else {
                navBadge.textContent = "";
                navBadge.style.display = "none";
            }
        }

        var floatingBadge = document.getElementById("floatingNotifBadge");
        if (floatingBadge) {
            if (total > 0) {
                floatingBadge.textContent = displayCount;
                floatingBadge.classList.add("show");
            } else {
                floatingBadge.textContent = "";
                floatingBadge.classList.remove("show");
            }
        }

        var bottomNavBadge = document.getElementById("bottomNavMessagerieBadge");
        if (bottomNavBadge) {
            if (total > 0) {
                bottomNavBadge.textContent = displayCount;
                bottomNavBadge.style.display = "inline-flex";
            } else {
                bottomNavBadge.textContent = "";
                bottomNavBadge.style.display = "none";
            }
        }
    }

    function pollFallback() {
        var unreadApiUrl = window.inboxConfig && window.inboxConfig.unreadApiUrl;
        if (!unreadApiUrl) return;
        fetch(unreadApiUrl, { headers: { Accept: "application/json" } })
            .then(function (response) { return response.ok ? response.json() : null; })
            .then(function (data) { if (data) updateGlobalUnreadCount(data.non_lus); })
            .catch(function () { /* noop */ });
    }

    function connect() {
        if (connected) return;
        try {
            ws = new WebSocket(wsUrl);
        } catch (_) {
            return;
        }
        ws.onopen = function () {
            connected = true;
            reconnectDelayMs = 1500;
        };
        ws.onmessage = function (e) {
            var data;
            try { data = JSON.parse(e.data); } catch (_) { return; }
            if (data.type === "inbox_update_v1") {
                updateConversationItem(data);
            } else if (data.type === "unread_count_v1") {
                updateGlobalUnreadCount(data.non_lus_total);
            }
        };
        ws.onclose = function () {
            connected = false;
            setTimeout(connect, reconnectDelayMs);
            reconnectDelayMs = Math.min(reconnectDelayMs * 2, 10000);
        };
        ws.onerror = function () { /* allow onclose to handle reconnect */ };
    }

    function initMessagerieInbox() {
        connect();
        if (pollIntervalId === null) {
            pollIntervalId = window.setInterval(pollFallback, 30000);
            // Run once at startup to seed badges quickly.
            pollFallback();
        }
    }

    window.initMessagerieInbox = initMessagerieInbox;
    window.updateMessagerieGlobalUnread = updateGlobalUnreadCount;

    initMessagerieInbox();
})();
