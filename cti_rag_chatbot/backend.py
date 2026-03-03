# This backend implements a retrieval-augmented generation (RAG) chatbot. It
# leverages a FAISS vector index of MITRE ATT&CK content for retrieval and a
# local LLM (via Ollama) for synthesis.  Responses are streamed via SSE.
import json
import os
import re
from dotenv import load_dotenv
from flask import Flask, request, jsonify, send_from_directory, Response, stream_with_context
from flask_cors import CORS
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from langchain_ollama import ChatOllama

load_dotenv()

EMBEDDING_MODEL = "all-MiniLM-L6-v2"
# compute paths relative to this file so the service works when invoked from anywhere
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FAISS_PATH = os.path.join(BASE_DIR, "faiss_index")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:1b")

# Simple greetings — handled without hitting the LLM at all
GREETINGS = {"hi", "hello", "hey", "hi there", "hello there", "greetings", "good morning",
             "good afternoon", "good evening", "howdy", "sup", "what's up"}

GREETING_REPLY = (
    "Hello! I'm your **Cyber Threat Intelligence** assistant powered by the "
    "MITRE ATT&CK knowledge base.\n\n"
    "Here are some things I can help with:\n"
    "- **Techniques** — Explain any ATT&CK technique (e.g. T1059, T1078)\n"
    "- **Threat Groups** — Describe known adversaries like APT28, Lazarus Group\n"
    "- **Malware & Tools** — Detail malicious software such as Cobalt Strike\n"
    "- **Mitigations & Detections** — Recommend defenses for specific attacks\n\n"
    "Just type your question below to get started!"
)

SYSTEM_PROMPT = (
    "You are an expert Cyber Threat Intelligence analyst assistant.\n"
    "Answer strictly from the provided context. Use Markdown: headings, bullets, bold, "
    "inline code for MITRE IDs (e.g. `T1059.001`).\n"
    "Structure by: Description, Procedure Examples, Mitigations, Detection as applicable.\n"
    "Do NOT invent information. Do NOT include a Sources section.\n"
    "If the context is insufficient say: \"I could not find that in the MITRE ATT&CK knowledge base.\"\n\n"
    "Context:\n{context}"
)

app = Flask(__name__, static_folder="static", static_url_path="")
CORS(app)

chat_history = []
retriever = None
llm = None
prompt = None


