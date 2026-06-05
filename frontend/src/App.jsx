import { useEffect, useRef, useState } from "react";

// SVGs for nav
const ChatIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"></path>
  </svg>
);

const ShieldIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
  </svg>
);

const SearchIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="11" cy="11" r="8"></circle>
    <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
  </svg>
);

const BugIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="8" y="6" width="8" height="14" rx="4"></rect>
    <path d="M12 2v4"></path>
    <path d="M6 10h2"></path>
    <path d="M16 10h2"></path>
    <path d="M6 14h2"></path>
    <path d="M16 14h2"></path>
    <path d="M6 18h2"></path>
    <path d="M16 18h2"></path>
  </svg>
);

const HistoryIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="12 8 12 12 14 14"></polyline>
    <path d="M3.05 11a9 9 0 1 1 .5 4m-.5 5v-5h5"></path>
  </svg>
);

const TrashIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" width="16" height="16">
    <path d="M3 6h18"></path>
    <path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"></path>
    <path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"></path>
    <line x1="10" y1="11" x2="10" y2="17"></line>
    <line x1="14" y1="11" x2="14" y2="17"></line>
  </svg>
);

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
  for (let index = 0; index < messages.length; index++) {
    const userMessage = messages[index];
    if (userMessage && userMessage.role === "user") {
      const assistantMessage = messages[index + 1];
      entries.push({
        id: `${userMessage.id}-${assistantMessage?.id || index}`,
        question: userMessage.content || "",
        answer: assistantMessage?.content || "",
        sources: assistantMessage?.sources || [],
        retrieval: assistantMessage?.retrieval || null,
        fullConversation: messages.slice(0, index + 2)
      });
    }
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

function MalwareIntelligence() {
  const [malwareInput, setMalwareInput] = useState("");
  const [malwareData, setMalwareData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleScan = async () => {
    if (!malwareInput.trim()) return;
    setLoading(true);
    setError("");
    setMalwareData(null);
    try {
      const response = await fetch(buildApiUrl(`/api/malware/${encodeURIComponent(malwareInput.trim())}`));
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload.error || "Failed to fetch malware data.");
      }
      const data = await response.json();
      setMalwareData(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="vuln-container">
      <div className="vuln-header">
        <h2><ShieldIcon /> Malware Intelligence</h2>
        <p>Retrieve AI-powered threat scoring and defensive strategies for known malware.</p>
      </div>

      <div className="vuln-search-card">
        <h3>Threat Database Query</h3>
        <p>Enter the name of a virus, trojan, or tool (e.g., Emotet, Cobalt Strike) to scan the database.</p>
        <div className="vuln-search-box">
          <input 
            type="text" 
            placeholder="e.g. WannaCry" 
            value={malwareInput}
            onChange={(e) => setMalwareInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleScan()}
          />
          <button onClick={handleScan} disabled={loading || !malwareInput.trim()}>
            {loading ? "Scanning..." : "Scan Database"}
          </button>
        </div>
        {error && <p className="error" style={{marginTop: "12px", padding: 0}}>{error}</p>}
      </div>

      {malwareData && (
        <div className="vuln-result-card">
          <div className="vuln-result-header">
            <div className="vuln-title-group">
              <h2><BugIcon /> {malwareData.id}</h2>
              <span className="severity-badge">{malwareData.severity} THREAT</span>
            </div>
            <div className="cvss-gauge">
              {malwareData.cvss ? malwareData.cvss.toFixed(1) : "N/A"}
              <span>SCORE</span>
            </div>
          </div>
          
          <div className="vuln-details">
            <div className="vuln-section">
              <h4>MALWARE DESCRIPTION</h4>
              <p>{malwareData.description}</p>
            </div>
            <div className="vuln-section">
              <h4>DEFENSE STRATEGY</h4>
              <div className="remediation-box">
                {malwareData.remediation}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function App() {
  const [activeTab, setActiveTab] = useState("chat"); // 'chat' or 'vulnerabilities'
  
  const [currentSessionId, setCurrentSessionId] = useState(() => crypto.randomUUID());
  const [messages, setMessages] = useState([initialMessage]);
  const [historyMessages, setHistoryMessages] = useState([]);
  const [question, setQuestion] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [status, setStatus] = useState({ text: "Connecting...", model: "loading..." });
  const [errorText, setErrorText] = useState("");

  const abortControllerRef = useRef(null);
  const bottomRef = useRef(null);

  const saveHistoryToLocal = (msgs) => {
    setHistoryMessages(buildHistoryItems(msgs));
  };

  const loadHistory = async () => {
    try {
      const response = await fetch(buildApiUrl("/api/history"));
      if (response.ok) {
        const data = await response.json();
        const sessions = data.sessions || {};
        
        const newHistoryItems = [];
        for (const [sid, msgs] of Object.entries(sessions)) {
          if (msgs.length === 0) continue;
          
          const formatted = msgs.map((msg, i) => ({
            id: `db-${sid}-${i}`,
            role: msg.role,
            content: msg.content,
            sources: [],
            owaspRefs: [],
            retrieval: null
          }));
          const fullMsgs = [initialMessage, ...formatted];
          
          const userMsg = formatted.find(m => m.role === 'user');
          const assistantMsg = formatted.find(m => (m.role === 'ai' || m.role === 'assistant') && m !== initialMessage);
          
          newHistoryItems.push({
            id: sid,
            question: userMsg ? userMsg.content : "New Conversation",
            answer: assistantMsg ? assistantMsg.content : "",
            sources: [],
            retrieval: null,
            fullConversation: fullMsgs,
            timestamp: msgs[0].timestamp
          });
        }
        
        newHistoryItems.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
        setHistoryMessages(newHistoryItems.slice(0, 15));
      }
    } catch {
      setHistoryMessages([]);
    }
  };

  const loadHistoryConversation = (sid, msgs) => {
    setCurrentSessionId(sid);
    setMessages(msgs);
  };

  const deleteSession = async (e, sid) => {
    e.stopPropagation();
    try {
      const response = await fetch(buildApiUrl(`/api/history/${sid}`), {
        method: "DELETE"
      });
      if (response.ok) {
        await loadHistory();
        if (currentSessionId === sid) {
          resetChat();
        }
      }
    } catch (err) {
      console.error("Failed to delete session", err);
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
    if (activeTab === "chat") {
      bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, isStreaming, activeTab]);

  const stopStreaming = () => {
    if (!isStreaming) return;
    abortControllerRef.current?.abort();
    abortControllerRef.current = null;
    setIsStreaming(false);
  };

  const resetChat = () => {
    setCurrentSessionId(crypto.randomUUID());
    setMessages([initialMessage]);
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
    let updatedMessages = [
      ...messages,
      userMessage,
      {
        id: assistantMessageId,
        role: "assistant",
        content: "",
        sources: [],
        owaspRefs: [],
        retrieval: null
      }
    ];
    setMessages(updatedMessages);

    const controller = new AbortController();
    abortControllerRef.current = controller;

    try {
      const response = await fetch(buildApiUrl("/api/chat"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: q, session_id: currentSessionId }),
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

            updatedMessages = updatedMessages.map((msg) =>
              msg.id === assistantMessageId
                ? {
                    ...msg,
                    content: fullText,
                    sources,
                    owaspRefs,
                    retrieval
                  }
                : msg
            );
            setMessages(updatedMessages);
          }
          boundary = buffer.indexOf("\n\n");
        }
      }

      if (!fullText.trim()) {
        updatedMessages = updatedMessages.map((msg) =>
          msg.id === assistantMessageId
            ? {
                ...msg,
                content: "I could not generate an answer.",
                sources,
                owaspRefs,
                retrieval
              }
            : msg
        );
        setMessages(updatedMessages);
      }
      
      saveHistoryToLocal(updatedMessages);
      await loadHistory();

    } catch (error) {
      if (error.name !== "AbortError") {
        setErrorText(error.message || "Unexpected error occurred.");
        updatedMessages = updatedMessages.map((msg) =>
          msg.id === assistantMessageId
            ? { ...msg, content: `Error: ${error.message || "Request failed."}` }
            : msg
        );
        setMessages(updatedMessages);
        saveHistoryToLocal(updatedMessages);
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

        <nav className="nav-menu">
          <button 
            className={`nav-item ${activeTab === 'chat' ? 'active' : ''}`}
            onClick={() => setActiveTab('chat')}
          >
            <ChatIcon /> Threat Intelligence
          </button>
          <button 
            className={`nav-item ${activeTab === 'vulnerabilities' ? 'active' : ''}`}
            onClick={() => setActiveTab('vulnerabilities')}
          >
            <ShieldIcon /> Malware Intelligence
          </button>
        </nav>

        {activeTab === 'chat' && (
          <>
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
              <h2><HistoryIcon /> Recent History (Database)</h2>
              {historyMessages.length > 0 ? (
                <div className="history-list">
                  {historyMessages.map((item) => (
                    <button
                      key={item.id}
                      type="button"
                      className={`history-item ${item.id === currentSessionId ? 'active-session' : ''}`}
                      onClick={() => loadHistoryConversation(item.id, item.fullConversation)}
                      title="Click to load this conversation"
                    >
                      <div className="history-header">
                        <p className="history-question">{summarize(item.question, 110)}</p>
                        <button 
                          className="delete-session-btn" 
                          onClick={(e) => deleteSession(e, item.id)}
                          title="Delete this chat"
                        >
                          <TrashIcon />
                        </button>
                      </div>
                      <p className="history-answer">{summarize(item.answer, 140) || "No answer saved yet."}</p>
                      <p className="history-meta">
                        {item.sources.length} source{item.sources.length === 1 ? "" : "s"}
                        {item.retrieval?.confidence != null ? ` · ${Math.round((item.retrieval.confidence || 0) * 100)}% confidence` : ""}
                      </p>
                    </button>
                  ))}
                </div>
              ) : (
                <p className="muted">No saved database history yet.</p>
              )}
            </section>

            <button type="button" className="reset" onClick={resetChat} disabled={isStreaming}>
              New Chat
            </button>
          </>
        )}
      </aside>

      <main className="chat-shell">
        {activeTab === 'vulnerabilities' ? (
          <MalwareIntelligence />
        ) : (
          <>
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
          </>
        )}
      </main>
    </div>
  );
}
