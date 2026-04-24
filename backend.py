import os
import re
import socket
import json
from flask import Flask, request, jsonify, send_from_directory, Response, stream_with_context
from flask_cors import CORS
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from dotenv import load_dotenv

load_dotenv()

# ── Config ─────────────────────────────────────────────
GROQ_API_KEY    = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL      = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
FAISS_PATH      = "faiss_index"

app = Flask(__name__, static_folder="static", static_url_path="")
CORS(app)

chat_history = []
retriever    = None
chain        = None
llm_mode     = "groq"
vector_store = None
attack_id_map = {}
intrusion_set_map = {}

LOCAL_STIX_FILE = "data/enterprise-attack.json"

MIN_RELEVANCE_SCORE = 0.25

MITRE_SCOPE_KEYWORDS = {
    "mitre", "attack", "att&ck", "technique", "techniques", "tactic", "tactics",
    "ttp", "ttps", "intrusion", "threat", "threats", "adversary", "adversaries",
    "apt", "malware", "tool", "tools", "detection", "detections", "mitigation",
    "mitigations", "credential", "persistence", "lateral", "exfiltration",
    "privilege", "reconnaissance", "evasion", "execution", "initial access",
    "command and control", "c2", "defense"
}


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
        # Quick connectivity check – if Groq is unreachable this will raise
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


def _rewrite_query(question):
    """Rewrite vague or offensive-sounding queries into defensive MITRE ATT&CK research queries."""
    q = question.lower().strip()
    # Map common vague offensive queries to proper defensive research queries
    rewrites = {
        "how to hack": "What are the most common MITRE ATT&CK techniques used by adversaries to compromise systems, and what are the recommended detection and mitigation strategies?",
        "how to hack systems": "What are the most common MITRE ATT&CK techniques used by adversaries to compromise systems, and what are the recommended detection and mitigation strategies?",
        "how to hack a computer": "What MITRE ATT&CK techniques describe methods adversaries use to gain access to computer systems, and how can defenders detect and prevent them?",
        "how to hack a network": "What MITRE ATT&CK techniques describe network-based attacks, and what are the recommended network defense mitigations?",
        "how to attack": "What are common initial access and execution techniques in the MITRE ATT&CK framework, and how should organizations defend against them?",
        "how to exploit": "What exploitation techniques are documented in MITRE ATT&CK, and what mitigations and detections are recommended?",
    }
    for trigger, rewrite in rewrites.items():
        if q == trigger or q == trigger + " systems" or q.startswith(trigger):
            return rewrite
    return question


def _force_cyber_context(question):
    """Convert any input into a cybersecurity-only query."""
    q = question.strip()
    if not q:
        q = "general query"
    return (
        "Answer strictly in cybersecurity context only. "
        f"Treat the user input '{q}' as a cyber threat, attack pattern, intrusion set, or defensive-control prompt. "
        "Do not answer literally, do not do math, do not render HTML, and do not leave the cyber domain. "
        "Focus on MITRE ATT&CK techniques, adversary behavior, detections, mitigations, or incident-response implications."
    )


def _is_mitre_scoped_query(question):
    """All questions are allowed, but they are rewritten into cyber context first."""
    return True


def _retrieve_with_relevance(question, k=5):
    """Retrieve documents with relevance scores (0..1)."""
    if vector_store is None:
        return []
    try:
        return vector_store.similarity_search_with_relevance_scores(question, k=k)
    except Exception:
        # If relevance scores are unavailable, fall back to plain retrieval.
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

    # For very short in-scope prompts, add retrieval hints while preserving user intent.
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


def _normalize(s):
    return re.sub(r"\s+", "", s.lower())


