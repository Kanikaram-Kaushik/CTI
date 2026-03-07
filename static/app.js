const messagesEl = document.getElementById("messages");
const questionInput = document.getElementById("question-input");
const sendBtn = document.getElementById("send-btn");
const resetBtn = document.getElementById("reset-btn");

const API_BASE = window.location.origin.includes('5000') ? '' : 'http://127.0.0.1:5000';

// ── Fetch backend status (online vs offline mode) ──
(async function fetchStatus() {
    try {
        const res = await fetch(`${API_BASE}/api/status`);
        const data = await res.json();
        const badge = document.getElementById("status-badge");
        const statusText = document.getElementById("status-text");
        const modelName = document.getElementById("model-name");
        if (data.mode === "groq") {
            statusText.textContent = "Online — Groq Cloud";
            modelName.textContent = data.model;
        } else if (data.mode === "ollama") {
            statusText.textContent = "Offline — Ollama Local";
            badge.classList.add("offline-mode");
            modelName.textContent = data.model + " (local)";
        } else {
            statusText.textContent = "Connecting…";
        }
    } catch {
        const statusText = document.getElementById("status-text");
        if (statusText) statusText.textContent = "Backend unavailable";
    }
})();

sendBtn.addEventListener("click", sendMessage);
questionInput.addEventListener("keydown", e => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); }
});
questionInput.addEventListener("input", () => {
    questionInput.style.height = "auto";
    questionInput.style.height = Math.min(questionInput.scrollHeight, 140) + "px";
});

async function sendMessage() {
    const q = questionInput.value.trim();
    if (!q) return;
    appendMessage("user", q);
    questionInput.value = "";
    questionInput.style.height = "auto";
    sendBtn.disabled = true;
    const typingId = showTyping();
    try {
        const res = await fetch(`${API_BASE}/api/chat`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ question: q }),
        });
        if (!res.ok) {
            removeTyping(typingId);
            const data = await res.json().catch(() => ({}));
            throw new Error(data.error || "Request failed.");
        }

        const msg = document.createElement("div");
        msg.className = "message bot";
        const avatar = document.createElement("div");
        avatar.className = "avatar";
        avatar.textContent = "🤖";
        const bubble = document.createElement("div");
        bubble.className = "bubble";

        const reader = res.body.getReader();
        const decoder = new TextDecoder("utf-8");
        let fullText = "";
        let sourcesData = [];
        let buffer = "";
        let hasStartedText = false;

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });

            let newlineIndex;
            while ((newlineIndex = buffer.indexOf("\n\n")) >= 0) {
                const eventStr = buffer.slice(0, newlineIndex);
                buffer = buffer.slice(newlineIndex + 2);

                if (eventStr.startsWith("data: ")) {
                    const dataStr = eventStr.substring(6).trim();
                    if (dataStr === "[DONE]") continue;
                    try {
                        const evt = JSON.parse(dataStr);
                        if (evt.sources) sourcesData = evt.sources;
                        if (evt.chunk) {
                            if (!hasStartedText) {
                                hasStartedText = true;
                                removeTyping(typingId);
                                msg.appendChild(avatar);
                                msg.appendChild(bubble);
                                messagesEl.appendChild(msg);
                            }
                            fullText += evt.chunk;
                            bubble.innerHTML = `<p>${formatText(fullText)}</p>`;
                            scrollToBottom();
                        }
                    } catch (err) { }
                }
            }
        }

        // Edge case: if loop finished but no text was generated
        if (!hasStartedText) {
            removeTyping(typingId);
            msg.appendChild(avatar);
            msg.appendChild(bubble);
            messagesEl.appendChild(msg);
        }

        if (sourcesData.length > 0) {
            const toggle = document.createElement("button");
            toggle.className = "sources-toggle";
            toggle.innerHTML = `📄 View ${sourcesData.length} source${sourcesData.length > 1 ? "s" : ""} ▾`;
            const list = document.createElement("div");
            list.className = "sources-list hidden";
            sourcesData.forEach(s => {
                const card = document.createElement("div");
                card.className = "source-card";
                card.innerHTML = `<div class="src-name">${s.name}</div>
            <div class="src-type">${s.type}${s.url ? ` · <a href="${s.url}" target="_blank" style="color:var(--accent)">link</a>` : ""}</div>
            <div class="src-snippet">${s.snippet}…</div>`;
                list.appendChild(card);
            });
            toggle.addEventListener("click", () => {
                const open = !list.classList.contains("hidden");
                list.classList.toggle("hidden");
                toggle.innerHTML = open ? `📄 View ${sourcesData.length} source${sourcesData.length > 1 ? "s" : ""} ▾` : `📄 Hide sources ▴`;
            });
            bubble.appendChild(toggle);
            bubble.appendChild(list);
            scrollToBottom();
        }
    } catch (e) {
        removeTyping(typingId);
        appendMessage("bot", `❌ ${e.message}`);
    } finally {
        sendBtn.disabled = false;
        questionInput.focus();
    }
}

