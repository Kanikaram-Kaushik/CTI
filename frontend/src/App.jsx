import { useEffect, useRef, useState } from "react";

const initialMessage = {
  id: crypto.randomUUID(),
  role: "assistant",
  content:
    "Hello! I am your CTI analyst assistant. Ask about MITRE ATT&CK techniques, threat groups, malware, detections, or mitigations.",
  sources: [],
  owaspRefs: [],
  retrieval: null
};

const suggestions = [
  "What is the T1059 technique?",
  "How can I detect credential dumping?",
  "What techniques does APT28 use?",
  "What are common privilege escalation techniques?",
  "Tell me about Cobalt Strike"
];

const owaspLinks = [
  {
    title: "OWASP Top 10",
    url: "https://owasp.org/www-project-top-ten/"
  },
  {
    title: "OWASP ASVS",
    url: "https://owasp.org/www-project-application-security-verification-standard/"
  },
  {
    title: "OWASP Cheat Sheet Series",
    url: "https://cheatsheetseries.owasp.org/"
  }
];

function buildApiUrl(path) {
  const explicitBase = import.meta.env.VITE_API_BASE;
  if (explicitBase) {
    return `${explicitBase}${path}`;
  }
  if (import.meta.env.DEV) {
    return `http://127.0.0.1:5000${path}`;
  }
  return path;
}

function summarize(text, maxLength = 96) {
  const value = (text || "").trim().replace(/\s+/g, " ");
  if (value.length <= maxLength) return value;
  return `${value.slice(0, maxLength - 1)}…`;
}

function buildHistoryItems(messages) {
  const entries = [];

  for (let index = 0; index < messages.length; index += 2) {
    const userMessage = messages[index];
    const assistantMessage = messages[index + 1];

    if (!userMessage || userMessage.role !== "user") continue;

    entries.push({
      id: `${userMessage.id}-${assistantMessage?.id || index}`,
      question: userMessage.content || "",
      answer: assistantMessage?.content || "",
      sources: assistantMessage?.sources || [],
      retrieval: assistantMessage?.retrieval || null
    });
  }

  return entries.slice(-5).reverse();
}

function Message({ message }) {
  return (
    <article className={`message ${message.role}`}>
      <div className="avatar">{message.role === "user" ? "You" : "CTI"}</div>
      <div className="bubble">
        <p dangerouslySetInnerHTML={{ __html: message.content || "..." }}></p>

        {message.retrieval && (
          <div className="retrieval-meta">
            <strong>Confidence:</strong> {Math.round((message.retrieval.confidence || 0) * 100)}%
            {" "}
            · <strong>Mode:</strong> {message.retrieval.mode}
            {" "}
            · <strong>Status:</strong> {message.retrieval.abstain ? "abstained" : "answered"}
          </div>
        )}

        {message.sources?.length > 0 && (
          <details className="panel">
            <summary>Sources ({message.sources.length})</summary>
            <div className="cards">
              {message.sources.map((s, idx) => (
                <div key={`${s.name}-${idx}`} className="card">
                  <h4>{s.name}</h4>
                  <p className="meta">
                    {s.type}
                    {s.url ? (
                      <>
                        {" "}
                        ·{" "}
                        <a href={s.url} target="_blank" rel="noreferrer noopener">
                          link
                        </a>
                      </>
                    ) : null}
                  </p>
                  <p>{s.snippet}...</p>
                </div>
              ))}
            </div>
          </details>
        )}

        {message.owaspRefs?.length > 0 && (
          <details className="panel">
            <summary>OWASP Guidance ({message.owaspRefs.length})</summary>
            <div className="cards">
              {message.owaspRefs.map((ref, idx) => (
                <div key={`${ref.title}-${idx}`} className="card">
                  <h4>{ref.title}</h4>
                  <p>
                    <a href={ref.url} target="_blank" rel="noreferrer noopener">
                      Open reference
                    </a>
                  </p>
                  <p>{ref.reason}</p>
                </div>
              ))}
            </div>
          </details>
        )}
      </div>
    </article>
  );
}

