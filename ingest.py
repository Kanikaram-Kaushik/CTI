import os
import json
import requests
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
LOCAL_STIX_FILE  = "data/enterprise-attack.json"
MITRE_STIX_URL   = "https://raw.githubusercontent.com/mitre/cti/master/enterprise-attack/enterprise-attack.json"
FAISS_INDEX_PATH  = "faiss_index"

# Free local embedding model (no API key needed)
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

STIX_TYPES = {"attack-pattern", "course-of-action", "intrusion-set", "malware", "tool"}


def load_mitre_data():
    """Load STIX JSON from a local file if it exists, otherwise download it."""
    if os.path.exists(LOCAL_STIX_FILE):
        print(f"Loading local STIX file: {LOCAL_STIX_FILE}")
        with open(LOCAL_STIX_FILE, "r", encoding="utf-8") as f:
            stix_data = json.load(f)
    else:
        print(f"Local file '{LOCAL_STIX_FILE}' not found.")
        try:
            print(f"Downloading MITRE ATT&CK data from {MITRE_STIX_URL}...")
            response = requests.get(MITRE_STIX_URL, timeout=120)
            response.raise_for_status()
            stix_data = response.json()
            # Save locally for next run so you don't download again
            os.makedirs("data", exist_ok=True)
            with open(LOCAL_STIX_FILE, "w", encoding="utf-8") as f:
                json.dump(stix_data, f)
            print(f"Saved to '{LOCAL_STIX_FILE}' for future use.")
        except Exception as e:
            print(f"\n✗ ERROR: Cannot download from internet ({e})")
            print("Please provide the enterprise-attack.json file locally at: data/enterprise-attack.json")
            return None

    documents = []
    objects = stix_data.get("objects", [])

    print(f"Processing {len(objects)} STIX objects...")

    for obj in objects:
        if obj.get("type") not in STIX_TYPES:
            continue

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
    cache_dir = os.path.expanduser("~/.cache/huggingface/hub")
    
    try:
        embeddings = HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL,
            cache_folder=cache_dir,
            show_progress=True,
        )
    except Exception as e:
        print(f"✗ ERROR: Failed to load embedding model: {e}")
        print(f"Please download the model first: python download_embedding_model.py")
        raise

    print("Generating embeddings and creating FAISS index (this may take several minutes)...")
    vector_store = FAISS.from_documents(chunks, embeddings)

    print(f"Saving FAISS index to '{FAISS_INDEX_PATH}'...")
    vector_store.save_local(FAISS_INDEX_PATH)
    print("[OK] Done! FAISS index created successfully.")


def load_owasp_data():
    """Download OWASP Cheat Sheet Series and load markdown files."""
    owasp_dir = "data/CheatSheetSeries"
    if not os.path.exists(owasp_dir):
        print("Cloning OWASP CheatSheetSeries...")
        try:
            import subprocess
            subprocess.run(["git", "clone", "--depth", "1", "https://github.com/OWASP/CheatSheetSeries.git", owasp_dir], check=True)
        except Exception as e:
            print(f"✗ ERROR: Cannot clone OWASP CheatSheetSeries ({e})")
            return []
    
    import glob
    md_files = glob.glob(f"{owasp_dir}/docs/cheatsheets/*.md")
    print(f"Processing {len(md_files)} OWASP markdown files...")
    
    documents = []
    for filepath in md_files:
        filename = os.path.basename(filepath)
        name = filename.replace(".md", "").replace("_", " ")
        url = f"https://cheatsheetseries.owasp.org/cheatsheets/{filename.replace('.md', '.html')}"
        
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            
            doc_content = f"Name: {name} (OWASP Cheat Sheet)\nType: owasp-cheatsheet\nDescription: Security guidance and best practices.\n\n{content}"
            
            metadata = {
                "id": filename,
                "name": name,
                "type": "owasp-cheatsheet",
                "url": url,
            }
            documents.append(Document(page_content=doc_content, metadata=metadata))
        except Exception as e:
            print(f"Warning: could not read {filepath} ({e})")
            
    print(f"Loaded {len(documents)} OWASP documents.")
    return documents


if __name__ == "__main__":
    docs = load_mitre_data() or []
    owasp_docs = load_owasp_data() or []
    all_docs = docs + owasp_docs
    if all_docs:
        create_vector_db(all_docs)
        print("\n[OK] Ingestion complete! Your app now has the MITRE ATT&CK and OWASP data.")
    else:
        print("\n[ERROR] No documents found to process.")
        import sys
        sys.exit(1)
