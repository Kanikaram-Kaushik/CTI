# CTI RAG Chatbot Workflow

This repository contains a **retrieval-augmented generation (RAG)** cyber threat intelligence assistant using MITRE ATT&CK data.

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

   The requirements file includes packages for Flask, LangChain, FAISS, Groq integration, and `pytest` for testing.

## Indexing Data

The `ingest.py` script downloads the MITRE ATT&CK STIX bundle (if not present), parses relevant objects, chunks the text, and builds a FAISS vector index.

Run it once before starting the server (or whenever you update the STIX data):

```powershell
python ingest.py
```

This creates the `faiss_index/index.faiss` file required by the backend.

## Frontend Setup (React)

Install Node dependencies for the React app:

```powershell
cd frontend
npm install
```

Build the React app for Flask to serve:

```powershell
npm run build
cd ..
```

For local UI development with hot reload, run:

```powershell
cd frontend
npm run dev
```

## Running the Server (Flask API + React build)

Start the backend service:

```powershell
python backend.py
```

The Flask app listens on `http://localhost:5000` and exposes:

- `GET /` serves the built React UI from `frontend/dist`
- `POST /api/chat` streams responses with source and OWASP metadata via Server-Sent Events
- `POST /api/reset` clears the chat history.
- `GET /api/status` returns backend/model readiness.

If React build files are missing, Flask returns a clear `503` message with build instructions.

## MongoDB Chat History (Optional)

You can persist chat history in MongoDB by setting environment variables:

```powershell
$env:MONGODB_URI="mongodb://localhost:27017"
$env:MONGODB_DB="anti_rtrp"
$env:MONGODB_COLLECTION="chat_history"
```

Behavior:

- If `MONGODB_URI` is set and reachable, chat exchanges are persisted
- `GET /api/history` returns recent persisted messages for frontend bootstrapping
- `POST /api/reset` clears in-memory and persisted chat history
- If MongoDB is not configured, the app falls back to in-memory history

## Testing

A simple test suite exercises greetings, empty input handling, and retrieval behavior.

To run the tests:

```powershell
python -m pytest test_chat.py -q
```

## RAG Evaluation Harness

Run the lightweight quality benchmark (backend must be running first):

```powershell
python evaluate_rag.py
```

This prints:

- average answer-term recall
- source-hint hit rate
- average retrieval confidence
- abstain rate
- average number of sources

## Retrieval and Confidence

- Retrieval mode uses hybrid ranking (dense FAISS + lexical signals)
- Responses include a confidence estimate and abstain decision
- Low-confidence queries are safely abstained with an explanation

Tests will automatically regenerate the FAISS index if missing.

## Notes & Tips

- The backend verifies that the FAISS index exists and raises a clear error if not found.
- Paths are computed relative to the script file so you can launch from any working directory.
- Set `GROQ_API_KEY` before starting the backend. You can optionally set `GROQ_MODEL` to override the default Groq model.

## Contributors & Team Attribution

This project was developed collaboratively by a team of 5 members, with the following role assignments:

### **Project Lead & Core Development**
- **You** (Team Lead)
  - Architecture and system design
  - LLM integration (Groq migration from Ollama)
  - Backend optimization and prompt engineering
  - Cybersecurity-only context enforcement
  - DevOps and deployment configuration
  - Project coordination and code review

### **Backend Development**
- **Munna** (Backend Engineer)
  - Flask application framework and API endpoints
  - Chat streaming and real-time response architecture
  - Error handling and logging infrastructure
  - Performance optimization for query processing
  - Integration testing and validation

### **Data & Retrieval Pipeline**
- **Sandy** (Data Engineer)
  - FAISS vector store implementation and optimization
  - MITRE ATT&CK data ingestion and parsing
  - Embedding model configuration and tuning
  - Relevance scoring and retrieval enhancement
  - Data pipeline automation

### **Frontend & UI**
- **Med** (Frontend Developer)
  - React/vanilla JavaScript UI components
  - Real-time streaming message display
  - Chat history and reset functionality
  - Status badge and connection monitoring
  - Web UI styling and UX improvements

### **MITRE ATT&CK Domain & Testing**
- **Sah** (QA & Cybersecurity Specialist)
  - MITRE ATT&CK context validation
  - Cybersecurity test case design
  - Query scope enforcement testing
  - Threat intelligence accuracy verification
  - Test suite maintenance and expansion

---

Each team member's contributions are equally important to the project's success. Decisions regarding model selection, feature prioritization, and architecture were made collaboratively.

With these steps, the full workflow—from dependency installation and data ingestion through to API operation and testing—is re-established and documented.