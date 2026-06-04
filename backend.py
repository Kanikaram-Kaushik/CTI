import os
import re
import socket
import json
import math
import threading
from collections import Counter
from datetime import datetime, timezone
from flask import Flask, request, jsonify, send_from_directory, Response, stream_with_context
from flask_cors import CORS
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from dotenv import load_dotenv
import requests

load_dotenv()

# ── Config ─────────────────────────────────────────────
GROQ_API_KEY    = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL      = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
BASE_DIR        = os.path.dirname(os.path.abspath(__file__))
FAISS_PATH      = os.path.join(BASE_DIR, "faiss_index")
FRONTEND_DIST   = os.path.join(BASE_DIR, "frontend", "dist")

app = Flask(
    __name__,
    static_folder=os.path.join(FRONTEND_DIST, "assets"),
    static_url_path="/assets",
)
CORS(app)

chat_history = []
retriever    = None
chain        = None
llm_mode     = "groq"
vector_store = None
attack_id_map = {}
intrusion_set_map = {}
_startup_lock = threading.Lock()
_startup_done = False

LOCAL_STIX_FILE = os.path.join(BASE_DIR, "data", "enterprise-attack.json")

MIN_RELEVANCE_SCORE = 0.15
# Only answer when the retrieval confidence is strong enough to avoid guessing.
ABSTAIN_CONFIDENCE_THRESHOLD = 0.35

hybrid_index_docs = []
hybrid_term_freqs = []
hybrid_doc_freq = {}

OWASP_BASE_REFS = [
    {
        "title": "OWASP Top 10",
        "url": "https://owasp.org/www-project-top-ten/",
        "reason": "Primary web application risk categories and defensive priorities.",
    },
    {
        "title": "OWASP ASVS",
        "url": "https://owasp.org/www-project-application-security-verification-standard/",
        "reason": "Structured verification checklist for secure design and implementation.",
    },
    {
        "title": "OWASP Cheat Sheet Series",
        "url": "https://cheatsheetseries.owasp.org/",
        "reason": "Practical secure coding and hardening guidance.",
    },
]


def _get_owasp_refs(question):
    """Return OWASP references relevant to the current CTI query."""
    q = question.lower()
    refs = []

    def add_ref(title, url, reason):
        if not any(r["url"] == url for r in refs):
            refs.append({"title": title, "url": url, "reason": reason})

    if any(tok in q for tok in ["credential", "password", "auth", "login", "session", "token"]):
        add_ref(
            "A07:2021 Identification and Authentication Failures",
            "https://owasp.org/Top10/A07_2021-Identification_and_Authentication_Failures/",
            "Helpful when discussing credential abuse, authentication bypass, and session risks.",
        )
        add_ref(
            "Authentication Cheat Sheet",
            "https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html",
            "Actionable controls for authentication and account defense.",
        )

    if any(tok in q for tok in ["injection", "command", "sql", "xss", "script"]):
        add_ref(
            "A03:2021 Injection",
            "https://owasp.org/Top10/A03_2021-Injection/",
            "Relevant to command, script, and input-based exploitation patterns.",
        )
        add_ref(
            "Input Validation Cheat Sheet",
            "https://cheatsheetseries.owasp.org/cheatsheets/Input_Validation_Cheat_Sheet.html",
            "Guidance to reduce injection and malformed-input attack paths.",
        )

    if any(tok in q for tok in ["logging", "monitor", "detect", "detection", "incident", "response"]):
        add_ref(
            "A09:2021 Security Logging and Monitoring Failures",
            "https://owasp.org/Top10/A09_2021-Security_Logging_and_Monitoring_Failures/",
            "Useful for mapping CTI detections to stronger monitoring controls.",
        )
        add_ref(
            "Logging Cheat Sheet",
            "https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html",
            "Operational guidance for high-value security telemetry.",
        )

    if any(tok in q for tok in ["api", "service", "backend", "microservice"]):
        add_ref(
            "OWASP API Security Top 10",
            "https://owasp.org/www-project-api-security/",
            "Complements ATT&CK tactics with API-specific risk coverage.",
        )

    if not refs:
        for ref in OWASP_BASE_REFS:
            add_ref(ref["title"], ref["url"], ref["reason"])

    return refs[:4]



