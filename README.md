# 🛡️ CTI RAG Chatbot

A **Retrieval-Augmented Generation (RAG)** chatbot for **Cyber Threat Intelligence (CTI)** powered by the MITRE ATT&CK knowledge base.

## Features

- 🔍 Semantic search over the full MITRE ATT&CK Enterprise dataset
- 🤖 AI-generated answers grounded in real threat intelligence
- 💬 Conversational memory across the session
- 📄 Source citations for every answer
- 🆓 Free local embeddings (no OpenAI quota needed for ingestion)

## Stack

| Component | Technology |
|---|---|
| Frontend | Streamlit |
| Embeddings | `all-MiniLM-L6-v2` (HuggingFace, local) |
| Vector Store | FAISS |
| LLM | OpenAI `gpt-4o-mini` |
| Data Source | MITRE ATT&CK STIX (Enterprise) |

## Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure API Key
Create a `.env` file:
```
OPENAI_API_KEY=your_openai_api_key_here
```

### 3. Build the FAISS Index
Downloads MITRE ATT&CK data and creates a local vector index (run once):
```bash
python ingest.py
```

### 4. Run the App
```bash
python -m streamlit run app.py
```
Then open [http://localhost:8501](http://localhost:8501)

## Example Questions

- *What is the T1059 technique?*
- *How can I detect credential dumping?*
- *What mitigations exist for lateral movement attacks?*
- *Tell me about the APT28 threat group*

## Notes

- The `.env` file and `faiss_index/` directory are excluded from git (see `.gitignore`)
- Re-run `ingest.py` if you need to refresh the MITRE ATT&CK data
