"""
vectorstore.py
---------------
Handles embedding + storing + retrieving documents (trial data + rep notes)
using a local ChromaDB database and a free, local sentence-transformers
embedding model (no extra API key needed for embeddings).

This is the "R" (retrieval) in RAG.
"""

import chromadb
from chromadb.utils import embedding_functions
from typing import List, Dict, Optional

DB_PATH = "./chroma_db"
COLLECTION_NAME = "life_sciences_kb"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"  # small, fast, runs on CPU


def get_collection():
    client = chromadb.PersistentClient(path=DB_PATH)
    embed_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=EMBEDDING_MODEL
    )
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=embed_fn,
    )
    return collection


def add_documents(docs: List[Dict]):
    """
    docs: list of dicts, each must have at least 'id' and 'text'.
    Any other keys are stored as metadata (used later for filtering).
    """
    if not docs:
        return

    collection = get_collection()

    ids = [d["id"] for d in docs]
    texts = [d["text"] for d in docs]
    metadatas = []
    for d in docs:
        meta = {k: v for k, v in d.items() if k not in ("id", "text")}
        # Chroma metadata values must be str/int/float/bool
        meta = {k: ("" if v is None else str(v)) for k, v in meta.items()}
        metadatas.append(meta)

    # Upsert so re-running ingestion doesn't create duplicates
    collection.upsert(ids=ids, documents=texts, metadatas=metadatas)
    print(f"Indexed {len(ids)} documents into '{COLLECTION_NAME}'.")

def query(
    query_text: str,
    n_results: int = 6,
    where: Optional[Dict] = None
) -> List[Dict]:
    """
    Semantic search over the indexed documents.

    Supports metadata filtering such as:
        {"source_type": "rep_note"}

    For multiple metadata conditions, they are combined with
    ChromaDB's $and operator.
    """
    collection = get_collection()

    if where and len(where) > 1:
        where = {
            "$and": [
                {key: value}
                for key, value in where.items()
            ]
        }

    results = collection.query(
        query_texts=[query_text],
        n_results=n_results,
        where=where,
    )

    hits = []

    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    ids = results.get("ids", [[]])[0]

    for doc_id, doc_text, meta in zip(ids, docs, metas):
        hits.append({
            "id": doc_id,
            "text": doc_text,
            **meta
        })

    return hits
def reset_collection():
    """Wipe the collection — useful during development."""
    client = chromadb.PersistentClient(path=DB_PATH)
    try:
        client.delete_collection(COLLECTION_NAME)
        print(f"Deleted collection '{COLLECTION_NAME}'.")
    except Exception:
        pass
