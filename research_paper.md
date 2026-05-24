# CTI RAG Chatbot for MITRE ATT&CK Threat Intelligence

Final Submission

Prepared by: Anti-RTRP Project Team

Date: May 9, 2026

## Abstract
Cyber threat intelligence teams need fast, accurate, and context-aware answers about adversary behavior, mitigation options, and detection opportunities. This project presents a retrieval-augmented generation (RAG) chatbot that answers cybersecurity questions using MITRE ATT&CK as its primary knowledge source. The system combines a local FAISS vector index built from ATT&CK STIX data, a lightweight lexical reranker, and a cloud-hosted large language model served through Flask. To improve trustworthiness, the assistant applies a confidence-based abstention policy and only responds when retrieval evidence is strong enough. The application also augments answers with OWASP guidance and optionally persists chat history in MongoDB. The result is a practical CTI assistant that emphasizes grounded responses, safe refusal behavior, and a simple web interface for analyst workflows.

## Keywords
Cyber threat intelligence, MITRE ATT&CK, retrieval-augmented generation, FAISS, Flask, React, OWASP, MongoDB

## 1. Introduction
Threat intelligence analysts and security engineers must often translate raw adversary knowledge into actionable guidance. MITRE ATT&CK is one of the most widely used taxonomies for describing adversary tactics, techniques, procedures, malware, tools, and intrusion sets. However, ATT&CK data is large and difficult to query quickly without a specialized retrieval layer.

This project addresses that problem by building a RAG-based chatbot that accepts natural-language questions and returns responses grounded in ATT&CK content. Instead of relying only on a language model's internal knowledge, the system retrieves relevant ATT&CK passages first and then generates an answer from those passages. This design reduces hallucination risk and makes the assistant more useful in real-world security workflows.

The main contribution of the project is a complete end-to-end CTI assistant pipeline:
- MITRE ATT&CK data ingestion and vector indexing
- Hybrid retrieval using dense and lexical signals
- Confidence scoring and safe abstention when evidence is weak
- Web-based chat interface for interactive use
- Optional MongoDB persistence for previous conversations
- OWASP reference enrichment for security-oriented follow-up guidance

## 2. Background and Motivation
RAG systems are well suited to threat intelligence because the desired answer must usually be grounded in a curated corpus rather than generated from open-ended speculation. In CTI, an incorrect answer can mislead defenders about technique usage, detection ideas, or mitigation priorities. For that reason, this system is designed to prefer grounded refusal over unverified output.

MITRE ATT&CK provides a structured knowledge base for adversary behavior, while OWASP offers complementary application-security guidance. The project links these sources by using ATT&CK for primary retrieval and OWASP references for contextual reinforcement when the user query touches topics such as authentication, injection, logging, or API security.

## 3. System Overview
The application is implemented as a Flask backend with a React frontend. The backend exposes the chat API, serves the built frontend, performs retrieval, and streams responses to the browser. The frontend renders a chat-style interface, shows answer sources, displays retrieval confidence, and supports chat reset and history loading.

At a high level, the workflow is:
1. Load MITRE ATT&CK STIX data.
2. Convert relevant objects into documents.
3. Chunk the text and embed it with a sentence-transformer model.
4. Save the vectors in FAISS.
5. At query time, retrieve candidate chunks with dense and lexical methods.
6. Compute a confidence score and decide whether to answer or abstain.
7. Stream the response and metadata to the client.

## 4. Data Ingestion and Knowledge Base Construction
The ingestion pipeline reads MITRE ATT&CK enterprise STIX data from `data/enterprise-attack.json`, or downloads it from the MITRE ATT&CK GitHub repository if the file is missing. The system keeps only the most relevant STIX object types for CTI Q&A:
- attack-pattern
- course-of-action
- intrusion-set
- malware
- tool

Each object is converted into a document that includes its name, type, and description. Metadata such as object ID and external reference URL are preserved so the assistant can show source information in the frontend.

Before indexing, documents are split into chunks of approximately 1000 characters with 200 characters of overlap. This choice balances retrieval granularity against context continuity. The chunked documents are embedded with `all-MiniLM-L6-v2`, a local sentence-transformer model that does not require an external embedding API. The resulting vectors are saved in a FAISS index under `faiss_index/index.faiss`.

This design keeps the ingestion pipeline lightweight, reproducible, and suitable for local development as well as deployment.

## 5. Retrieval and Answer Generation
The backend uses a hybrid retrieval strategy rather than relying on dense similarity alone. Dense retrieval is performed through FAISS, while a lightweight lexical layer computes term frequencies and document frequencies over the indexed chunks. The lexical score acts as a BM25-like signal that helps exact mention queries and keyword-heavy CTI questions.

The final retrieval score combines three signals:
- dense semantic similarity
- lexical relevance
- token overlap between query and document

