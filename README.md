---
title: CTI RAG Chatbot
emoji: 🛡️
colorFrom: blue
colorTo: indigo
sdk: docker
pinned: false
---

# CTI RAG Chatbot

A retrieval-augmented generation (RAG) chatbot for cyber-threat-intelligence research. The application combines MITRE ATT&CK and OWASP security knowledge bases with hybrid retrieval and a Groq-powered language model to answer cybersecurity questions with supporting sources, confidence information, and safe abstention when the available evidence is insufficient.

> **Important:** This project is an educational and research tool. Do not treat generated responses as a substitute for validated threat intelligence, incident-response procedures, or professional security advice.

## Features

- Cybersecurity-focused conversational assistant.
- MITRE ATT&CK knowledge retrieval for techniques, tactics, intrusion sets, malware, and tools.
- OWASP Cheat Sheet Series ingestion for secure-development and defensive guidance.
- Hybrid retrieval using FAISS dense vectors and lexical/BM25-like ranking signals.
- Confidence scoring and safe abstention for low-evidence questions.
- Streaming answers over Server-Sent Events (SSE).
- Source metadata and relevant OWASP references returned with each response.
- React frontend served by the Flask backend after a production build.
- SQLite-backed chat history with optional persistent storage on deployment platforms.
- CVE lookup through the MITRE CVE API with an NVD fallback.
- Docker and Docker Compose support.

## Architecture

```text
User
  │
  ▼
React frontend ── HTTP/SSE ──▶ Flask backend
                                  │
                  ┌───────────────┼────────────────┐
                  ▼               ▼                ▼
             FAISS index     Groq LLM       SQLite history
                  │
                  ▼
       MITRE ATT&CK + OWASP documents
```

### Retrieval and response flow

1. MITRE ATT&CK STIX data and OWASP Cheat Sheets are loaded by `ingest.py`.
2. Documents are split into chunks and embedded with `all-MiniLM-L6-v2`.
3. FAISS stores the dense vector index under `faiss_index/`.
4. The backend combines dense retrieval with lexical matching and reranks the candidates.
5. Retrieved context is passed to the Groq model.
6. The backend streams the response, sources, OWASP references, and retrieval metadata to the frontend.
7. If confidence is below the configured threshold, the assistant abstains instead of guessing.

## Repository layout

```text
.
├── backend.py                 # Flask API, RAG pipeline, SSE streaming, and CVE lookup
├── database.py                # SQLite chat-history persistence
├── ingest.py                  # Downloads/parses source data and builds the FAISS index
├── analyze_mitre.py           # MITRE ATT&CK analysis utility
├── fetch_logs.py              # Log-fetching utility
├── test_chat.py              # Basic API smoke test
├── data/                     # Local source data and cloned OWASP content
├── faiss_index/              # Generated FAISS vector-store files
├── frontend/                 # React/Vite user interface
├── Dockerfile                # Production container image
├── docker-compose.yml        # Local container orchestration
├── render.yaml               # Render deployment configuration
├── requirements.txt          # Python dependencies
└── repos.json                # Repository/data configuration
```

## Prerequisites

- Python 3.11 or newer
- Node.js 18+ and npm
- Git
- A Groq API key for answer generation
- Internet access on the first ingestion run to download MITRE ATT&CK and OWASP data

## Configuration

Create a `.env` file in the repository root:

```dotenv
GROQ_API_KEY=gsk_your_api_key_here
GROQ_MODEL=llama-3.1-8b-instant
```

Optional MongoDB variables are supported by the deployment configuration when external chat persistence is needed:

```dotenv
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB=anti_rtrp
MONGODB_COLLECTION=chat_history
```

Never commit `.env` files or API keys to the repository.

## Local development

### 1. Clone the repository

```bash
git clone https://github.com/Kanikaram-Kaushik/CTI.git
cd CTI
```

### 2. Create and activate a virtual environment

