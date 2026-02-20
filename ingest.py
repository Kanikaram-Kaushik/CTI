import os
import requests
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
MITRE_STIX_URL = "https://raw.githubusercontent.com/mitre/cti/master/enterprise-attack/enterprise-attack.json"
FAISS_INDEX_PATH = "faiss_index"

# Free local embedding model (no API key needed)
EMBEDDING_MODEL = "all-MiniLM-L6-v2"


def load_mitre_data():
    """Download and parse MITRE ATT&CK STIX data."""
    print(f"Downloading MITRE ATT&CK data from {MITRE_STIX_URL}...")
    response = requests.get(MITRE_STIX_URL, timeout=60)
    response.raise_for_status()
    stix_data = response.json()

    documents = []
    objects = stix_data.get("objects", [])

    print(f"Processing {len(objects)} STIX objects...")

    for obj in objects:
        if obj.get("type") in ["attack-pattern", "course-of-action", "intrusion-set", "malware", "tool"]:
            name = obj.get("name", "Unknown")
            description = obj.get("description", "")

            if not description:
                continue

            content = f"Name: {name}\nType: {obj.get('type')}\nDescription: {description}"

            metadata = {
                "id": obj.get("id"),
                "name": name,
                "type": obj.get("type"),
                "url": obj.get("external_references", [{}])[0].get("url", ""),
            }

            documents.append(Document(page_content=content, metadata=metadata))

    print(f"Loaded {len(documents)} documents.")
    return documents


def create_vector_db(documents):
    """Create FAISS vector store from documents using local embeddings."""
    print("Chunking documents...")
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = text_splitter.split_documents(documents)
    print(f"Created {len(chunks)} chunks.")

    print(f"Loading local embedding model '{EMBEDDING_MODEL}'...")
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)

    print("Generating embeddings and creating FAISS index (this may take several minutes)...")
    vector_store = FAISS.from_documents(chunks, embeddings)

    print(f"Saving FAISS index to '{FAISS_INDEX_PATH}'...")
    vector_store.save_local(FAISS_INDEX_PATH)
    print("Done! FAISS index created successfully.")


if __name__ == "__main__":
    docs = load_mitre_data()
    if docs:
        create_vector_db(docs)
    else:
        print("No documents found to process.")
