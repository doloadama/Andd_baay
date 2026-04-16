document.addEventListener('DOMContentLoaded', () => {
    const themeToggle = document.getElementById('themeToggle');
    const themeToggleMobile = document.getElementById('themeToggleMobile');
    const htmlElement = document.documentElement;
    const themeColorMeta = document.querySelector('meta[name="theme-color"]');

    function setTheme(newTheme, { persist = true } = {}) {
        htmlElement.setAttribute('data-bs-theme', newTheme);

        if (newTheme === 'dark') {
            htmlElement.classList.add('dark-mode');
            htmlElement.classList.remove('light-mode');
            document.body.classList.add('dark-mode');
            document.body.classList.remove('light-mode');
            if (themeColorMeta) themeColorMeta.setAttribute('content', '#0a0d0a');
        } else {
            htmlElement.classList.add('light-mode');
            htmlElement.classList.remove('dark-mode');
            document.body.classList.add('light-mode');
            document.body.classList.remove('dark-mode');
            if (themeColorMeta) themeColorMeta.setAttribute('content', '#f4f3ef');
        }

        if (persist) {
            try {
                localStorage.setItem('theme', newTheme);
            } catch (e) {
                // localStorage may be blocked in private mode / WebView
            }
        }
    }

    setTheme(htmlElement.getAttribute('data-bs-theme') === 'dark' ? 'dark' : 'light', { persist: false });

    function toggleTheme(event) {
        if (event) event.preventDefault();
        const isCurrentlyDark = htmlElement.getAttribute('data-bs-theme') === 'dark';
        const newTheme = isCurrentlyDark ? 'light' : 'dark';
        setTheme(newTheme, { persist: true });
        window.dispatchEvent(new CustomEvent('themeChanged', { detail: { isDark: newTheme === 'dark' } }));
    }

    if (themeToggle) themeToggle.addEventListener('click', toggleTheme);
    if (themeToggleMobile) themeToggleMobile.addEventListener('click', toggleTheme);

    const prefersDark = window.matchMedia ? window.matchMedia('(prefers-color-scheme: dark)') : null;
    const onSystemThemeChange = (e) => {
        let stored = null;
        try {
            stored = localStorage.getItem('theme');
        } catch (err) {
            stored = null;
        }
        if (stored === 'light' || stored === 'dark') return;
        setTheme(e.matches ? 'dark' : 'light', { persist: false });
    };

    if (prefersDark) {
        if (typeof prefersDark.addEventListener === 'function') {
            prefersDark.addEventListener('change', onSystemThemeChange);
        } else if (typeof prefersDark.addListener === 'function') {
            prefersDark.addListener(onSystemThemeChange);
        }
    }

    const chatBubble = document.getElementById('chatBubble');
    const chatWindow = document.getElementById('chatWindow');
    const minimizeChat = document.getElementById('minimizeChat');
    const chatNotification = document.getElementById('chatNotification');
    const messageInput = document.getElementById('message');
    const sendButton = document.getElementById('sendMessage');
    const chatMessages = document.getElementById('chat-messages');
    const welcomeMessage = document.getElementById('welcome-message');
    const clearChatButton = document.getElementById('clearChat');

    let messageHistory = [];
    let unreadMessages = 0;

    if (localStorage.getItem('chatState') === 'open' && window.innerWidth > 768) {
        setTimeout(openChat, 100);
    }

    if (chatBubble) {
        chatBubble.addEventListener('click', () => chatWindow.classList.contains('open') ? closeChat() : openChat());
    }
    if (minimizeChat) {
        minimizeChat.addEventListener('click', closeChat);
    }

    function openChat() {
        chatWindow.classList.add('open');
        chatBubble.classList.add('active');
        localStorage.setItem('chatState', 'open');
        unreadMessages = 0;
        chatNotification.classList.remove('show');
        chatNotification.hidden = true;
        setTimeout(() => messageInput && messageInput.focus(), 300);
    }

    function closeChat() {
        chatWindow.classList.remove('open');
        chatBubble.classList.remove('active');
        localStorage.setItem('chatState', 'closed');
    }

    if (messageInput) {
        messageInput.addEventListener('input', function () {
            this.style.height = 'auto';
            this.style.height = (Math.min(this.scrollHeight, 100)) + 'px';
        });

        messageInput.addEventListener('keydown', e => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
    }

    if (sendButton) {
        sendButton.addEventListener('click', () => sendMessage());
    }

    if (clearChatButton) {
        clearChatButton.addEventListener('click', () => {
            if (messageHistory.length && confirm('Effacer la discussion ?')) {
                messageHistory = [];
                localStorage.removeItem('chatHistory');
                if (chatMessages) {
                    chatMessages.innerHTML = '';
                    if (welcomeMessage) {
                        chatMessages.appendChild(welcomeMessage);
                        welcomeMessage.style.display = 'block';
                    }
                }
            }
        });
    }

    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    let lastUserMessage = '';

    function sendMessage(retryText = null) {
        if (!messageInput) return;
        const message = retryText || messageInput.value.trim();
        if (!message) return;

        lastUserMessage = message;

        if (welcomeMessage) welcomeMessage.style.display = 'none';
        if (!retryText) {
            addMessage(message, 'user');
            messageInput.value = '';
            messageInput.style.height = 'auto';
        }

        if (sendButton) {
            sendButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
            sendButton.disabled = true;
        }

        const historyPayload = messageHistory.slice(-12).map(m => ({
            role: m.sender === 'user' ? 'user' : 'assistant',
            text: m.text || m.content || ''
        }));

        fetch('/api/chatbot/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
            body: JSON.stringify({ message, history: historyPayload }),
        })
            .then(async res => {
                const data = await res.json();
                if (!res.ok || data.error) {
                    throw { serverMessage: data.error || 'Une erreur est survenue.' };
                }
                return data;
            })
            .then(data => {
                addMessage(data.response || 'Aucune réponse.', 'assistant');
                if (chatWindow && !chatWindow.classList.contains('open')) {
                    unreadMessages++;
                    chatNotification.textContent = unreadMessages;
                    chatNotification.classList.add('show');
                    chatNotification.hidden = false;
                }
            })
            .catch(err => {
                const msg = err.serverMessage || 'Une erreur est survenue. Veuillez réessayer.';
                renderError(msg, lastUserMessage);
            })
            .finally(() => {
                if (sendButton) {
                    sendButton.innerHTML = '<i class="fas fa-arrow-up"></i>';
                    sendButton.disabled = false;
                }
            });
    }

    function renderError(friendlyMessage, retryMessage) {
        if (!chatMessages) return;
        const timestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        const messageEl = document.createElement('div');
        messageEl.className = 'message assistant';

        const contentEl = document.createElement('div');
        contentEl.className = 'message-content';
        contentEl.style.borderColor = 'var(--danger)';
        contentEl.style.color = 'var(--danger)';

        const retryBtn = document.createElement('button');
        retryBtn.innerHTML = '<i class="fas fa-redo me-1"></i> Réessayer';
        retryBtn.style.cssText = 'margin-top:8px; padding:5px 12px; border-radius:8px; border:1px solid var(--danger); background:transparent; color:var(--danger); font-size:0.8rem; cursor:pointer; display:block;';
        retryBtn.onclick = () => {
            messageEl.remove();
            sendMessage(retryMessage);
        };

        contentEl.textContent = friendlyMessage;
        contentEl.appendChild(retryBtn);

        const timeEl = document.createElement('div');
        timeEl.className = 'message-time';
        timeEl.textContent = timestamp;

        messageEl.appendChild(contentEl);
        messageEl.appendChild(timeEl);
        chatMessages.appendChild(messageEl);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    const CHAT_HISTORY_KEY = 'chatHistory';
    const MAX_HISTORY = 50;

    function saveChatHistory() {
        const toSave = messageHistory.slice(-MAX_HISTORY);
        try {
            localStorage.setItem(CHAT_HISTORY_KEY, JSON.stringify(toSave));
        } catch (e) {
            // ignore quota errors
        }
    }

    function restoreChatHistory() {
        if (!chatMessages) return;
        try {
            const saved = localStorage.getItem(CHAT_HISTORY_KEY);
            if (!saved) return;
            const history = JSON.parse(saved);
            if (!Array.isArray(history) || history.length === 0) return;

            if (welcomeMessage) welcomeMessage.style.display = 'none';
            history.forEach(msg => {
                renderMessage(msg.text, msg.sender, msg.timestamp, false);
                messageHistory.push(msg);
            });
        } catch (e) {
            localStorage.removeItem(CHAT_HISTORY_KEY);
        }
    }

    function renderMessage(text, sender, timestamp, scroll = true) {
        if (!chatMessages) return;
        const messageEl = document.createElement('div');
        messageEl.className = `message ${sender}`;

        const contentEl = document.createElement('div');
        contentEl.className = 'message-content';
        contentEl.innerHTML = text.replace(/\n/g, '<br>');

        const timeEl = document.createElement('div');
        timeEl.className = 'message-time';
        timeEl.textContent = timestamp;

        messageEl.appendChild(contentEl);
        messageEl.appendChild(timeEl);
        chatMessages.appendChild(messageEl);
        if (scroll) chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function addMessage(text, sender, isError = false) {
        if (!chatMessages) return;
        const timestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        const msgData = { text, sender, timestamp };
        messageHistory.push(msgData);
        saveChatHistory();

        const messageEl = document.createElement('div');
        messageEl.className = `message ${sender}`;

        const contentEl = document.createElement('div');
        contentEl.className = 'message-content';
        if (isError) {
            contentEl.style.borderColor = 'var(--danger)';
            contentEl.style.color = 'var(--danger)';
        }
        contentEl.innerHTML = text.replace(/\n/g, '<br>');

        const timeEl = document.createElement('div');
        timeEl.className = 'message-time';
        timeEl.textContent = timestamp;

        messageEl.appendChild(contentEl);
        messageEl.appendChild(timeEl);
        chatMessages.appendChild(messageEl);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    restoreChatHistory();

    setTimeout(() => {
        if (chatWindow && !chatWindow.classList.contains('open')) {
            chatNotification.classList.add('show');
            chatNotification.hidden = false;
        }
    }, 3000);
});
