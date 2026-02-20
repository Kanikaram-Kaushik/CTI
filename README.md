# 🛡️ CTI RAG Chatbot

A **Retrieval-Augmented Generation (RAG)** chatbot for **Cyber Threat Intelligence (CTI)** powered by the MITRE ATT&CK knowledge base.

## Features

- 🔍 Semantic search over the full MITRE ATT&CK Enterprise dataset
- 🤖 AI-generated answers grounded in real threat intelligence (Groq + Llama 3.3)
- 💬 Conversational memory across the session
- 📄 Source citations for every answer
- 🆓 Fully free — local embeddings + Groq free tier LLM
- 🌐 Clean HTML/CSS/JS frontend (no Streamlit)

## Stack

| Component | Technology |
|---|---|
| Backend | Flask (Python) |
| Frontend | HTML + CSS + JavaScript |
| Embeddings | `all-MiniLM-L6-v2` (HuggingFace, local) |
| Vector Store | FAISS |
| LLM | Groq `llama-3.3-70b-versatile` (free) |
| Data Source | MITRE ATT&CK STIX (Enterprise) |

## Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Build the FAISS Index
Downloads MITRE ATT&CK data and creates a local vector index (run once):
```bash
python ingest.py
```

### 3. Run the Backend
```bash
python backend.py
```
Then open [http://localhost:5000](http://localhost:5000)

## Project Structure

```
cti_rag_chatbot/
├── backend.py          # Flask API server
├── ingest.py           # MITRE ATT&CK data ingestion
├── requirements.txt    # Python dependencies
├── static/
│   ├── index.html      # Chat UI
│   ├── style.css       # Cyberpunk-themed styles
│   └── app.js          # Frontend logic
└── faiss_index/        # (generated, not in git)
```

## Example Questions

- *What is the T1059 technique?*
- *How can I detect credential dumping?*
- *What mitigations exist for lateral movement attacks?*
- *Tell me about the APT28 threat group*
- *What techniques does Cobalt Strike use?*

## Notes

- The `faiss_index/` directory is excluded from git — re-run `ingest.py` to regenerate it
- The Groq API key is configured in `backend.py`
- Get a free Groq key at [console.groq.com](https://console.groq.com)
