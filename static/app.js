const messagesEl = document.getElementById("messages");
const questionInput = document.getElementById("question-input");
const sendBtn = document.getElementById("send-btn");
const resetBtn = document.getElementById("reset-btn");

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
        const res = await fetch("/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ question: q }),
        });
        const data = await res.json();
        removeTyping(typingId);
        if (!res.ok) throw new Error(data.error || "Request failed.");
        appendBotResponse(data.answer, data.sources || []);
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
    await fetch("/api/reset", { method: "POST" });
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
            list.classList.toggle("hidden", open);
            toggle.innerHTML = open
                ? `📄 View ${sources.length} source${sources.length > 1 ? "s" : ""} ▾`
                : `📄 Hide sources ▴`;
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