def _try_groq():
    """Try to initialise the Groq cloud LLM. Returns the LLM or None."""
    if not GROQ_API_KEY:
        return None
    if not GROQ_API_KEY.startswith("gsk_"):
        print("Groq API key format looks invalid. Groq keys usually start with 'gsk_'.")
        return None
    try:
        from langchain_groq import ChatGroq
        llm = ChatGroq(
            model=GROQ_MODEL,
            temperature=0.3,
            max_tokens=4096,
            groq_api_key=GROQ_API_KEY,
        )
        llm.invoke("ping")
        return llm
    except Exception as e:
        print(f"Groq unavailable ({e})")
        return None


def _is_offline():
    """Quick check: can we resolve huggingface.co?"""
    try:
        socket.create_connection(("huggingface.co", 443), timeout=3)
        return False
    except OSError:
        return True




def _tokenize(text):
    return re.findall(r"[a-z0-9]+", text.lower())


def _build_hybrid_index():
    """Build lightweight lexical index from FAISS docstore for hybrid retrieval."""
    global hybrid_index_docs, hybrid_term_freqs, hybrid_doc_freq
    hybrid_index_docs = []
    hybrid_term_freqs = []
    hybrid_doc_freq = {}

    if vector_store is None:
        return

    doc_items = getattr(getattr(vector_store, "docstore", None), "_dict", {})
    if not doc_items:
        return

    for doc in doc_items.values():
        if not isinstance(doc, Document):
            continue

        tokens = _tokenize(doc.page_content)
        if not tokens:
            continue

        tf = Counter(tokens)
        hybrid_index_docs.append(doc)
        hybrid_term_freqs.append(tf)

        for term in tf.keys():
            hybrid_doc_freq[term] = hybrid_doc_freq.get(term, 0) + 1


def _lexical_search(question, k=8):
    """Simple BM25-like lexical retrieval over in-memory document chunks."""
    if not hybrid_index_docs:
        return []

    q_terms = _tokenize(question)
    if not q_terms:
        return []

    n_docs = len(hybrid_index_docs)
    scored = []

    for idx, tf in enumerate(hybrid_term_freqs):
        score = 0.0
        overlap_terms = 0
        for term in q_terms:
            term_tf = tf.get(term, 0)
            if term_tf <= 0:
                continue
            overlap_terms += 1
            df = hybrid_doc_freq.get(term, 0)
            idf = math.log((n_docs + 1) / (df + 1)) + 1.0
            score += (term_tf / (term_tf + 1.2)) * idf

        if score > 0:
            # Small overlap reward helps rerank exact-mention chunks higher.
            overlap_ratio = overlap_terms / max(len(set(q_terms)), 1)
            score += 0.2 * overlap_ratio
            scored.append((hybrid_index_docs[idx], score))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:k]


def _doc_key(doc):
    md = doc.metadata or {}
    return (
        md.get("id", ""),
        md.get("name", ""),
        md.get("type", ""),
        md.get("url", ""),
        hash(doc.page_content[:180]),
    )


def _normalize_scores(values):
    if not values:
        return []
    max_val = max(values)
    if max_val <= 0:
        return [0.0 for _ in values]
    return [v / max_val for v in values]


