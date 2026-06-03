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
      retrieval: assistantMessage?.retrieval || null,
      fullConversation: messages.slice(0, index + 2)
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

function VulnerabilityIntelligence() {
  const [cveInput, setCveInput] = useState("");
  const [cveData, setCveData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleScan = async () => {
    if (!cveInput.trim()) return;
    setLoading(true);
    setError("");
    setCveData(null);
    try {
      const response = await fetch(buildApiUrl(`/api/cve/${cveInput.trim().toUpperCase()}`));
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload.error || "Failed to fetch CVE data.");
      }
      const data = await response.json();
      setCveData(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="vuln-container">
      <div className="vuln-header">
        <h2><ShieldIcon /> Vulnerability Intelligence</h2>
        <p>Retrieve detailed threat intelligence, CVSS scoring, and mitigations.</p>
      </div>

      <div className="vuln-search-card">
        <h3>CVE Database Query</h3>
        <p>Enter a valid CVE identifier (e.g., CVE-2024-3400) to scan the database.</p>
        <div className="vuln-search-box">
          <input 
            type="text" 
            placeholder="CVE-2024-3400" 
            value={cveInput}
            onChange={(e) => setCveInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleScan()}
          />
          <button onClick={handleScan} disabled={loading || !cveInput.trim()}>
            {loading ? "Scanning..." : "Scan Database"}
          </button>
        </div>
        {error && <p className="error" style={{marginTop: "12px", padding: 0}}>{error}</p>}
      </div>

      {cveData && (
        <div className="vuln-result-card">
          <div className="vuln-result-header">
            <div className="vuln-title-group">
              <h2><BugIcon /> {cveData.id}</h2>
              <span className="severity-badge">{cveData.severity} SEVERITY</span>
            </div>
            <div className="cvss-gauge">
              {cveData.cvss ? cveData.cvss.toFixed(1) : "N/A"}
              <span>CVSS</span>
            </div>
          </div>
          
          <div className="vuln-details">
            <div className="vuln-section">
              <h4>VULNERABILITY DESCRIPTION</h4>
              <p>{cveData.description}</p>
            </div>
            <div className="vuln-section">
              <h4>REMEDIATION</h4>
              <div className="remediation-box">
                {cveData.remediation}
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
  
  const [messages, setMessages] = useState([initialMessage]);
  const [historyMessages, setHistoryMessages] = useState([]);
  const [question, setQuestion] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [status, setStatus] = useState({ text: "Connecting...", model: "loading..." });
  const [errorText, setErrorText] = useState("");

  const abortControllerRef = useRef(null);
  const bottomRef = useRef(null);

  const saveHistoryToLocal = (msgs) => {
    try {
      localStorage.setItem("cti_chat_history", JSON.stringify(msgs));
      setHistoryMessages(buildHistoryItems(msgs));
    } catch (e) {
      console.error("Failed to save history", e);
    }
  };

  const loadHistory = async () => {
    try {
      const stored = localStorage.getItem("cti_chat_history");
      if (stored) {
        const parsed = JSON.parse(stored);
        if (Array.isArray(parsed) && parsed.length > 0) {
          if (messages.length <= 1) {
            setMessages(parsed);
          }
          setHistoryMessages(buildHistoryItems(parsed));
        }
      }
    } catch {
      setHistoryMessages([]);
    }
  };

  const loadHistoryConversation = (msgs) => {
    setMessages(msgs);
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

  const resetChat = async () => {
    try {
      await fetch(buildApiUrl("/api/reset"), { method: "POST" });
    } catch {
      // Keep UI reset even if backend reset fails.
    }
    setMessages([initialMessage]);
    localStorage.removeItem("cti_chat_history");
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
            <ShieldIcon /> Vulnerability Intelligence
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
              <h2><HistoryIcon /> Recent History (Local)</h2>
              {historyMessages.length > 0 ? (
                <div className="history-list">
                  {historyMessages.map((item) => (
                    <button
                      key={item.id}
                      type="button"
                      className="history-item"
                      onClick={() => loadHistoryConversation(item.fullConversation)}
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
                <p className="muted">No saved local history yet.</p>
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
          <VulnerabilityIntelligence />
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