export default function App() {
  const [messages, setMessages] = useState([initialMessage]);
  const [historyMessages, setHistoryMessages] = useState([]);
  const [question, setQuestion] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [status, setStatus] = useState({ text: "Connecting...", model: "loading..." });
  const [errorText, setErrorText] = useState("");

  const abortControllerRef = useRef(null);
  const bottomRef = useRef(null);

  const loadHistory = async () => {
    try {
      const historyRes = await fetch(buildApiUrl("/api/history"));
      const historyData = await historyRes.json().catch(() => ({ messages: [] }));

      if (Array.isArray(historyData.messages) && historyData.messages.length > 0) {
        setHistoryMessages(buildHistoryItems(historyData.messages));
        if (messages.length <= 1) {
          setMessages(historyData.messages);
        }
      } else {
        setHistoryMessages([]);
      }
    } catch {
      setHistoryMessages([]);
    }
  };

  const loadHistoryConversation = (question) => {
    try {
      const historyRes = fetch(buildApiUrl("/api/history"));
      historyRes
        .then((res) => res.json())
        .then((data) => {
          if (Array.isArray(data.messages) && data.messages.length > 0) {
            setMessages(data.messages);
          }
        })
        .catch(() => {
          setErrorText("Could not load conversation history.");
        });
    } catch {
      setErrorText("Error loading conversation.");
    }
  };

  useEffect(() => {
    const bootstrap = async () => {
      try {
        const statusRes = await fetch(buildApiUrl("/api/status"));

        const data = await statusRes.json();
        setStatus({
          text: data.ready ? "Online - Groq Cloud" : "Connecting...",
          model: data.model || "Groq"
        });

        await loadHistory();
      } catch {
        setStatus({ text: "Backend unavailable", model: "unknown" });
      }
    };

    bootstrap();
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isStreaming]);

  const stopStreaming = () => {
    if (!isStreaming) return;
    abortControllerRef.current?.abort();
    abortControllerRef.current = null;
    setIsStreaming(false);
  };

  const resetChat = async () => {
    try {
      await fetch(buildApiUrl("/api/reset"), { method: "POST" });
    } catch {
      // Keep UI reset even if backend reset fails.
    }
    setMessages([initialMessage]);
    setHistoryMessages([]);
    setErrorText("");
  };

  const sendMessage = async (value) => {
    const q = (value ?? question).trim();
    if (!q || isStreaming) return;

    setErrorText("");
    setQuestion("");
    setIsStreaming(true);

    const userMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: q,
      sources: [],
      owaspRefs: [],
      retrieval: null
    };

    const assistantMessageId = crypto.randomUUID();
    setMessages((prev) => [
      ...prev,
      userMessage,
      {
        id: assistantMessageId,
        role: "assistant",
        content: "",
        sources: [],
        owaspRefs: [],
        retrieval: null
      }
    ]);

    const controller = new AbortController();
    abortControllerRef.current = controller;

    try {
      const response = await fetch(buildApiUrl("/api/chat"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: q }),
        signal: controller.signal
      });

      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload.error || "Request failed.");
      }

      if (!response.body) {
        throw new Error("No response stream returned by backend.");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");

      let buffer = "";
      let fullText = "";
      let sources = [];
      let owaspRefs = [];
      let retrieval = null;

      while (true) {
        const { done, value: chunk } = await reader.read();
        if (done) break;

        buffer += decoder.decode(chunk, { stream: true });
        let boundary = buffer.indexOf("\n\n");

        while (boundary >= 0) {
          const eventBlock = buffer.slice(0, boundary);
          buffer = buffer.slice(boundary + 2);

          const lines = eventBlock
            .split("\n")
            .map((line) => line.trim())
            .filter(Boolean);

          for (const line of lines) {
            if (!line.startsWith("data: ")) continue;
            const payload = line.slice(6).trim();
            if (payload === "[DONE]") continue;

            let parsed;
            try {
              parsed = JSON.parse(payload);
            } catch {
              continue;
            }

            if (parsed.sources) sources = parsed.sources;
            if (parsed.owasp_refs) owaspRefs = parsed.owasp_refs;
            if (parsed.retrieval) retrieval = parsed.retrieval;
            if (parsed.chunk) fullText += parsed.chunk;

            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === assistantMessageId
                  ? {
                      ...msg,
                      content: fullText,
                      sources,
                      owaspRefs,
                      retrieval
                    }
                  : msg
              )
            );
          }

          boundary = buffer.indexOf("\n\n");
        }
      }

      if (!fullText.trim()) {
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantMessageId
              ? {
                  ...msg,
                  content: "I could not generate an answer.",
                  sources,
                  owaspRefs,
                  retrieval
                }
              : msg
          )
        );
      }

      await loadHistory();
    } catch (error) {
      if (error.name !== "AbortError") {
        setErrorText(error.message || "Unexpected error occurred.");
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantMessageId
              ? { ...msg, content: `Error: ${error.message || "Request failed."}` }
              : msg
          )
        );
      }
    } finally {
      setIsStreaming(false);
      abortControllerRef.current = null;
    }
  };

  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="brand">
          <span className="shield">Shield</span>
          <h1>CTI RAG</h1>
        </div>

        <section className="side-block status">
          <h2>Status</h2>
          <p>{status.text}</p>
          <p className="muted">Model: {status.model}</p>
        </section>

        <section className="side-block">
          <h2>Suggestions</h2>
          <div className="stack">
            {suggestions.map((item) => (
              <button
                key={item}
                type="button"
                className="chip"
                onClick={() => sendMessage(item)}
                disabled={isStreaming}
              >
                {item}
              </button>
            ))}
          </div>
        </section>

        <section className="side-block">
          <h2>OWASP References</h2>
          <div className="stack">
            {owaspLinks.map((link) => (
              <a key={link.title} href={link.url} target="_blank" rel="noreferrer noopener">
                {link.title}
              </a>
            ))}
          </div>
        </section>

        <section className="side-block history-panel">
          <h2>Recent Chat History</h2>
          {historyMessages.length > 0 ? (
            <div className="history-list">
              {historyMessages.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  className="history-item"
                  onClick={() => loadHistoryConversation(item.question)}
                  title="Click to load this conversation"
                >
                  <p className="history-question">{summarize(item.question, 110)}</p>
                  <p className="history-answer">{summarize(item.answer, 140) || "No answer saved yet."}</p>
                  <p className="history-meta">
                    {item.sources.length} source{item.sources.length === 1 ? "" : "s"}
                    {item.retrieval?.confidence != null ? ` · ${Math.round((item.retrieval.confidence || 0) * 100)}% confidence` : ""}
                  </p>
                </button>
              ))}
            </div>
          ) : (
            <p className="muted">No saved MongoDB history yet.</p>
          )}
        </section>

        <button type="button" className="reset" onClick={resetChat} disabled={isStreaming}>
          New Chat
        </button>
      </aside>

      <main className="chat-shell">
        <header className="header">
          <h2>Cyber Threat Intelligence Assistant</h2>
          <p>Grounded responses from MITRE ATT&CK with OWASP guidance.</p>
        </header>

        <section className="messages" aria-live="polite">
          {messages.map((message) => (
            <Message key={message.id} message={message} />
          ))}
          {isStreaming && <div className="typing">Streaming response...</div>}
          <div ref={bottomRef} />
        </section>

        <footer className="composer">
          <textarea
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
              }
            }}
            placeholder="Ask about a threat, technique, or mitigation..."
            rows={1}
            disabled={isStreaming}
          />

          <div className="actions">
            <button type="button" onClick={stopStreaming} disabled={!isStreaming}>
              Stop
            </button>
            <button type="button" onClick={() => sendMessage()} disabled={isStreaming || !question.trim()}>
              Send
            </button>
          </div>
        </footer>

        {errorText ? <p className="error">{errorText}</p> : null}
      </main>
    </div>
  );
}
