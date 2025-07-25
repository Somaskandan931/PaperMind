from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import requests, faiss, os
from dotenv import load_dotenv
import openai

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

app = FastAPI()

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class Query(BaseModel):
    text: str

class Paper(BaseModel):
    title: str
    abstract: str
    url: str

# Cache (simple in-memory)
paper_data = []
index = None
paper_embeddings = []

# ------------------------
# 1. Fetch papers from Semantic Scholar
# ------------------------
def fetch_papers(query: str, limit=10):
    global paper_data
    url = f"https://api.semanticscholar.org/graph/v1/paper/search?query={query}&limit={limit}&fields=title,abstract,url"
    response = requests.get(url)
    data = response.json()
    papers = []

    for item in data.get("data", []):
        if item.get("abstract"):
            papers.append({
                "title": item["title"],
                "abstract": item["abstract"],
                "url": item["url"]
            })

    paper_data = papers
    return papers

# ------------------------
# 2. Embed using OpenAI
# ------------------------
def get_embedding(text):
    response = openai.Embedding.create(
        input=text,
        model="text-embedding-3-small"
    )
    return response['data'][0]['embedding']

# ------------------------
# 3. Build FAISS index
# ------------------------
def build_index(papers):
    global index, paper_embeddings
    dim = 1536
    index = faiss.IndexFlatL2(dim)
    vectors = []

    for paper in papers:
        emb = get_embedding(paper["abstract"])
        vectors.append(emb)

    paper_embeddings = vectors
    index.add(np.array(vectors).astype("float32"))

# ------------------------
# 4. Recommend route
# ------------------------
import numpy as np

@app.post("/recommend")
def recommend(query: Query):
    global index, paper_data, paper_embeddings

    if index is None or not paper_data:
        # Fetch new papers and build index
        papers = fetch_papers(query.text)
        if not papers:
            raise HTTPException(status_code=404, detail="No papers found.")
        build_index(papers)

    query_emb = np.array(get_embedding(query.text)).astype("float32")
    D, I = index.search(np.array([query_emb]), k=5)

    results = []
    for idx in I[0]:
        paper = paper_data[idx]
        results.append(paper)

    return {"papers": results}
