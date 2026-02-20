import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_groq import ChatGroq
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

app = Flask(__name__, static_folder="static", static_url_path="")
CORS(app)

chat_history = []
retriever    = None
chain        = None


def load_chain():
    global retriever, chain
    print("Loading FAISS index…")
    embeddings   = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    vector_store = FAISS.load_local(FAISS_PATH, embeddings, allow_dangerous_deserialization=True)
    retriever    = vector_store.as_retriever(search_kwargs={"k": 5})

    llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=0,
        groq_api_key=GROQ_API_KEY,
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

    def get_context(inputs):
        docs = retriever.invoke(inputs["question"])
        return "\n\n".join(d.page_content for d in docs)

    chain = (
        RunnablePassthrough.assign(context=RunnableLambda(get_context))
        | prompt | llm | StrOutputParser()
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
        answer = chain.invoke({"question": question, "chat_history": chat_history})
        chat_history.append(HumanMessage(content=question))
        chat_history.append(AIMessage(content=answer))
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
    print("Starting server → http://localhost:5000")
    app.run(debug=False, port=5000)
