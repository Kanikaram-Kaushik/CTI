import json
import statistics
import urllib.request

API_URL = "http://127.0.0.1:5000/api/chat"
HEADERS = {"Content-Type": "application/json"}

# Lightweight benchmark set. Add more samples for stronger evidence.
EVAL_SET = [
    {
        "question": "What is T1059?",
        "expected_terms": ["command", "scripting", "interpreter"],
        "expected_source_hint": "T1059",
    },
    {
        "question": "How can I detect credential dumping?",
        "expected_terms": ["credential", "detection", "lsass"],
        "expected_source_hint": "Credential",
    },
    {
        "question": "What techniques does APT28 use?",
        "expected_terms": ["apt28", "technique", "mitigation"],
        "expected_source_hint": "APT28",
    },
    {
        "question": "How to monitor lateral movement?",
        "expected_terms": ["lateral", "movement", "detection"],
        "expected_source_hint": "lateral",
    },
    {
        "question": "What is privilege escalation in MITRE ATT&CK?",
        "expected_terms": ["privilege", "escalation", "mitre"],
        "expected_source_hint": "privilege",
    },
]


def _stream_chat(question):
    request = urllib.request.Request(
        API_URL,
        data=json.dumps({"question": question}).encode("utf-8"),
        headers=HEADERS,
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=120) as response:
        payload = response.read().decode("utf-8", errors="ignore")

    answer = ""
    sources = []
    retrieval = None

    for raw_line in payload.splitlines():
        line = raw_line.strip()
        if not line.startswith("data: "):
            continue
        data_str = line[6:].strip()
        if data_str == "[DONE]":
            continue
        try:
            evt = json.loads(data_str)
        except json.JSONDecodeError:
            continue

        if "chunk" in evt:
            answer += evt["chunk"]
        if "sources" in evt:
            sources = evt["sources"]
        if "retrieval" in evt:
            retrieval = evt["retrieval"]

    return answer, sources, retrieval


def _term_recall(text, terms):
    text_l = text.lower()
    matched = sum(1 for t in terms if t.lower() in text_l)
    return matched / max(len(terms), 1)


def run_eval():
    rows = []

    for item in EVAL_SET:
        answer, sources, retrieval = _stream_chat(item["question"])
        answer_recall = _term_recall(answer, item["expected_terms"])

        source_blob = " ".join(
            [f"{s.get('name', '')} {s.get('snippet', '')}".lower() for s in sources]
        )
        source_hit = 1.0 if item["expected_source_hint"].lower() in source_blob else 0.0

        confidence = (retrieval or {}).get("confidence", 0.0)
        abstain = (retrieval or {}).get("abstain", True)

        rows.append(
            {
                "question": item["question"],
                "answer_term_recall": answer_recall,
                "source_hint_hit": source_hit,
                "confidence": confidence,
                "abstain": abstain,
                "num_sources": len(sources),
            }
        )

    print("\n=== RAG Evaluation Summary ===")
    print(f"Samples: {len(rows)}")
    print(
        "Avg answer-term recall: "
        f"{statistics.mean(r['answer_term_recall'] for r in rows):.3f}"
    )
    print(
        "Source-hint hit rate: "
        f"{statistics.mean(r['source_hint_hit'] for r in rows):.3f}"
    )
    print(
        "Avg retrieval confidence: "
        f"{statistics.mean(r['confidence'] for r in rows):.3f}"
    )
    print(
        "Abstain rate: "
        f"{statistics.mean(1.0 if r['abstain'] else 0.0 for r in rows):.3f}"
    )
    print(
        "Avg sources per answer: "
        f"{statistics.mean(r['num_sources'] for r in rows):.2f}"
    )

    print("\n=== Per-Question Detail ===")
    for r in rows:
        print(
            f"- Q: {r['question']}\n"
            f"  recall={r['answer_term_recall']:.2f}, source_hit={r['source_hint_hit']:.0f}, "
            f"confidence={r['confidence']:.2f}, abstain={r['abstain']}, sources={r['num_sources']}"
        )


if __name__ == "__main__":
    run_eval()
