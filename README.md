# CTI RAG Chatbot Workflow

is repository contains a simple **retrieval‑augmented generation (RAG)** cyber threat intelligence assistant using MITRE ATT&CK data.

## Setup

1. **Create Python virtual environment** (if not already):
   ```powershell
   python -m venv .venv
   ```

2. **Activate environment**:
   ```powershell
   .\.venv\Scripts\Activate.ps1  # PowerShell
   # or .venv\Scripts\activate.bat (cmd)
   ```

3. **Install dependencies**:
   ```powershell
   python -m pip install --upgrade pip
   python -m pip install -r requirements.txt
   ```

   The requirements file includes packages for Flask, LangChain, FAISS, and `pytest` for testing.

## Indexing Data

The `injest.py` script downloads the MITRE ATT&CK STIX bundle (if not present), parses relevant objects, chunks the text, and builds a FAISS vector index.

Run it once before starting the server (or whenever you update the STIX data):

```powershell
python cti_rag_chatbot\injest.py
```

This will create the `cti_rag_chatbot/faiss_index/index.faiss` file required by the backend.

## Running the Server

Start the backend service:

```powershell
python cti_rag_chatbot\backend.py
```

The Flask app listens on `http://localhost:5000` and exposes:

- `GET /` serves the static UI
- `POST /api/chat` accepts JSON {"question": "..."}. It retrieves relevant passages from the ATT&CK index and generates an answer grounded in those documents. The endpoint includes a hallucination guard—if the response cannot be justified from the context, it replies with a polite failure message. The returned JSON includes `answer`, `sources`, and (when generated) the full `context` used for synthesis.
- `POST /api/reset` clears the chat history.

## Testing

A simple test suite exercises greetings, empty input handling, and retrieval behavior.

To run the tests:

```powershell
python -m pytest cti_rag_chatbot\test_backend.py -q
```

Tests will automatically regenerate the FAISS index if missing.

## Notes & Tips

- The backend verifies that the FAISS index exists and raises a clear error if not found.
- Paths are computed relative to the script file so you can launch from any working directory.
- Ensure `OLLAMA_MODEL` environment variable is set or defaults to `llama3.2:1b`.

---

With these steps, the full workflow—from dependency installation and data ingestion through to API operation and testing—is re-established and documented.