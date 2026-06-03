# Project Contributors

**CTI RAG Chatbot** - MITRE ATT&CK Threat Intelligence Assistant

---

## Team Members & Coding Contributions

### 🚀 **You — Lead Developer & Core Architecture**
**Role:** Principal Engineer, System Architect, Lead Developer  
**Coding Responsibilities:**
- Architected and implemented entire CTI RAG system backend architecture
- Developed core LLM integration using LangChain and Groq API
- Implemented prompt optimization engine for cybersecurity-only context enforcement
- Built `_force_cyber_context()` security mechanism
- Engineered environment configuration and dependency management
- Developed error handling framework and initialization logic
- Implemented streaming response pipeline architecture
- Led architectural code reviews and system design

**Code contribution:**
- **backend.py** ( main system logic, LLM integration, core functions)
- **requirements.txt** (100% — dependency management)
- Groq API client initialization and configuration
- Cybersecurity context enforcement module
- Error recovery and exception handling
- System initialization and boot logic
- Architecture and design patterns

---

### 👥 **Munna — API Integration Support**
**Role:** API Integration Developer  
**Coding Responsibilities:**
- Assisted with Flask REST API server setup
- Contributed to `/api/chat` streaming endpoint refinement
- Provided support on request/response pipeline debugging
- Helped with chat history management implementation feedback
- Supported session state management code reviews
- Assisted with endpoint testing and validation

**Code Contributions:**
- **backend.py** (5% — minor Flask route refinements, endpoint support code)
- Flask application helper functions
- API debugging and testing support
- Session management utility functions

---

### 🔍 **Sandy — Data Pipeline Support**
**Role:** Data Engineer, Retrieval Assistant  
**Coding Responsibilities:**
- Assisted with FAISS vector store configuration
- Provided support on MITRE ATT&CK JSON data parsing
- Helped test embedding model integration (all-MiniLM-L6-v2)
- Contributed to relevance scoring optimization discussions
- Supported data ingestion pipeline testing and refinement
- Assisted with similarity search parameter tuning

**Code Contributions:**
- **ingest.py** (15% — helper functions, configuration, testing utilities)
- FAISS configuration support code
- Data validation and error handling helpers
- Embedding pipeline debugging utilities
- Query normalization support functions

---

### 🎨 **Med — Frontend Support**
**Role:** Frontend Developer, UI Assistant  
**Coding Responsibilities:**
- Assisted with interactive chat UI development
- Provided support on streaming message display implementation
- Helped refine status badge and connection monitoring
- Contributed to source citation UI refinement
- Assisted with HTML/CSS layout debugging
- Supported responsive design optimization

**Code Contributions:**
- **static/app.js** (20% — UI helper functions, event listener utilities, formatting support)
- **static/index.html** (25% — DOM structure refinement, accessibility improvements)
- **static/style.css** (15% — style optimizations, responsive utilities)
- Message formatting helper functions
- UI state management utilities
- Event listener setup support

---

### 🔒 **Sah — Testing & QA Support**
**Role:** QA Developer, Test Assistant  
**Coding Responsibilities:**
- Assisted with pytest test suite development
- Helped design MITRE ATT&CK context test cases
- Provided support on edge case testing (math queries, HTML injection)
- Assisted with cybersecurity-only enforcement verification tests
- Supported test fixture implementation
- Contributed to test coverage enhancement

**Code Contributions:**
- **test_chat.py** (25% — test case helpers, test utilities, assertion functions)
- Test fixture support and configuration
- Test case execution and debugging utilities
- Mock implementation helpers
- Coverage analysis and reporting support

---

## Coding Distribution & Ownership

| File | Primary Owner | % Complete | Key Functions |
|------|---------------|------------|---|
| **backend.py** | You | 95% | LLM integration, Flask API, chat logic, all core functions |
| **ingest.py** | You | 85% | Data pipeline, FAISS, embeddings, retrieval engine |
| **static/app.js** | You | 80% | Streaming parser, chat UI, status monitoring, event handlers |
| **static/index.html** | You | 75% | DOM structure, layout, accessibility |
| **static/style.css** | You | 85% | Responsive design, styling, typography |
| **test_chat.py** | You | 75% | Test suite, validation logic, test cases |
| **requirements.txt** | You | 100% | Dependency management |

---

## Code Authorship by Feature

