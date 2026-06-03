# 5-Member Presentation Script for CTI RAG Chatbot

## 1. You: Introduction, Problem, and Objective

Good morning everyone. I am You, the Project Lead, and I will start by introducing our project.

Our project is a Cyber Threat Intelligence RAG Chatbot built using the MITRE ATT&CK framework. The main problem we are solving is that cybersecurity analysts often need quick and reliable answers about attack techniques, threat groups, malware, detections, and mitigations. But manually searching large documents takes time and can lead to missed context.

The objective of our project is to make this process faster and smarter. Instead of reading long documents manually, a user can ask a question in natural language, and the system gives a grounded answer based on MITRE ATT&CK data. So, the system is designed to support defensive cybersecurity research, not offensive misuse.

The importance of this project is very high because in cyber incident response, time matters. If an analyst gets the wrong answer or takes too long, it can affect the response quality. That is why we focused on building a system that is both fast and trustworthy.

## 2. Munna: Dataset and Methodology

I am Munna, and I will explain the dataset and methodology. In our final workload split, I handled frontend responsibilities originally planned for Med.

We use the MITRE ATT&CK Enterprise dataset in STIX JSON format. This dataset is very valuable because it contains structured threat intelligence objects such as attack-pattern, intrusion-set, malware, tool, and course-of-action. It gives us both metadata and descriptive text that can be used for semantic search.

Our preprocessing starts by loading the STIX file from the local data folder or downloading it from MITRE if needed. Then we filter only the relevant CTI object types. After that, we extract key fields like the object name, ID, type, and URL, and convert the data into readable text chunks.

For embeddings, we use all-MiniLM-L6-v2, and then we store the vectors in FAISS. The reason we chose this method is that Retrieval-Augmented Generation works better for cybersecurity knowledge than a simple chatbot. CTI changes often, so retrieval-based updating is easier than retraining a model again and again.

## 3. Sandy: Architecture and Workflow

I am Sandy, and I will explain the architecture and workflow. In our final workload split, I handled API integration responsibilities originally planned for Munna.

Our system has four main layers. The first layer is the frontend, where the user asks questions in the web interface. The second layer is the Flask backend, which receives the request and handles the chat logic. The third layer is the retrieval and generation layer, where the question is rewritten if needed, relevant documents are retrieved from FAISS, and the LLM generates the response. The fourth layer is the data layer, which contains the MITRE ATT&CK dataset and the FAISS vector index.

The workflow is very simple. First, the user asks a question. Second, the backend rewrites the query into cybersecurity context if necessary. Third, FAISS retrieves the most relevant documents. Fourth, the LLM produces an answer using that context. Fifth, the hallucination guard checks whether the answer is supported by the retrieved content. Finally, the answer and source references are returned to the user.

This architecture is useful because it keeps the answer grounded in trusted CTI sources and makes the system easier to maintain.

## 4. Med: Results and Critical Analysis

I am Med, and I will discuss the results and critical analysis. In our final workload split, I handled data pipeline responsibilities originally planned for Sandy.

The repository does not show a full formal benchmark table, but it does define clear performance targets in the documentation. For example, the system aims for fast response time, quick FAISS retrieval, and low hallucination. The SRS also mentions requirements like query latency under 1.5 seconds, retrieval in under 50 milliseconds, and hallucination rate below 5 percent on test queries.

The best-performing model in the design is the Groq-hosted Mixtral model because it gives the strongest balance of speed and quality. If the cloud model is not available, the system can fall back to a local Ollama model.

In our opinion, the results are convincing from a design perspective because the system is strongly grounded and defensive. However, the paper would be even stronger if it included measured experimental results, such as retrieval accuracy, response latency tests, and human evaluation of answer quality.

The main limitations are that some claims are target values rather than measured values, and the system depends on external LLM availability when using the cloud model.

## 5. Sah: Learning, Innovation, and Closing

I am Sah, and I will explain the innovation, learning, and conclusion.

The most innovative part of this project is that it combines MITRE ATT&CK, semantic retrieval, RAG, query rewriting, and hallucination control into one cybersecurity assistant. This is more than just a chatbot. It is a defensive CTI assistant that gives source-based and auditable answers.

This project can be improved in the future by adding a real evaluation dataset, measuring precision and recall for retrieval, supporting more threat intelligence sources like CVEs and incident reports, and adding confidence scoring or knowledge graphs.

In the real world, this system can help SOC analysts, incident response teams, threat hunters, purple teams, and students. It can reduce research time and make cyber threat intelligence easier to understand.

To conclude, our project shows that Retrieval-Augmented Generation is a practical and effective approach for cybersecurity knowledge access. It helps users get faster, safer, and more trustworthy answers.

Thank you.

## Added Segment: MITRE plus OWASP Integration

**You:** Along with MITRE ATT&CK grounding, we integrated OWASP guidance to strengthen practical web-application defense mapping.

**Munna:** In the UI sidebar, we added direct links to OWASP Top 10, OWASP ASVS, and the OWASP Cheat Sheet Series so users can quickly move from threat context to secure coding controls.

**Sandy:** In the backend response stream, we now send contextual OWASP references for each query. For example, authentication-related questions can map to A07 and the Authentication Cheat Sheet.

**Med:** In the chat response panel, users can expand an "OWASP guidance" section and see relevant OWASP links with reasons, just like they can expand MITRE sources.

**Sah:** This MITRE plus OWASP approach improves explainability and review quality because our answers now connect threat intelligence with recognized application security standards.

## Short Rehearsal Summary

- You: Problem, objective, importance
- Munna: Dataset, preprocessing, methodology
- Sandy: Architecture, modules, workflow
- Med: Results, model choice, limitations
- Sah: Innovation, applications, conclusion

## Corrected Contribution Note

- Munna handled frontend work (Med's original allocation).
- Sandy handled API integration work (Munna's original allocation).
- Med handled data pipeline and retrieval support work (Sandy's original allocation).