def _hybrid_retrieve(question, dense_k=8, lexical_k=8, final_k=4):
    """
    Hybrid retrieval: FAISS dense retrieval + lexical retrieval + weighted rerank.
    Returns ranked list of dicts with document and score components.
    """
    dense = _retrieve_with_relevance(question, k=dense_k)
    lexical = _lexical_search(question, k=lexical_k)

    dense_map = {}
    for doc, score in dense:
        dense_map[_doc_key(doc)] = (doc, max(score or 0.0, 0.0))

    lexical_map = {}
    for doc, score in lexical:
        lexical_map[_doc_key(doc)] = (doc, max(score, 0.0))

    dense_norm_vals = _normalize_scores([v[1] for v in dense_map.values()])
    lexical_norm_vals = _normalize_scores([v[1] for v in lexical_map.values()])

    dense_norm = {}
    for key, norm in zip(dense_map.keys(), dense_norm_vals):
        dense_norm[key] = norm

    lexical_norm = {}
    for key, norm in zip(lexical_map.keys(), lexical_norm_vals):
        lexical_norm[key] = norm

    q_terms = set(_tokenize(question))
    candidates = []
    for key in set(dense_map.keys()) | set(lexical_map.keys()):
        doc = (dense_map.get(key) or lexical_map.get(key))[0]
        d_score = dense_norm.get(key, 0.0)
        l_score = lexical_norm.get(key, 0.0)
        doc_terms = set(_tokenize(doc.page_content))
        overlap = (len(q_terms & doc_terms) / max(len(q_terms), 1)) if q_terms else 0.0

        hybrid_score = (0.60 * d_score) + (0.30 * l_score) + (0.10 * overlap)
        candidates.append(
            {
                "doc": doc,
                "hybrid_score": hybrid_score,
                "dense_score": d_score,
                "lexical_score": l_score,
                "overlap": overlap,
            }
        )

    candidates.sort(key=lambda x: x["hybrid_score"], reverse=True)
    return candidates[:final_k]


def _compute_confidence(question, source_docs, ranked_items, force_allow=False):
    """Compute confidence and abstain decision with user-facing reasons."""
    reasons = []
    if not source_docs or not ranked_items:
        return {
            "confidence": 0.0,
            "abstain": True,
            "reasons": ["No supporting MITRE context was retrieved for this question."],
            "top_hybrid_score": 0.0,
            "top_dense_score": 0.0,
            "top_lexical_score": 0.0,
        }

    top = ranked_items[0]
    top_hybrid = float(top.get("hybrid_score", 0.0))
    top_dense = float(top.get("dense_score", 0.0))
    top_lexical = float(top.get("lexical_score", 0.0))

    # Confidence factors: retrieval strength + evidence count + entity mention signal.
    evidence_factor = min(len(source_docs) / 4.0, 1.0)
    entity_factor = 1.0 if re.search(r"\b(apt\s*\d+|t\d{4}(?:\.\d{3})?)\b", question, re.IGNORECASE) else 0.0

    confidence = (0.55 * top_hybrid) + (0.30 * evidence_factor) + (0.15 * entity_factor)
    confidence = max(0.0, min(confidence, 1.0))

    if top_hybrid >= 0.55:
        reasons.append("Top hybrid retrieval score is strong.")
    elif top_hybrid >= 0.35:
        reasons.append("Top hybrid retrieval score is moderate.")
    else:
        reasons.append("Top hybrid retrieval score is weak.")

    reasons.append(f"Retrieved {len(source_docs)} supporting MITRE chunk(s).")
    if entity_factor > 0:
        reasons.append("Query includes an explicit ATT&CK entity pattern (APT/T-ID).")

    abstain = (confidence < ABSTAIN_CONFIDENCE_THRESHOLD) and not force_allow
    if abstain:
        reasons.append("Confidence below abstain threshold, returning safe abstention.")

    return {
        "confidence": round(confidence, 3),
        "abstain": abstain,
        "reasons": reasons,
        "top_hybrid_score": round(top_hybrid, 3),
        "top_dense_score": round(top_dense, 3),
        "top_lexical_score": round(top_lexical, 3),
    }


def _retrieve_with_relevance(question, k=5):
    """Retrieve documents with relevance scores (0..1)."""
    if vector_store is None:
        return []
    try:
        return vector_store.similarity_search_with_relevance_scores(question, k=k)
    except Exception:
        docs = retriever.invoke(question)
        return [(doc, None) for doc in docs]


