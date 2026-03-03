/* ===== CTI RAG Chatbot — Frontend Logic (Streaming) ===== */

// Configure marked for safe markdown rendering
marked.setOptions({
    breaks: true,
    gfm: true,
    highlight: function (code, lang) {
        if (lang && hljs.getLanguage(lang)) {
            return hljs.highlight(code, { language: lang }).value;
        }
        return hljs.highlightAuto(code).value;
    },
});

const messagesEl = document.getElementById("messages");
const questionInput = document.getElementById("question-input");
const sendBtn = document.getElementById("send-btn");
const resetBtn = document.getElementById("reset-btn");
const welcomeScreen = document.getElementById("welcome-screen");
const sidebar = document.getElementById("sidebar");
const sidebarToggle = document.getElementById("sidebar-toggle");

// ===== Event Listeners =====
sendBtn.addEventListener("click", sendMessage);

questionInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

questionInput.addEventListener("input", () => {
    questionInput.style.height = "auto";
    questionInput.style.height = Math.min(questionInput.scrollHeight, 140) + "px";
});

document.querySelectorAll(".suggestion-chip").forEach((btn) => {
    btn.addEventListener("click", () => {
        questionInput.value = btn.dataset.q;
        sendMessage();
        closeSidebar();
    });
});

document.querySelectorAll(".welcome-card").forEach((card) => {
    card.addEventListener("click", () => {
        questionInput.value = card.dataset.q;
        sendMessage();
    });
});

resetBtn.addEventListener("click", async () => {
    await fetch("/api/reset", { method: "POST" });
    messagesEl.innerHTML = createWelcomeHTML();
    bindWelcomeCards();
});

sidebarToggle.addEventListener("click", () => {
    sidebar.classList.toggle("open");
});

function closeSidebar() {
    sidebar.classList.remove("open");
}

document.addEventListener("click", (e) => {
    if (
        sidebar.classList.contains("open") &&
        !sidebar.contains(e.target) &&
        !sidebarToggle.contains(e.target)
    ) {
        closeSidebar();
    }
});

// ===== Send Message (Streaming via SSE) =====
let isStreaming = false;

async function sendMessage() {
    const q = questionInput.value.trim();
    if (!q || isStreaming) return;

    // Hide welcome screen
    const ws = document.querySelector(".welcome-screen");
    if (ws) ws.remove();

    appendMessage("user", q);
    questionInput.value = "";
    questionInput.style.height = "auto";
    sendBtn.disabled = true;
    isStreaming = true;
    const typingId = showTyping();

    try {
        const res = await fetch("/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ question: q }),
        });

        if (!res.ok) {
            const errData = await res.json();
            throw new Error(errData.error || "Request failed.");
        }

        removeTyping(typingId);

        // Prepare the bot message shell
        const { bubble, mdEl, wrapper, msg } = createBotMessageShell();
        messagesEl.appendChild(msg);

        let fullText = "";
        let sources = [];
        let sourcesRendered = false;

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split("\n");
            buffer = lines.pop(); // keep incomplete line

            for (const line of lines) {
                if (!line.startsWith("data: ")) continue;
                const jsonStr = line.slice(6).trim();
                if (!jsonStr) continue;

                let payload;
                try {
                    payload = JSON.parse(jsonStr);
                } catch {
                    continue;
                }

                if (payload.sources) {
                    sources = payload.sources;
                }

                if (payload.token) {
                    fullText += payload.token;
                    // Re-render markdown on each token batch
                    mdEl.innerHTML = renderMarkdown(fullText + "▍");
                    scrollToBottom();
                }

                if (payload.replace) {
                    fullText = payload.replace;
                    mdEl.innerHTML = renderMarkdown(fullText);
                }

                if (payload.done && !sourcesRendered) {
                    // Final render without cursor
                    mdEl.innerHTML = renderMarkdown(fullText);

                    // Add sources
                    if (sources.length > 0) {
                        appendSourcesTo(bubble, sources);
                        sourcesRendered = true;
                    }

                    // Add meta row
                    const meta = document.createElement("div");
                    meta.className = "message-meta";
                    meta.innerHTML = `<span class="msg-time">${getTimeStr()}</span>`;
                    meta.appendChild(createCopyButton(fullText));
                    wrapper.appendChild(meta);

                    scrollToBottom();
                }
            }
        }

        // Safety: if stream ended without a done event
        if (!sourcesRendered) {
            mdEl.innerHTML = renderMarkdown(fullText);
            if (sources.length > 0) appendSourcesTo(bubble, sources);
            const meta = document.createElement("div");
            meta.className = "message-meta";
            meta.innerHTML = `<span class="msg-time">${getTimeStr()}</span>`;
            meta.appendChild(createCopyButton(fullText));
            wrapper.appendChild(meta);
        }
    } catch (e) {
        removeTyping(typingId);
        appendMessage("error", e.message);
    } finally {
        sendBtn.disabled = false;
        isStreaming = false;
        questionInput.focus();
    }
}

// ===== Create an empty bot message shell for streaming into =====
function createBotMessageShell() {
    const msg = document.createElement("div");
    msg.className = "message bot";

    const avatar = document.createElement("div");
    avatar.className = "avatar";
    avatar.textContent = "🛡️";

    const wrapper = document.createElement("div");
    wrapper.className = "bubble-wrapper";

    const bubble = document.createElement("div");
    bubble.className = "bubble";

    const mdEl = document.createElement("div");
    mdEl.className = "md-content";
    mdEl.innerHTML = renderMarkdown("▍");
    bubble.appendChild(mdEl);

    wrapper.appendChild(bubble);
    msg.appendChild(avatar);
    msg.appendChild(wrapper);

    return { bubble, mdEl, wrapper, msg };
}