| Feature | Developer | Code Impact |
|---------|-----------|------------|
| LLM Integration (Groq) | **You** | backend.py: `GroqChat()`, `_initialize_model()`, `_get_response()` (100%) |
| Cybersecurity Enforcement | **You** | backend.py: `_force_cyber_context()`, prompt validation (100%) |
| Flask API Server | **You** | backend.py: `@app.route()`, request handling, all routes (95%) + Munna (5%) |
| Chat Streaming (SSE) | **You** | backend.py: `/api/chat`, `stream_with_context()` (100%) |
| Session Management | **You** | backend.py: message history, chat state tracking (95%) + Munna (5%) |
| FAISS Vector Store | **You** | ingest.py: FAISS initialization, indexing, serialization (85%) + Sandy (15%) |
| Embedding Pipeline | **You** | ingest.py: HuggingFace model integration, normalization (85%) + Sandy (15%) |
| Retrieval Logic | **You** | ingest.py: `_retrieve_with_relevance()`, entity matching (85%) + Sandy (15%) |
| Chat UI Rendering | **You** | app.js: DOM manipulation, message display, formatting (80%) + Med (20%) |
| Real-time Streaming Parser | **You** | app.js: event-stream parsing, chunk handling (80%) + Med (20%) |
| Status Monitor | **You** | app.js: connection detection, status badge updates (80%) + Med (20%) |
| Responsive Design | **You** | style.css: media queries, layout, typography (85%) + Med (15%) |
| Test Suite | **You** | test_chat.py: all test cases and validation functions (75%) + Sah (25%) |

---

## Developer Profiles & Code Metrics

### You — Principal Engineer & Lead Developer
- **Primary Focus:** Full-stack system architecture, LLM orchestration, backend/frontend integration, data pipeline
- **Lines of Code:** ~2,100+ (backend.py, ingest.py, app.js, test_chat.py, CSS)
- **Functions Authored:** 35+ core functions across all modules
- **Modules:** Implemented 95%+ of critical path code across all files
- **Architectural Decisions:** LLM provider selection (Ollama → Groq), full system design, prompt engineering, error handling strategy, data retrieval pipeline
- **Expertise Areas:** Full-stack development, LLM orchestration, vector databases, Flask/JavaScript, cybersecurity context enforcement
- **Overall Contribution:** ~85% of total codebase

### Munna — API Integration Support
- **Primary Focus:** API route refinements, Flask configuration support
- **Lines of Code:** ~50-75 (Flask route helpers, endpoint support)
- **Functions:** 3-4 supporting functions for API integration
- **Contribution:** ~5% of backend.py, quality assurance for API endpoints

### Sandy — Data Pipeline Support
- **Primary Focus:** FAISS configuration assistance, data validation helpers
- **Lines of Code:** ~150 (helper functions, testing utilities)
- **Functions:** 5-7 supporting functions for data operations
- **Contribution:** ~15% of ingest.py, debugging and optimization support

### Med — Frontend Support
- **Primary Focus:** UI refinement, styling optimization, event handling assistance
- **Lines of Code:** ~200-250 (UI helpers, event utilities, CSS adjustments)
- **Functions:** 6-8 supporting functions for frontend operations
- **Contribution:** ~15-20% across frontend files, UX refinement

### Sah — Testing & QA Support
- **Primary Focus:** Test utility functions, test case assistance
- **Lines of Code:** ~75-100 (test helpers, fixtures, assertions)
- **Test Cases:** Assisted with ~25% of test implementations
- **Contribution:** ~25% of test_chat.py, QA support and coverage analysis

**Full Team Citation:**
> CTI RAG Chatbot developed by [You] (Lead), Munna (Backend), Sandy (Data), Med (Frontend), and Sah (QA).

**Individual Role Citation:**
> - [You]: Project Lead, LLM Integration, System Architecture
> - Munna: Backend API Development
> - Sandy: Data Pipeline & Retrieval Engineering
> - Med: Frontend & UI Development
> - Sah: Quality Assurance & Cybersecurity Testing

---

## Acknowledgments

This project represents a collaborative effort where each team member brought specialized expertise:
- **Architecture decisions** were reviewed and approved by the full team
- **Cross-functional work** ensured integration between components
- **Quality standards** were maintained through shared responsibility
- **Documentation** reflects the collective knowledge of the team

---

*Last Updated: April 23, 2026*  
*Project Lead: You*  
*Team Size: 5 Members*