In the current implementation, the reranking formula weights dense similarity most heavily, followed by lexical relevance and token overlap. This helps the system handle both concept-level questions and exact ATT&CK entity lookups.

The answer generation step uses a Groq-hosted language model through LangChain. The backend streams the generated response in chunks using Server-Sent Events so the user sees the answer gradually rather than waiting for the full completion. During generation, the system suppresses any reasoning tags and converts markdown-like output into HTML for display.

A critical feature of the system is confidence-based abstention. If retrieval evidence is weak, the assistant refuses to answer rather than guessing. The confidence estimate considers retrieval strength, number of supporting chunks, and whether the query contains an explicit ATT&CK-style entity pattern such as a T-ID or APT identifier. When confidence falls below the abstain threshold, the assistant returns a safe refusal message that directs the user to ask a more specific MITRE ATT&CK question.

This is important for CTI use because a grounded refusal is often better than an uncertain answer.

## 6. Security-Oriented Response Framing
The backend enforces a cybersecurity-only scope. User requests are checked before retrieval, and questions outside MITRE ATT&CK and related defensive content are rejected. This reduces prompt drift and keeps the assistant focused on threat intelligence rather than general-purpose chat.

The system also injects OWASP references when the question suggests a security topic such as credentials, injection, logging, monitoring, or APIs. These references are not the primary knowledge base, but they provide useful supplementary material for analysts who want to extend a CTI answer into secure design or remediation guidance.

This combination of scope enforcement, grounded retrieval, and optional OWASP enrichment helps the assistant stay useful while limiting unsafe or irrelevant output.

## 7. Frontend and User Experience
The frontend is implemented in React and provides a chat-centric interface. It includes:
- an initial assistant message that explains the system purpose
- suggested example prompts for common CTI topics
- streaming message rendering
- source cards with names, types, snippets, and links
- retrieval metadata showing confidence, mode, and abstention status
- expandable OWASP guidance panels
- reset and history functionality

The frontend also queries backend status on load so the user can see whether the model and retrieval pipeline are ready. This improves usability during startup and deployment.

## 8. Persistence and Operational Behavior
The application supports optional MongoDB persistence for chat history. If MongoDB is configured through environment variables, the backend stores each question-answer exchange with retrieval metadata and source information. If MongoDB is unavailable, the system falls back to in-memory history.

The backend exposes the following endpoints:
- `/` serves the frontend build
- `/api/chat` handles streamed question answering
- `/api/reset` clears stored conversation state
- `/api/history` returns prior exchanges
- `/api/status` reports model and readiness information

This small API surface makes the system easy to deploy and integrate.

## 9. Evaluation Strategy
The repository includes a simple test suite for basic behavior such as greeting handling, empty-input validation, and retrieval-related checks. The codebase is also structured so that the retrieval pipeline can be evaluated separately from the user interface.

For a CTI assistant, evaluation should focus on more than raw language quality. Useful criteria include:
- whether answers are grounded in ATT&CK content
- whether the system abstains when retrieval confidence is low
- whether source snippets match the user query
- whether the assistant remains within cybersecurity scope
- whether streaming and persistence work reliably in the browser

The current implementation is optimized for these properties rather than for open-domain conversational breadth. In practical terms, that is the correct tradeoff for a threat-intelligence assistant.

## 10. Limitations and Future Work
Several limitations remain. The system depends on the quality and freshness of the MITRE ATT&CK corpus, so future updates should periodically refresh the STIX source. Retrieval quality also depends on the embedding model and the lexical weighting scheme, which may need tuning for specialized adversary terminology.

Future work could extend the assistant with:
- richer evaluation datasets for CTI question answering
- automated comparison against analyst-written reference answers
- citation-level provenance for every generated claim
- support for more threat intelligence sources beyond ATT&CK
- stronger role-based access control for enterprise deployments
- improved benchmarking of abstention accuracy and false-positive answer rates

## 11. Conclusion
This project demonstrates a focused retrieval-augmented generation system for cyber threat intelligence. By grounding answers in MITRE ATT&CK, combining dense and lexical retrieval, and refusing to answer when evidence is weak, the assistant prioritizes reliability over speculation. The Flask and React implementation makes the system easy to use, while optional MongoDB persistence and OWASP reference enrichment add operational value.

Overall, the project shows that a carefully constrained RAG pipeline can be an effective interface for ATT&CK-driven security analysis.

## References
1. MITRE ATT&CK Enterprise Matrix. https://attack.mitre.org/
2. MITRE CTI STIX repository. https://github.com/mitre/cti
3. OWASP Top 10. https://owasp.org/www-project-top-ten/
4. OWASP Application Security Verification Standard. https://owasp.org/www-project-application-security-verification-standard/
5. OWASP Cheat Sheet Series. https://cheatsheetseries.owasp.org/