def _expand_query_for_retrieval(question):
    """Expand short MITRE entity queries to improve strict-RAG retrieval recall."""
    q = question.strip()
    q_lower = q.lower()

    apt_match = re.search(r"\bapt\s*\d+\b", q_lower)
    if apt_match:
        apt_label = apt_match.group(0).upper().replace(" ", "")
        mapped_name = intrusion_set_map.get(apt_label, {}).get("name", apt_label)
        return (
            f"MITRE ATT&CK intrusion set {mapped_name} threat group "
            f"tactics techniques malware tools detections mitigations"
        )

    if re.fullmatch(r"t\d{4}(?:\.\d{3})?", q_lower):
        t_id = q.upper()
        mapped_name = attack_id_map.get(t_id, {}).get("name", "")
        return (
            f"MITRE ATT&CK technique {t_id} {mapped_name} description "
            f"detection mitigation procedure examples"
        )

    if len(q_lower.split()) <= 2:
        return f"MITRE ATT&CK {q} technique tactic threat group malware detection mitigation"

    return question


def _load_attack_id_map():
    """Load ATT&CK technique ID -> document info from local MITRE STIX JSON."""
    mapping = {}
    if not os.path.exists(LOCAL_STIX_FILE):
        return mapping

    try:
        with open(LOCAL_STIX_FILE, "r", encoding="utf-8") as f:
            stix_data = json.load(f)
        for obj in stix_data.get("objects", []):
            if obj.get("type") != "attack-pattern":
                continue

            ext_refs = obj.get("external_references", [])
            ext_id = ""
            ext_url = ""
            for ref in ext_refs:
                candidate = ref.get("external_id", "")
                if re.fullmatch(r"T\d{4}(?:\.\d{3})?", candidate):
                    ext_id = candidate.upper()
                    ext_url = ref.get("url", "")
                    break

            if not ext_id:
                continue

            name = obj.get("name", "Unknown")
            description = obj.get("description", "")
            content = f"Name: {name}\nType: attack-pattern\nATT&CK ID: {ext_id}\nDescription: {description}"
            mapping[ext_id] = {
                "name": name,
                "url": ext_url,
                "content": content,
            }
    except Exception as e:
        print(f"Warning: failed to build ATT&CK ID map ({e})")

    return mapping


def _load_intrusion_set_map():
    """Load intrusion-set name map, keyed by compact name (e.g., APT28)."""
    mapping = {}
    if not os.path.exists(LOCAL_STIX_FILE):
        return mapping

    try:
        with open(LOCAL_STIX_FILE, "r", encoding="utf-8") as f:
            stix_data = json.load(f)
        for obj in stix_data.get("objects", []):
            if obj.get("type") != "intrusion-set":
                continue

            name = obj.get("name", "Unknown")
            compact = re.sub(r"\s+", "", name.upper())
            ext_url = ""
            for ref in obj.get("external_references", []):
                if ref.get("source_name") == "mitre-attack":
                    ext_url = ref.get("url", "")
                    break

            description = obj.get("description", "")
            content = f"Name: {name}\nType: intrusion-set\nDescription: {description}"
            mapping[compact] = {
                "name": name,
                "url": ext_url,
                "content": content,
            }
    except Exception as e:
        print(f"Warning: failed to build intrusion-set map ({e})")

    return mapping


def _convert_markdown_to_html(text):
    """Convert markdown formatting (**bold**, ***bold-italic***, *italic*) to HTML tags."""
    # Order matters: process bold-italic first, then bold, then italic
    # Bold-italic: ***text***
    text = re.sub(r'\*\*\*(.+?)\*\*\*', r'<strong><em>\1</em></strong>', text)
    # Bold: **text**
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    # Italic: *text* (but not already processed)
    text = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'<em>\1</em>', text)
    return text


def _normalize(s):
    return re.sub(r"\s+", "", s.lower())