def load_chain():
    global retriever, chain, llm_mode, vector_store, attack_id_map, intrusion_set_map
    print("Loading FAISS index...")

    # If we can't reach HuggingFace, tell the hub library to use cached model files
    is_offline = _is_offline()
    cache_dir = os.path.expanduser("~/.cache/huggingface/hub")
    
    if is_offline:
        os.environ["HF_HUB_OFFLINE"] = "1"
        print("Network unavailable — using cached embedding model.")

    try:
        embeddings = HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL,
            cache_folder=cache_dir,
            show_progress=True,
        )
    except Exception as e:
        print(f"\n✗ ERROR: Failed to load embedding model '{EMBEDDING_MODEL}'")
        print(f"Details: {e}")
        if is_offline:
            print("\n" + "="*70)
            print("OFFLINE MODE REQUIRES CACHED MODEL")
            print("="*70)
            print("The model must be downloaded while online:")
            print("   python download_embedding_model.py")
            print("="*70)
        raise
    
    vector_store = FAISS.load_local(FAISS_PATH, embeddings, allow_dangerous_deserialization=True)
    retriever    = vector_store.as_retriever(search_kwargs={"k": 5})
    attack_id_map = _load_attack_id_map()
    intrusion_set_map = _load_intrusion_set_map()
    print(f"Loaded ATT&CK technique map entries: {len(attack_id_map)}")
    print(f"Loaded intrusion-set map entries: {len(intrusion_set_map)}")

    # Groq is the only supported LLM provider.
    llm = _try_groq()
    if llm is None:
        raise RuntimeError(
            "No Groq LLM available. Set GROQ_API_KEY and ensure Groq is reachable."
        )

    print(f"Using Groq cloud LLM ({GROQ_MODEL}) [ok]")

    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "You are a strict cybersecurity-only assistant.\n"
         "1. Every user input must be interpreted only through the lens of cyberattacks, defenses, MITRE ATT&CK, incident response, or threat analysis.\n"
         "2. If the user asks for math, HTML, code, numbers, or unrelated content, reinterpret it as a cybersecurity question instead of answering literally.\n"
         "3. Keep the response clear, concise, and helpful.\n\n"
         "Retrieved Context:\n{context}"),
        ("human", "Question: {question}"),
    ])

    chain = (
        prompt | llm | StrOutputParser()
    )
    print("Chain ready [ok]")


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/api/chat", methods=["POST"])
def chat():
    global chat_history
    if chain is None:
        return jsonify({"error": "Backend not ready. Please wait a moment."}), 503

    data     = request.json or {}
    question = data.get("question", "").strip()
    if not question:
        return jsonify({"error": "Question cannot be empty."}), 400

    # Hard scope gate: reject casual/non-MITRE prompts before generation.
    if not _is_mitre_scoped_query(question):
        return jsonify({
            "error": (
                "This assistant is strict MITRE RAG only. Ask questions about "
                "MITRE ATT&CK techniques, tactics, threat groups, malware, tools, "
                "detections, or mitigations."
            )
        }), 400

    # Rewrite every input into cybersecurity context before retrieval or generation.
    question_for_llm = _force_cyber_context(question)
    retrieval_query = _expand_query_for_retrieval(question_for_llm)

    try:
        scored_results = _retrieve_with_relevance(retrieval_query, k=4)
        
        source_docs = [doc for doc, _ in scored_results] if scored_results else []

        # Strict entity grounding helpers.
        allow_low_score = False
        technique_match = re.search(r"\b(T\d{4}(?:\.\d{3})?)\b", question.upper())
        if technique_match:
            t_id = technique_match.group(1)
            if t_id in attack_id_map:
                allow_low_score = True
                exact = attack_id_map[t_id]
                exact_doc = type(source_docs[0])(
                    page_content=exact["content"],
                    metadata={
                        "name": exact["name"],
                        "type": "attack-pattern",
                        "url": exact.get("url", ""),
                    },
                )
                # Put exact technique context first so generation is anchored.
                source_docs = [exact_doc] + source_docs

        apt_matches = re.findall(r"\bAPT\s*\d+\b", question.upper())
        if apt_matches:
            normalized_targets = {_normalize(a) for a in apt_matches}
            # If exact APT exists in local MITRE document, inject it first.
            for target in normalized_targets:
                if target.upper() in intrusion_set_map:
                    exact = intrusion_set_map[target.upper()]
                    exact_doc = type(source_docs[0])(
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

        # Relevance gate to keep responses strictly grounded in MITRE context.
        best_score = None
        if scored_results and scored_results[0][1] is not None:
            best_score = scored_results[0][1]
            # We no longer block on low relevance scores so that greetings and 
            # general cyber questions can be handled by the LLM natively.
            # But if the score is very low, we drop the context to avoid confusing the LLM.
            is_entity_query = bool(re.fullmatch(r"(?i)\s*(apt\s*\d+|t\d{4}(?:\.\d{3})?)\s*", question.strip()))
            threshold = 0.18 if is_entity_query else MIN_RELEVANCE_SCORE
            if best_score < threshold and not allow_low_score:
                source_docs = [] # Clear context, let the LLM use general knowledge/greetings

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
        
        def generate():
            yield f"data: {json.dumps({'sources': sources})}\n\n"
            
            full_answer = ""
            # Stream the response instead of blocking for the whole answer
            for chunk in chain.stream({"question": question_for_llm, "context": context_text}):
                # Light filter for think tags in case deepseek is used
                if "<think>" in chunk or "</think>" in chunk:
                    continue
                full_answer += chunk
                yield f"data: {json.dumps({'chunk': chunk})}\n\n"

            # Fallback if empty
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
        "ready": chain is not None,
    })


if __name__ == "__main__":
    load_chain()
    print(f"Starting server -> http://localhost:5000  (mode: {llm_mode})")
    app.run(debug=False, port=5000)