// ===== Append sources to a bubble =====
function appendSourcesTo(bubble, sources) {
    const toggle = document.createElement("button");
    toggle.className = "sources-toggle";
    toggle.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><polyline points="6 9 12 15 18 9"/></svg> ${sources.length} source${sources.length > 1 ? "s" : ""} retrieved`;

    const list = document.createElement("div");
    list.className = "sources-list hidden";

    sources.forEach((s) => {
        const card = document.createElement("div");
        card.className = "source-card";
        card.innerHTML = `
            <div class="src-header">
                <span class="src-name">${escapeHtml(s.name)}</span>
                <span class="src-type">${escapeHtml(s.type)}</span>
            </div>
            ${s.url ? `<a class="src-link" href="${escapeHtml(s.url)}" target="_blank" rel="noopener">View on MITRE →</a>` : ""}
            <div class="src-snippet">${escapeHtml(s.snippet)}…</div>
        `;
        list.appendChild(card);
    });

    toggle.addEventListener("click", () => {
        const isHidden = list.classList.contains("hidden");
        list.classList.toggle("hidden", !isHidden);
        toggle.classList.toggle("open", isHidden);
    });

    bubble.appendChild(toggle);
    bubble.appendChild(list);
}

// ===== Append User / Error Message =====
function appendMessage(role, text) {
    const msg = document.createElement("div");
    msg.className = `message ${role}`;

    const avatar = document.createElement("div");
    avatar.className = "avatar";

    if (role === "user") {
        avatar.textContent = "👤";
    } else if (role === "error") {
        avatar.textContent = "⚠️";
        msg.className = "message bot error";
    } else {
        avatar.textContent = "🛡️";
    }

    const wrapper = document.createElement("div");
    wrapper.className = "bubble-wrapper";

    const bubble = document.createElement("div");
    bubble.className = "bubble";

    if (role === "user") {
        bubble.innerHTML = `<p>${escapeHtml(text)}</p>`;
    } else {
        bubble.innerHTML = `<div class="md-content">${renderMarkdown(text)}</div>`;
    }

    wrapper.appendChild(bubble);

    const meta = document.createElement("div");
    meta.className = "message-meta";
    meta.innerHTML = `<span class="msg-time">${getTimeStr()}</span>`;

    if (role !== "user") {
        meta.appendChild(createCopyButton(text));
    }

    wrapper.appendChild(meta);
    msg.appendChild(avatar);
    msg.appendChild(wrapper);
    messagesEl.appendChild(msg);
    scrollToBottom();
}

// ===== Typing Indicator =====
function showTyping() {
    const id = "typing-" + Date.now();
    const msg = document.createElement("div");
    msg.className = "message bot";
    msg.id = id;
    msg.innerHTML = `
        <div class="avatar">🛡️</div>
        <div class="bubble-wrapper">
            <div class="bubble typing-bubble">
                <span></span><span></span><span></span>
            </div>
        </div>`;
    messagesEl.appendChild(msg);
    scrollToBottom();
    return id;
}

function removeTyping(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}

// ===== Utilities =====
function scrollToBottom() {
    requestAnimationFrame(() => {
        messagesEl.scrollTop = messagesEl.scrollHeight;
    });
}

function getTimeStr() {
    return new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}

function renderMarkdown(text) {
    try {
        return marked.parse(text);
    } catch {
        return escapeHtml(text).replace(/\n/g, "<br/>");
    }
}

function createCopyButton(text) {
    const btn = document.createElement("button");
    btn.className = "btn-copy";
    btn.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/></svg> Copy`;
    btn.addEventListener("click", async () => {
        try {
            await navigator.clipboard.writeText(text);
            btn.classList.add("copied");
            btn.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12"><polyline points="20 6 9 17 4 12"/></svg> Copied!`;
            setTimeout(() => {
                btn.classList.remove("copied");
                btn.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/></svg> Copy`;
            }, 2000);
        } catch {
            // fallback
        }
    });
    return btn;
}

function createWelcomeHTML() {
    return `
    <div class="welcome-screen">
        <div class="welcome-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="48" height="48">
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                <path d="M9 12l2 2 4-4" stroke-linecap="round" stroke-linejoin="round" />
            </svg>
        </div>
        <h2>Welcome to CTI RAG</h2>
        <p>Ask me about MITRE ATT&CK techniques, threat groups, malware, mitigations, or any cyber threat intelligence topic.</p>
        <div class="welcome-cards">
            <div class="welcome-card" data-q="Explain T1059 Command and Scripting Interpreter">
                <div class="wc-icon">🔧</div>
                <div class="wc-text"><strong>Techniques</strong><span>Explain T1059 technique</span></div>
            </div>
            <div class="welcome-card" data-q="What techniques does APT28 use?">
                <div class="wc-icon">👥</div>
                <div class="wc-text"><strong>Threat Groups</strong><span>APT28 techniques</span></div>
            </div>
            <div class="welcome-card" data-q="How to detect and mitigate phishing attacks?">
                <div class="wc-icon">🛡️</div>
                <div class="wc-text"><strong>Mitigations</strong><span>Phishing defenses</span></div>
            </div>
            <div class="welcome-card" data-q="Tell me about Cobalt Strike capabilities">
                <div class="wc-icon">🦠</div>
                <div class="wc-text"><strong>Malware</strong><span>Cobalt Strike analysis</span></div>
            </div>
        </div>
    </div>`;
}

function bindWelcomeCards() {
    document.querySelectorAll(".welcome-card").forEach((card) => {
        card.addEventListener("click", () => {
            questionInput.value = card.dataset.q;
            sendMessage();
        });
    });
}