def load_chain():
    global retriever, chain, llm_mode, vector_store, attack_id_map, intrusion_set_map
    print("Loading FAISS index...")

    cache_dir = os.path.expanduser("~/.cache/huggingface/hub")
    
    try:
        embeddings = HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL,
            cache_folder=cache_dir,
            show_progress=True,
        )
        
        faiss_file = os.path.join(FAISS_PATH, "index.faiss")
        if os.path.exists(faiss_file) and os.path.getsize(faiss_file) < 1000:
            print("Detected Git LFS pointers for FAISS. Downloading actual binaries...")
            import requests
            base_url = "https://huggingface.co/spaces/Kaushik-17/CTI_RAG_chatbot/resolve/main/faiss_index/"
            try:
                for fname in ["index.faiss", "index.pkl"]:
                    resp = requests.get(base_url + fname)
                    resp.raise_for_status()
                    with open(os.path.join(FAISS_PATH, fname), "wb") as f:
                        f.write(resp.content)
                print("Successfully downloaded FAISS binaries.")
            except Exception as e:
                print(f"Warning: Failed to download FAISS binaries: {e}")

        vector_store = FAISS.load_local(FAISS_PATH, embeddings, allow_dangerous_deserialization=True)
        retriever    = vector_store.as_retriever(search_kwargs={"k": 5})
        _build_hybrid_index()
    except Exception as e:
        print(f"\n✗ WARNING: Failed to load embeddings or FAISS index: {e}")
        print("Backend will continue to run, but retrieval may be degraded or disabled.")
    if not os.path.exists(LOCAL_STIX_FILE):
        print("Downloading MITRE ATT&CK STIX data...")
        os.makedirs(os.path.dirname(LOCAL_STIX_FILE), exist_ok=True)
        try:
            resp = requests.get("https://raw.githubusercontent.com/mitre/cti/master/enterprise-attack/enterprise-attack.json", timeout=30)
            resp.raise_for_status()
            with open(LOCAL_STIX_FILE, "wb") as f:
                f.write(resp.content)
            print("Downloaded enterprise-attack.json successfully.")
        except Exception as e:
            print(f"Warning: Failed to download STIX data: {e}")

    attack_id_map = _load_attack_id_map()
    intrusion_set_map = _load_intrusion_set_map()
    print(f"Hybrid lexical chunks indexed: {len(hybrid_index_docs)}")
    print(f"Loaded ATT&CK technique map entries: {len(attack_id_map)}")
    print(f"Loaded intrusion-set map entries: {len(intrusion_set_map)}")

    llm = _try_groq()
    if llm is None:
        raise RuntimeError(
            "No Groq LLM available. Set GROQ_API_KEY and ensure Groq is reachable."
        )

    print(f"Using Groq cloud LLM ({GROQ_MODEL}) [ok]")

    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "You are a strict cybersecurity-only assistant.\n"
         "1. Answer the user's question using ONLY the provided Retrieved Context.\n"
         "2. If the answer cannot be found in the context, do not guess or make up information. Instead, state that you do not have enough information to answer.\n"
         "3. Keep the response clear, concise, and helpful.\n\n"
         "Retrieved Context:\n{context}"),
        ("human", "Question: {question}"),
    ])

    chain = prompt | llm | StrOutputParser()
    print("Chain ready [ok]")


def ensure_startup():
    """Run one-time startup for production servers (e.g., gunicorn workers)."""
    global _startup_done
    if _startup_done:
        return

    with _startup_lock:
        if _startup_done:
            return
        load_chain()
        _startup_done = True


@app.route("/")
def index():
    if not os.path.exists(os.path.join(FRONTEND_DIST, "index.html")):
        return jsonify(
            {
                "error": (
                    "React frontend build not found. Run 'npm install' and "
                    "'npm run build' inside the frontend folder."
                )
            }
        ), 503
    return send_from_directory(FRONTEND_DIST, "index.html")


@app.route("/<path:path>")
def serve_frontend(path):
    # Let API routes and static assets keep their own handlers.
    if path.startswith("api/") or path.startswith("assets/"):
        return jsonify({"error": "Not found"}), 404

    target = os.path.join(FRONTEND_DIST, path)
    if os.path.exists(target) and os.path.isfile(target):
        return send_from_directory(FRONTEND_DIST, path)

    if os.path.exists(os.path.join(FRONTEND_DIST, "index.html")):
        return send_from_directory(FRONTEND_DIST, "index.html")

    return jsonify({"error": "Frontend build not found."}), 503