def load_chain():
    global retriever, llm, prompt

    print("Loading FAISS index...")
    if not os.path.isdir(FAISS_PATH) or not os.path.exists(os.path.join(FAISS_PATH, "index.faiss")):
        raise FileNotFoundError(
            f"FAISS index not found at '{FAISS_PATH}/index.faiss'. "
            "Please generate or download the index before starting the server."
        )
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    vector_store = FAISS.load_local(
        FAISS_PATH, embeddings, allow_dangerous_deserialization=True
    )
    retriever = vector_store.as_retriever(search_kwargs={"k": 5})

    llm = ChatOllama(
        model=OLLAMA_MODEL,
        base_url="http://127.0.0.1:11434",
        temperature=0.1,
        num_predict=512,   # cap max tokens for speed
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{question}"),
    ])

    print("Chain ready. Model:", OLLAMA_MODEL)


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/api/chat", methods=["POST"])
def chat():
    global chat_history
    if llm is None:
        return jsonify({"error": "Backend not ready. Please wait."}), 503

    data = request.json or {}
    question = data.get("question", "").strip()
    if not question:
        return jsonify({"error": "Question cannot be empty."}), 400

    # Handle greetings without touching the LLM
    if question.lower().rstrip("!?.") in GREETINGS:
        return jsonify({"answer": GREETING_REPLY, "sources": []})

    try:
        # expand short or code-like queries for better retrieval
        query = question
        words = question.split()
        if len(words) <= 3 and not question.endswith("?"):
            if re.match(r"^[TtSsMm]\d{4}(\.\d{1,3})?$", question.strip()):
                query = f"Explain MITRE ATT&CK technique {question} including description, mitigations, and detection"
            else:
                query = f"What is {question} in cyber threat intelligence and MITRE ATT&CK?"

        # ---- Single retrieval call (reused for context + sources) ----
        source_docs = retriever.invoke(query)
        sources = []
        context_parts = []

        for d in source_docs:
            name = d.metadata.get("name", "Unknown")
            mid = d.metadata.get("external_id") or d.metadata.get("id") or ""
            url = d.metadata.get("url", "")

            sources.append({
                "name": name,
                "type": d.metadata.get("type", ""),
                "url": url,
                "snippet": d.page_content[:200],
            })

            context_parts.append(f"[{name} | {mid}]\n{d.page_content}")

        context_text = "\n\n---\n\n".join(context_parts)

        # Build the prompt messages directly (no chain overhead)
        messages = prompt.invoke({
            "context": context_text,
            "chat_history": chat_history,
            "question": query,
        })

        # ---- Stream response via SSE ----
        def generate():
            full_answer = []
            # First emit sources so the frontend can show them immediately
            yield f"data: {json.dumps({'sources': sources})}\n\n"

            for chunk in llm.stream(messages):
                token = chunk.content
                if token:
                    full_answer.append(token)
                    yield f"data: {json.dumps({'token': token})}\n\n"

            answer = "".join(full_answer)

            # lightweight grounding check
            ans_words = set(w.lower().strip(".,?!;:\"'()") for w in answer.split())
            ctx_words = set(w.lower().strip(".,?!;:\"'()") for w in context_text.split())
            if ans_words and ctx_words:
                overlap = sum(1 for w in ans_words if w in ctx_words)
                if overlap / len(ans_words) < 0.10:
                    answer = ("I could not find that in the MITRE ATT&CK knowledge base. "
                              "Please ask a question related to cyber threat intelligence, "
                              "attack techniques, malware, or threat groups.")
                    yield f"data: {json.dumps({'replace': answer})}\n\n"

            # update history
            chat_history.append(HumanMessage(content=question))
            chat_history.append(AIMessage(content=answer))
            if len(chat_history) > 10:
                chat_history[:] = chat_history[-10:]

            yield "data: {\"done\": true}\n\n"

        return Response(
            stream_with_context(generate()),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Keep the non-streaming endpoint for backwards compat / simple clients
@app.route("/api/chat/sync", methods=["POST"])
def chat_sync():
    global chat_history
    if llm is None:
        return jsonify({"error": "Backend not ready. Please wait."}), 503

    data = request.json or {}
    question = data.get("question", "").strip()
    if not question:
        return jsonify({"error": "Question cannot be empty."}), 400

    if question.lower().rstrip("!?.") in GREETINGS:
        return jsonify({"answer": GREETING_REPLY, "sources": []})

    try:
        query = question
        words = question.split()
        if len(words) <= 3 and not question.endswith("?"):
            if re.match(r"^[TtSsMm]\d{4}(\.\d{1,3})?$", question.strip()):
                query = f"Explain MITRE ATT&CK technique {question} including description, mitigations, and detection"
            else:
                query = f"What is {question} in cyber threat intelligence and MITRE ATT&CK?"

        source_docs = retriever.invoke(query)
        sources = []
        context_parts = []
        for d in source_docs:
            name = d.metadata.get("name", "Unknown")
            mid = d.metadata.get("external_id") or d.metadata.get("id") or ""
            url = d.metadata.get("url", "")
            sources.append({"name": name, "type": d.metadata.get("type", ""), "url": url, "snippet": d.page_content[:200]})
            context_parts.append(f"[{name} | {mid}]\n{d.page_content}")

        context_text = "\n\n---\n\n".join(context_parts)
        messages = prompt.invoke({"context": context_text, "chat_history": chat_history, "question": query})
        result = llm.invoke(messages)
        answer = result.content

        chat_history.append(HumanMessage(content=question))
        chat_history.append(AIMessage(content=answer))
        if len(chat_history) > 10:
            chat_history[:] = chat_history[-10:]

        return jsonify({"answer": answer, "sources": sources})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/reset", methods=["POST"])
def reset():
    global chat_history
    chat_history = []
    return jsonify({"status": "reset"})


if __name__ == "__main__":
    load_chain()
    print("Starting server -> http://localhost:5000")
    app.run(debug=False, port=5000)
