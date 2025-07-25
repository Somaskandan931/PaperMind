# backend/embedding_utils.py

import os
import json
import openai
import faiss
import numpy as np

EMBEDDING_MODEL = "text-embedding-ada-002"
openai.api_key = os.getenv("OPENAI_API_KEY")

INDEX_FILE = "data/faiss_index.index"
METADATA_FILE = "data/papers.json"


def get_embedding(text: str) -> list:
    """Generate embedding for a given text using OpenAI."""
    response = openai.Embedding.create(
        input=text,
        model=EMBEDDING_MODEL
    )
    return response['data'][0]['embedding']


def build_faiss_index(paper_list: list, save=True):
    """
    Builds FAISS index from a list of papers.
    Each paper must have a 'title' and 'abstract'.
    """
    embeddings = []
    metadata = []

    for paper in paper_list:
        text = f"{paper['title']}\n{paper['abstract']}"
        emb = get_embedding(text)
        embeddings.append(emb)
        metadata.append(paper)

    dim = len(embeddings[0])
    index = faiss.IndexFlatL2(dim)
    index.add(np.array(embeddings).astype("float32"))

    if save:
        faiss.write_index(index, INDEX_FILE)
        with open(METADATA_FILE, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

    return index, metadata


def load_faiss_index():
    """Load FAISS index and associated metadata."""
    index = faiss.read_index(INDEX_FILE)
    with open(METADATA_FILE, "r", encoding="utf-8") as f:
        metadata = json.load(f)
    return index, metadata


def search_similar_papers(query: str, top_k=5):
    """Return top_k most relevant papers for a query."""
    index, metadata = load_faiss_index()
    query_embedding = get_embedding(query)
    query_vec = np.array([query_embedding]).astype("float32")

    D, I = index.search(query_vec, top_k)
    results = [metadata[i] for i in I[0]]
    return results