@app.route("/api/chat", methods=["POST"])
def chat():
    global chat_history
    if chain is None:
        return jsonify({"error": "Backend not ready. Please wait a moment."}), 503

    data     = request.json or {}
    question = data.get("question", "").strip()
    if not question:
        return jsonify({"error": "Question cannot be empty."}), 400



    question_for_llm = question
    retrieval_query = _expand_query_for_retrieval(question)

    try:
        ranked_results = _hybrid_retrieve(retrieval_query, dense_k=8, lexical_k=8, final_k=4)
        source_docs = [item["doc"] for item in ranked_results] if ranked_results else []

        allow_low_score = False
        technique_match = re.search(r"\b(T\d{4}(?:\.\d{3})?)\b", question.upper())
        if technique_match:
            t_id = technique_match.group(1)
            if t_id in attack_id_map:
                allow_low_score = True
                exact = attack_id_map[t_id]
                exact_doc = Document(
                    page_content=exact["content"],
                    metadata={
                        "name": exact["name"],
                        "type": "attack-pattern",
                        "url": exact.get("url", ""),
                    },
                )
                source_docs = [exact_doc] + source_docs

        apt_matches = re.findall(r"\bAPT\s*\d+\b", question.upper())
        if apt_matches:
            normalized_targets = {_normalize(a) for a in apt_matches}
            for target in normalized_targets:
                if target.upper() in intrusion_set_map:
                    exact = intrusion_set_map[target.upper()]
                    exact_doc = Document(
                        page_content=exact["content"],
                        metadata={
                            "name": exact["name"],
                            "type": "intrusion-set",
                            "url": exact.get("url", ""),
                        },
                    )
                    source_docs = [exact_doc] + source_docs
                    allow_low_score = True
                    break

            if any(_normalize(d.metadata.get("name", "")) in normalized_targets for d in source_docs):
                allow_low_score = True

        top_dense_score = ranked_results[0].get("dense_score", 0.0) if ranked_results else 0.0
        threshold = 0.15
        if top_dense_score < threshold and not allow_low_score:
            source_docs = []

        confidence_meta = _compute_confidence(
            question=question,
            source_docs=source_docs,
            ranked_items=ranked_results,
            force_allow=allow_low_score,
        )

        sources = [
            {
                "name":    d.metadata.get("name", "Unknown"),
                "type":    d.metadata.get("type", ""),
                "url":     d.metadata.get("url", ""),
                "snippet": d.page_content[:250],
            }
            for d in source_docs
        ]
        context_text = "\n\n".join(d.page_content for d in source_docs)
        owasp_refs = _get_owasp_refs(question)
        
        def generate():
            yield f"data: {json.dumps({'sources': sources})}\n\n"
            yield f"data: {json.dumps({'owasp_refs': owasp_refs})}\n\n"
            yield f"data: {json.dumps({'retrieval': {'mode': 'hybrid_dense_lexical', **confidence_meta}})}\n\n"

            if not source_docs or confidence_meta["abstain"]:
                abstain_reason = confidence_meta["reasons"][-1] if confidence_meta["reasons"] else "Low retrieval confidence."
                yield f"data: {json.dumps({'chunk': f'I cannot answer this with enough confidence from the available MITRE ATT&CK sources ({abstain_reason}). Please ask a more specific MITRE technique, tactic, group, malware, tool, detection, or mitigation question.'})}\n\n"
                yield "data: [DONE]\n\n"
                return
            
            full_answer = ""
            for chunk in chain.stream({"question": question_for_llm, "context": context_text}):
                if "<think>" in chunk or "</think>" in chunk:
                    continue
                full_answer += chunk
                # Convert markdown to HTML before sending
                html_chunk = _convert_markdown_to_html(chunk)
                yield f"data: {json.dumps({'chunk': html_chunk})}\n\n"

            if not full_answer.strip():
                yield f"data: {json.dumps({'chunk': 'I could not generate an answer.'})}\n\n"

            chat_history.append(HumanMessage(content=question))
            chat_history.append(AIMessage(content=full_answer.strip()))
            yield "data: [DONE]\n\n"
            
        return Response(stream_with_context(generate()), mimetype='text/event-stream')
    except Exception as e:
        print(f"Chat error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/reset", methods=["POST"])
