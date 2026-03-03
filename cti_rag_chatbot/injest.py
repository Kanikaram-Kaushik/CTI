import os
import json
import requests
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from dotenv import load_dotenv

load_dotenv()

# ── Configuration ─────────────────────────────────────────────────────────────
# Drop your MITRE ATT&CK STIX JSON here (enterprise-attack.json or similar)
LOCAL_STIX_FILE  = "data/enterprise-attack.json"

# Fallback: download from MITRE GitHub if no local file is found
MITRE_STIX_URL   = "https://raw.githubusercontent.com/mitre/cti/master/enterprise-attack/enterprise-attack.json"

FAISS_INDEX_PATH = "faiss_index"
EMBEDDING_MODEL  = "all-MiniLM-L6-v2"

STIX_TYPES = {"attack-pattern", "course-of-action", "intrusion-set", "malware", "tool"}


def load_stix_json() -> dict:
    """Load STIX JSON from a local file if it exists, otherwise download it."""
    if os.path.exists(LOCAL_STIX_FILE):
        print(f"📂 Loading local STIX file: {LOCAL_STIX_FILE}")
        with open(LOCAL_STIX_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        print(f"⚠️  Local file '{LOCAL_STIX_FILE}' not found.")
        print(f"🌐 Downloading from: {MITRE_STIX_URL}")
        response = requests.get(MITRE_STIX_URL, timeout=120)
        response.raise_for_status()
        # Save locally for next run so you don't download again
        os.makedirs("data", exist_ok=True)
        with open(LOCAL_STIX_FILE, "w", encoding="utf-8") as f:
            f.write(response.text)
        print(f"✅ Saved to '{LOCAL_STIX_FILE}' for future use.")
        return response.json()


def parse_stix(stix_data: dict) -> list[Document]:
    """Extract useful objects from STIX bundle into LangChain Documents."""
    objects = stix_data.get("objects", [])
    print(f"📊 Processing {len(objects)} STIX objects…")

    documents = []
    for obj in objects:
        if obj.get("type") not in STIX_TYPES:
            continue
        description = obj.get("description", "").strip()
        if not description:
            continue

        name = obj.get("name", "Unknown")
        content = (
            f"Name: {name}\n"
            f"Type: {obj.get('type')}\n"
            f"Description: {description}"
        )
        metadata = {
            "id":   obj.get("id", ""),
            "name": name,
            "type": obj.get("type", ""),
            "url":  obj.get("external_references", [{}])[0].get("url", ""),
        }
        documents.append(Document(page_content=content, metadata=metadata))

    print(f"✅ Loaded {len(documents)} documents.")
    return documents


def create_vector_db(documents: list[Document]):
    """Chunk documents, embed them, and save to FAISS index."""
    print("✂️  Chunking documents…")
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks   = splitter.split_documents(documents)
    print(f"   → {len(chunks)} chunks created.")

    print(f"🧠 Loading embedding model '{EMBEDDING_MODEL}'…")
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)

    print("⚙️  Building FAISS index (this may take a few minutes)…")
    vector_store = FAISS.from_documents(chunks, embeddings)

    print(f"💾 Saving index to '{FAISS_INDEX_PATH}'…")
    vector_store.save_local(FAISS_INDEX_PATH)
    print("🎉 Done! FAISS index created successfully.")


if __name__ == "__main__":
    stix_data = load_stix_json()
    docs      = parse_stix(stix_data)
    if docs:
        create_vector_db(docs)
    else:
        print("❌ No documents found to process.")
