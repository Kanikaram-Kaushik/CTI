import os
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
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
FAISS_PATH      = "faiss_index"
OLLAMA_MODEL    = os.getenv("OLLAMA_MODEL", "llama3.2:1b")

app = Flask(__name__, static_folder="static", static_url_path="")
CORS(app)

chat_history = []
retriever    = None
chain        = None
llm_mode     = "unknown"   # "groq" or "ollama"


def _try_groq():
    """Try to initialise the Groq cloud LLM. Returns the LLM or None."""
    if not GROQ_API_KEY:
        return None
    try:
        from langchain_groq import ChatGroq
        llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            temperature=0,
            groq_api_key=GROQ_API_KEY,
        )
        # Quick connectivity check – if Groq is unreachable this will raise
        llm.invoke("ping")
        return llm
    except Exception as e:
        print(f"Groq unavailable ({e}), falling back to Ollama…")
        return None


def _try_ollama():
    """Try to initialise the local Ollama LLM. Returns the LLM or None."""
    try:
        from langchain_ollama import ChatOllama
        llm = ChatOllama(
            model=OLLAMA_MODEL,
            base_url="http://127.0.0.1:11434",
            temperature=0.1,
            num_predict=512,
        )
        return llm
    except Exception as e:
        print(f"Ollama unavailable ({e})")
        return None


def _is_offline():
    """Quick check: can we resolve huggingface.co?"""
    try:
        socket.create_connection(("huggingface.co", 443), timeout=3)
        return False
    except OSError:
        return True


def load_chain():
    global retriever, chain, llm_mode
    print("Loading FAISS index…")

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

    # Try Groq (online) first, then fall back to Ollama (offline)
    llm = _try_groq()
    if llm is not None:
        llm_mode = "groq"
        print("Using Groq cloud LLM ✓")
    else:
        llm = _try_ollama()
        if llm is not None:
            llm_mode = "ollama"
            print(f"Using Ollama local LLM ({OLLAMA_MODEL}) ✓")
        else:
            raise RuntimeError(
                "No LLM available. Set GROQ_API_KEY for cloud mode, "
                "or install & start Ollama (https://ollama.com) for offline mode."
            )

    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "You are a Cyber Threat Intelligence analyst assistant. "
         "Use the following retrieved context from MITRE ATT&CK to answer accurately. "
         "If the context doesn't contain the answer, say so and provide general guidance.\n\n"
         "Context:\n{context}"),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{question}"),
    ])

    chain = (
        prompt | llm | StrOutputParser()
    )
    print("Chain ready ✓")


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

    try:
        source_docs = retriever.invoke(question)
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
            for chunk in chain.stream({"question": question, "chat_history": chat_history, "context": context_text}):
                full_answer += chunk
                yield f"data: {json.dumps({'chunk': chunk})}\n\n"
            
            chat_history.append(HumanMessage(content=question))
            chat_history.append(AIMessage(content=full_answer))
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
        "model": "llama-3.3-70b-versatile" if llm_mode == "groq" else OLLAMA_MODEL,
        "ready": chain is not None,
    })


if __name__ == "__main__":
    load_chain()
    print(f"Starting server → http://localhost:5000  (mode: {llm_mode})")
    app.run(debug=False, port=5000)