def reset():
    global chat_history
    chat_history = []
    return jsonify({"status": "reset"})


@app.route("/api/status")
def status():
    """Return current LLM mode so the frontend can display it."""
    return jsonify({
        "mode": llm_mode,
        "model": GROQ_MODEL,
        "retrieval": "hybrid_dense_lexical",
        "history": "local-storage",
        "ready": chain is not None,
    })


@app.route("/api/cve/<cve_id>", methods=["GET"])
def get_cve(cve_id):
    try:
        # MITRE API is fast and doesn't require a key
        url = f"https://cveawg.mitre.org/api/cve/{cve_id}"
        resp = requests.get(url, timeout=10)
        
        if resp.status_code != 200:
            # Fallback to NVD if MITRE fails or doesn't have it
            nvd_url = f"https://services.nvd.nist.gov/rest/json/cves/2.0?cveId={cve_id}"
            nvd_resp = requests.get(nvd_url, timeout=15)
            if nvd_resp.status_code != 200:
                return jsonify({"error": "CVE not found or API unavailable"}), 404
            
            nvd_data = nvd_resp.json()
            if not nvd_data.get("vulnerabilities"):
                return jsonify({"error": "CVE not found in NVD"}), 404
                
            cve_item = nvd_data["vulnerabilities"][0]["cve"]
            descriptions = cve_item.get("descriptions", [])
            desc = next((d["value"] for d in descriptions if d["lang"] == "en"), "No description available.")
            
            metrics = cve_item.get("metrics", {})
            severity = "UNKNOWN"
            score = 0.0
            
            if "cvssMetricV31" in metrics:
                cvss_data = metrics["cvssMetricV31"][0]["cvssData"]
                severity = cvss_data.get("baseSeverity", "UNKNOWN")
                score = cvss_data.get("baseScore", 0.0)
            elif "cvssMetricV30" in metrics:
                cvss_data = metrics["cvssMetricV30"][0]["cvssData"]
                severity = cvss_data.get("baseSeverity", "UNKNOWN")
                score = cvss_data.get("baseScore", 0.0)
            elif "cvssMetricV2" in metrics:
                cvss_data = metrics["cvssMetricV2"][0]["cvssData"]
                severity = metrics["cvssMetricV2"][0].get("baseSeverity", "UNKNOWN")
                score = cvss_data.get("baseScore", 0.0)
                
            remediation = "Apply latest vendor patches. Monitor network traffic for anomalous behavior targeting this vulnerability."
            
            return jsonify({
                "id": cve_id,
                "description": desc,
                "severity": severity,
                "cvss": score,
                "remediation": remediation,
            })
            
        data = resp.json()
        containers = data.get("containers", {})
        cna = containers.get("cna", {})
        
        descriptions = cna.get("descriptions", [])
        desc = next((d["value"] for d in descriptions if d["lang"] == "en"), "No description available.")
        
        metrics = cna.get("metrics", [])
        severity = "UNKNOWN"
        score = 0.0
        
        for metric in metrics:
            if "cvssV3_1" in metric:
                severity = metric["cvssV3_1"].get("baseSeverity", "UNKNOWN")
                score = metric["cvssV3_1"].get("baseScore", 0.0)
                break
            elif "cvssV3_0" in metric:
                severity = metric["cvssV3_0"].get("baseSeverity", "UNKNOWN")
                score = metric["cvssV3_0"].get("baseScore", 0.0)
                break

        remediation = "Apply latest vendor patches. Monitor network traffic for anomalous behavior targeting this vulnerability."
        
        return jsonify({
            "id": cve_id,
            "description": desc,
            "severity": severity.upper(),
            "cvss": score,
            "remediation": remediation,
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    ensure_startup()
    print(f"Starting server -> http://localhost:5000  (mode: {llm_mode})")
    app.run(debug=False, port=5000)


# Ensure startup also runs when served by WSGI servers like gunicorn.
ensure_startup()
