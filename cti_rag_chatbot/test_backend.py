import os
import pytest

from backend import app, load_chain, retriever, chain


def ensure_index():
    # run injest if index isn't present
    faiss_dir = os.path.join(os.path.dirname(__file__), "faiss_index")
    index_file = os.path.join(faiss_dir, "index.faiss")
    if not os.path.exists(index_file):
        # import and run injest script
        from injest import create_vector_db, parse_stix, load_stix_json
        stix = load_stix_json()
        docs = parse_stix(stix)
        create_vector_db(docs)


@pytest.fixture(autouse=True)
def initialize_chain(tmp_path, monkeypatch):
    # ensure index is available before loading
    ensure_index()
    load_chain()
    yield


def test_greeting():
    with app.test_client() as client:
        resp = client.post("/api/chat", json={"question": "Hello"})
        assert resp.status_code == 200
        data = resp.get_json()
        assert "answer" in data
        assert "Cyber Threat Intelligence" in data["answer"]
        assert data["sources"] == []


def test_empty_question():
    with app.test_client() as client:
        resp = client.post("/api/chat", json={"question": ""})
        assert resp.status_code == 400
        assert resp.get_json()["error"] == "Question cannot be empty."


def test_retrieval():
    # test that a real query returns sources and context
    with app.test_client() as client:
        resp = client.post("/api/chat", json={"question": "phishing"})
        assert resp.status_code == 200
        data = resp.get_json()
        # should return at least an answer and a non-empty sources list
        assert "answer" in data and isinstance(data["answer"], str)
        assert data.get("sources")
        # context may be large; ensure it's present if returned
        if "context" in data:
            assert isinstance(data["context"], str)