document.querySelectorAll(".suggestion-chip").forEach(btn => {
    btn.addEventListener("click", () => {
        questionInput.value = btn.dataset.q;
        sendMessage();
    });
});

resetBtn.addEventListener("click", async () => {
    await fetch(`${API_BASE}/api/reset`, { method: "POST" });
    messagesEl.innerHTML = `
    <div class="message bot">
      <div class="avatar">🤖</div>
      <div class="bubble"><p>Chat reset! What would you like to know about cyber threats?</p></div>
    </div>`;
});

function appendMessage(role, text) {
    const msg = document.createElement("div");
    msg.className = `message ${role}`;
    const avatar = document.createElement("div");
    avatar.className = "avatar";
    avatar.textContent = role === "user" ? "👤" : "🤖";
    const bubble = document.createElement("div");
    bubble.className = "bubble";
    bubble.innerHTML = `<p>${formatText(text)}</p>`;
    msg.appendChild(avatar);
    msg.appendChild(bubble);
    messagesEl.appendChild(msg);
    scrollToBottom();
}

function appendBotResponse(answer, sources) {
    const msg = document.createElement("div");
    msg.className = "message bot";
    const avatar = document.createElement("div");
    avatar.className = "avatar";
    avatar.textContent = "🤖";
    const bubble = document.createElement("div");
    bubble.className = "bubble";
    bubble.innerHTML = `<p>${formatText(answer)}</p>`;
    if (sources.length > 0) {
        const toggle = document.createElement("button");
        toggle.className = "sources-toggle";
        toggle.innerHTML = `📄 View ${sources.length} source${sources.length > 1 ? "s" : ""} ▾`;
        const list = document.createElement("div");
        list.className = "sources-list hidden";
        sources.forEach(s => {
            const card = document.createElement("div");
            card.className = "source-card";
            card.innerHTML = `
        <div class="src-name">${s.name}</div>
        <div class="src-type">${s.type}${s.url ? ` · <a href="${s.url}" target="_blank" style="color:var(--accent)">link</a>` : ""}</div>
        <div class="src-snippet">${s.snippet}…</div>`;
            list.appendChild(card);
        });
        toggle.addEventListener("click", () => {
            const open = !list.classList.contains("hidden");
            list.classList.toggle("hidden");
            toggle.innerHTML = open ? `📄 View ${sources.length} source${sources.length > 1 ? "s" : ""} ▾` : `📄 Hide sources ▴`;
        });
        bubble.appendChild(toggle);
        bubble.appendChild(list);
    }
    msg.appendChild(avatar);
    msg.appendChild(bubble);
    messagesEl.appendChild(msg);
    scrollToBottom();
}

function showTyping() {
    const id = "typing-" + Date.now();
    const msg = document.createElement("div");
    msg.className = "message bot";
    msg.id = id;
    msg.innerHTML = `<div class="avatar">🤖</div><div class="bubble typing-bubble"><span></span><span></span><span></span></div>`;
    messagesEl.appendChild(msg);
    scrollToBottom();
    return id;
}
function removeTyping(id) { const el = document.getElementById(id); if (el) el.remove(); }
function scrollToBottom() { messagesEl.scrollTop = messagesEl.scrollHeight; }
function formatText(text) {
    return text
        .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
        .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
        .replace(/`(.+?)`/g, "<code>$1</code>")
        .replace(/\n/g, "<br/>");
}