#### macOS/Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
```

#### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install Python dependencies

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 4. Build the knowledge index

Run ingestion before starting the application:

```bash
python ingest.py
```

The script will:

- Load `data/enterprise-attack.json` if it exists, or download the MITRE ATT&CK Enterprise STIX bundle.
- Clone the OWASP Cheat Sheet Series into `data/CheatSheetSeries/` if it is not present.
- Generate embeddings with `all-MiniLM-L6-v2`.
- Save the resulting vector store to `faiss_index/`.

The first run may take several minutes and requires additional disk space for the embedding model and source data.

### 5. Install and build the frontend

```bash
cd frontend
npm install
npm run build
cd ..
```

The Flask application serves the compiled frontend from `frontend/dist`.

For frontend development with Vite hot reload:

```bash
cd frontend
npm run dev
```

### 6. Start the backend

```bash
python backend.py
```

The development server is available at:

```text
http://localhost:5000
```

The backend initializes the FAISS retriever, ATT&CK lookup maps, the Groq model, and the SQLite database during startup.

## Docker

Build and run the application with Docker Compose:

```bash
docker compose up --build
```

The container listens on port `7860`:

```text
http://localhost:7860
```

Docker Compose reads `GROQ_API_KEY` and optionally `GROQ_MODEL` from the environment or `.env` file.

To run the image directly:

```bash
docker build -t cti-rag-chatbot .
docker run --rm -p 7860:7860 --env-file .env cti-rag-chatbot
```

The production container starts Gunicorn with:

```text
gunicorn backend:app --bind 0.0.0.0:${PORT:-7860} --workers 1 --threads 4 --timeout 120
```

## API endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Serves the built React frontend. |
| `POST` | `/api/chat` | Streams a RAG response, sources, OWASP references, and retrieval metadata using SSE. |
| `GET` | `/api/status` | Returns model, retrieval, history, and readiness status. |
| `POST` | `/api/reset` | Returns a reset status for the current frontend session. |
| `GET` | `/api/history` | Returns stored chat sessions. |
| `DELETE` | `/api/history/<session_id>` | Deletes one chat-history session. |
| `GET` | `/api/malware/<name>` | Generates a threat summary for a MITRE malware/tool entry. |
| `GET` | `/api/cve/<cve_id>` | Looks up CVE details using MITRE and NVD APIs. |

### Chat request example

```bash
curl -N -X POST http://localhost:5000/api/chat \
  -H 'Content-Type: application/json' \
  -d '{"question":"What is MITRE ATT&CK technique T1059?","session_id":"demo"}'
```

The `/api/chat` endpoint returns Server-Sent Events. Events can include:

- `sources` — retrieved document names, types, URLs, and snippets.
- `owasp_refs` — related OWASP references.
- `retrieval` — retrieval mode and confidence details.
- `chunk` — streamed answer content.
- `[DONE]` — stream completion marker.

## Testing

Start the backend first, then run the basic API smoke test:

```bash
python test_chat.py
```

The script sends sample requests to `http://127.0.0.1:5000/api/chat` and prints the returned result or error.

## Deployment

The repository includes deployment files for container-based hosting:

- `Dockerfile` — builds the production image.
- `render.yaml` — defines a Render web service and its environment variables.
- Hugging Face Spaces metadata is included at the top of this README for Docker SDK deployments.

At minimum, configure `GROQ_API_KEY` in the deployment platform's secret/environment settings. Configure persistent storage if chat history or generated indexes must survive container restarts.

## Data sources and attribution

This project consumes or references:

- [MITRE ATT&CK](https://attack.mitre.org/) Enterprise ATT&CK STIX data.
- [OWASP Cheat Sheet Series](https://cheatsheetseries.owasp.org/).
- [MITRE CVE Services](https://www.cve.org/).
- [National Vulnerability Database](https://nvd.nist.gov/), used as a CVE fallback source.
- [Groq](https://groq.com/) for hosted language-model inference.
- [Hugging Face Sentence Transformers](https://www.sbert.net/) for local embeddings.

Review the terms and licenses of each upstream source before redistributing data or deploying the application commercially.

## Security and privacy notes

- Treat prompts and generated answers as potentially sensitive if they contain internal incident details.
- Do not place secrets, credentials, private indicators, or proprietary incident data in public deployments without appropriate controls.
- Validate retrieved sources and generated recommendations before taking defensive or operational action.
- Keep dependencies, source datasets, and deployment images updated.
- Restrict CORS, authentication, and network access before exposing the API beyond a trusted development environment.

## Contributing

1. Fork the repository and create a feature branch.
2. Make focused changes with clear commit messages.
3. Update documentation and tests when behavior changes.
4. Verify the application locally before opening a pull request.

## License

No license file is currently included in this repository. Unless a license is added, the default copyright rules apply and reuse or redistribution may be restricted. Add a license file before publishing the project for broader reuse.
