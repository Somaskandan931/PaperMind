from fastapi import FastAPI, HTTPException, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
import requests
import os
import faiss
import numpy as np
from dotenv import load_dotenv
from groq import Groq
import json
import time
import logging
from pathlib import Path
import xml.etree.ElementTree as ET
from datetime import datetime
import asyncio
from sentence_transformers import SentenceTransformer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
api_key = os.getenv("GROQ_API_KEY")

# Groq model — override via GROQ_MODEL env var
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

client = None
if api_key:
    try:
        client = Groq(api_key=api_key)
        logger.info(f"Groq client initialised — model: {GROQ_MODEL}")
    except Exception as e:
        logger.error(f"Failed to initialise Groq client: {e}. LLM features will use fallback text.")
else:
    logger.warning("GROQ_API_KEY not set — LLM features will use fallback text.")

embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

app = FastAPI(
    title="PaperMind Analyst API",
    description="AI-powered research paper analyst with cited synthesis",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Pydantic Models ────────────────────────────────────────────────────────────

class Query(BaseModel):
    text: str
    max_results: Optional[int] = 15
    sources: Optional[List[str]] = ["openalex", "crossref", "arxiv", "semantic_scholar"]


class AnalystQuestion(BaseModel):
    question: str
    paper_ids: List[str]          # IDs of papers currently loaded
    session_papers: List[dict]    # Full paper objects (title + abstract)
    top_k: Optional[int] = 8     # How many chunks to retrieve


class Paper(BaseModel):
    id: str
    title: str
    abstract: str
    authors: List[str]
    published: Optional[str] = None
    url: str
    source: str
    relevance_score: Optional[float] = None
    explanation: Optional[str] = None
    citation_count: Optional[int] = None
    pdf_url: Optional[str] = None


class RecommendationResponse(BaseModel):
    papers: List[Paper]
    query: str
    total_found: int
    processing_time: float


class Citation(BaseModel):
    paper_id: str
    title: str
    authors: List[str]
    url: str
    published: Optional[str] = None
    chunk_text: str   # the specific passage used


class AnalystAnswer(BaseModel):
    question: str
    answer: str                    # synthesised markdown answer
    citations: List[Citation]
    papers_consulted: int
    processing_time: float


# ── Global State ───────────────────────────────────────────────────────────────

EMBEDDING_DIM = 384
faiss_index = None
paper_metadata = []
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)


# ── Embedding Helpers ──────────────────────────────────────────────────────────

def get_embedding(text: str) -> List[float]:
    cleaned = text.replace('\n', ' ').strip()[:512]
    return embedding_model.encode(cleaned, convert_to_tensor=False).tolist()


# ── Chunking ───────────────────────────────────────────────────────────────────

def chunk_paper(paper: dict, chunk_size: int = 200, overlap: int = 40) -> List[dict]:
    """
    Semantic chunking: split abstract into overlapping word windows.
    Each chunk carries the paper's metadata for citation.
    """
    text = f"{paper['title']}. {paper['abstract']}"
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk_text = " ".join(words[start:end])
        chunks.append({
            "paper_id": paper["id"],
            "title": paper["title"],
            "authors": paper.get("authors", []),
            "url": paper.get("url", ""),
            "published": paper.get("published", ""),
            "chunk_text": chunk_text,
            "chunk_index": len(chunks),
        })
        start += chunk_size - overlap
    return chunks


def build_chunk_index(papers: List[dict]):
    """Build a FAISS index over all chunks from the given papers."""
    all_chunks = []
    for paper in papers:
        all_chunks.extend(chunk_paper(paper))

    if not all_chunks:
        raise ValueError("No chunks to index")

    embeddings = [get_embedding(c["chunk_text"]) for c in all_chunks]
    arr = np.array(embeddings, dtype=np.float32)

    index = faiss.IndexFlatL2(EMBEDDING_DIM)
    index.add(arr)
    logger.info(f"Chunk index built: {index.ntotal} chunks from {len(papers)} papers")
    return index, all_chunks


def retrieve_relevant_chunks(question: str, index, chunks: List[dict], top_k: int = 8):
    q_vec = np.array([get_embedding(question)], dtype=np.float32)
    distances, indices = index.search(q_vec, min(top_k, index.ntotal))
    results = []
    seen_papers = set()
    for dist, idx in zip(distances[0], indices[0]):
        if idx < len(chunks):
            chunk = chunks[idx].copy()
            chunk["score"] = float(1 / (1 + dist))
            results.append(chunk)
            seen_papers.add(chunk["paper_id"])
    return results, seen_papers


# ── Synthesis with Citations ───────────────────────────────────────────────────

def synthesise_answer(question: str, chunks: List[dict]) -> tuple[str, List[Citation]]:
    """
    Use GPT (or fallback) to synthesise a cited answer from retrieved chunks.
    Returns (markdown_answer, citations_list).
    """
    # Build numbered context block
    context_lines = []
    for i, c in enumerate(chunks, 1):
        authors_str = ", ".join(c["authors"][:2]) + (" et al." if len(c["authors"]) > 2 else "")
        context_lines.append(
            f"[{i}] **{c['title']}** ({authors_str}, {c['published'] or 'n.d.'})\n{c['chunk_text']}"
        )
    context = "\n\n".join(context_lines)

    system_prompt = (
        "You are an expert research analyst. "
        "Answer the user's question using ONLY the provided paper excerpts. "
        "Cite sources inline using [1], [2], … notation matching the excerpt numbers. "
        "Be precise, synthesised, and informative. Use markdown for structure. "
        "If the excerpts don't contain enough information, say so honestly."
    )

    user_prompt = f"""Question: {question}

Paper Excerpts:
{context}

Provide a well-structured, cited answer."""

    if client:
        try:
            response = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,
                max_tokens=600,
            )
            answer_text = response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"GPT synthesis failed: {e}")
            answer_text = _fallback_synthesis(question, chunks)
    else:
        answer_text = _fallback_synthesis(question, chunks)

    # Build citation objects
    seen = {}
    citations = []
    for i, c in enumerate(chunks, 1):
        pid = c["paper_id"]
        if pid not in seen and f"[{i}]" in answer_text:
            seen[pid] = True
            citations.append(Citation(
                paper_id=pid,
                title=c["title"],
                authors=c["authors"],
                url=c["url"],
                published=c["published"],
                chunk_text=c["chunk_text"][:250],
            ))

    return answer_text, citations


def _fallback_synthesis(question: str, chunks: List[dict]) -> str:
    lines = [f"Based on {len(chunks)} retrieved passages addressing **'{question}'**:\n"]
    for i, c in enumerate(chunks[:5], 1):
        lines.append(f"[{i}] From *{c['title']}*: {c['chunk_text'][:200]}…")
    lines.append(
        "\n*(No GROQ_API_KEY configured — set it in .env for full LLM-powered synthesis.)*"
    )
    return "\n\n".join(lines)


# ── Data Fetching ──────────────────────────────────────────────────────────────

# ── Source fetchers ────────────────────────────────────────────────────────────

def fetch_openalex_papers(query: str, limit: int = 25) -> List[dict]:
    """
    OpenAlex — free, no API key, 100 k req/day polite pool.
    Docs: https://docs.openalex.org/api-entities/works/search-works
    """
    try:
        params = {
            "search": query,
            "filter": "has_abstract:true",
            "per-page": min(limit, 50),
            "select": "id,title,abstract_inverted_index,authorships,publication_year,doi,cited_by_count,open_access",
            "mailto": "research@papermind.ai",   # polite pool — faster responses
        }
        response = requests.get(
            "https://api.openalex.org/works",
            params=params,
            timeout=30,
        )
        if response.status_code == 429:
            logger.warning("OpenAlex rate limited — backing off 5 s")
            time.sleep(5)
            response = requests.get("https://api.openalex.org/works", params=params, timeout=30)
        response.raise_for_status()

        results = response.json().get("results", [])
        papers = []
        for item in results:
            title = (item.get("title") or "").strip()
            if not title:
                continue

            # OpenAlex stores abstracts as inverted index — reconstruct
            inv = item.get("abstract_inverted_index") or {}
            if not inv:
                continue
            word_positions: List[tuple] = []
            for word, positions in inv.items():
                for pos in positions:
                    word_positions.append((pos, word))
            word_positions.sort()
            abstract = " ".join(w for _, w in word_positions)
            if len(abstract) < 50:
                continue

            authors = [
                a.get("author", {}).get("display_name", "")
                for a in item.get("authorships", [])
                if a.get("author", {}).get("display_name")
            ]

            doi = item.get("doi") or ""
            url = doi if doi.startswith("http") else (f"https://doi.org/{doi}" if doi else "")
            oa_url = (item.get("open_access") or {}).get("oa_url") or url

            papers.append({
                "id": item.get("id", "").split("/")[-1],   # W1234567890
                "title": title,
                "abstract": abstract,
                "authors": authors,
                "published": str(item.get("publication_year") or ""),
                "url": oa_url or url,
                "source": "openalex",
                "citation_count": item.get("cited_by_count", 0),
            })

        logger.info(f"Fetched {len(papers)} from OpenAlex")
        return papers
    except Exception as e:
        logger.error(f"OpenAlex error: {e}")
        return []


def fetch_crossref_papers(query: str, limit: int = 20) -> List[dict]:
    """
    CrossRef — free, no API key, ~50 req/s with polite pool.
    Only returns works that have abstracts (jats:abstract field).
    """
    try:
        params = {
            "query": query,
            "rows": min(limit, 50),
            "select": "DOI,title,abstract,author,published,is-referenced-by-count,URL",
            "mailto": "research@papermind.ai",
        }
        response = requests.get(
            "https://api.crossref.org/works",
            params=params,
            timeout=30,
        )
        response.raise_for_status()

        items = response.json().get("message", {}).get("items", [])
        papers = []
        for item in items:
            titles = item.get("title") or []
            title = titles[0].strip() if titles else ""
            if not title:
                continue

            abstract = (item.get("abstract") or "").strip()
            # CrossRef wraps abstracts in JATS XML tags — strip them
            if abstract:
                import re as _re
                abstract = _re.sub(r"<[^>]+>", " ", abstract).strip()
            if len(abstract) < 50:
                continue

            authors = []
            for a in item.get("author") or []:
                given = a.get("given", "")
                family = a.get("family", "")
                name = f"{given} {family}".strip()
                if name:
                    authors.append(name)

            doi = item.get("DOI", "")
            url = item.get("URL") or (f"https://doi.org/{doi}" if doi else "")

            pub_date = ""
            pd = item.get("published") or {}
            dp = pd.get("date-parts", [[]])[0]
            if dp:
                pub_date = str(dp[0])

            papers.append({
                "id": f"cr-{doi.replace('/', '-')}",
                "title": title,
                "abstract": abstract,
                "authors": authors,
                "published": pub_date,
                "url": url,
                "source": "crossref",
                "citation_count": item.get("is-referenced-by-count", 0),
            })

        logger.info(f"Fetched {len(papers)} from CrossRef")
        return papers
    except Exception as e:
        logger.error(f"CrossRef error: {e}")
        return []


def fetch_arxiv_papers(query: str, limit: int = 20) -> List[dict]:
    try:
        params = {
            "search_query": f"all:{query}",
            "start": 0,
            "max_results": limit,
            "sortBy": "relevance",
            "sortOrder": "descending",
        }
        response = requests.get("http://export.arxiv.org/api/query", params=params, timeout=30)
        response.raise_for_status()
        papers = []
        root = ET.fromstring(response.text)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        for entry in root.findall("atom:entry", ns):
            title_elem = entry.find("atom:title", ns)
            summary_elem = entry.find("atom:summary", ns)
            id_elem = entry.find("atom:id", ns)
            published_elem = entry.find("atom:published", ns)
            if not all([title_elem, summary_elem, id_elem]):
                continue
            title_text = (title_elem.text or "").strip().replace("\n", " ")
            abstract_text = (summary_elem.text or "").strip().replace("\n", " ")
            if not title_text or len(abstract_text) < 50:
                continue
            authors = []
            for author in entry.findall("atom:author", ns):
                name = author.find("atom:name", ns)
                if name is not None and name.text:
                    authors.append(name.text.strip())
            arxiv_id = id_elem.text.split("/")[-1]
            papers.append({
                "id": arxiv_id,
                "title": title_text,
                "abstract": abstract_text,
                "authors": authors,
                "published": published_elem.text[:10] if published_elem is not None else "",
                "url": f"https://arxiv.org/abs/{arxiv_id}",
                "pdf_url": f"https://arxiv.org/pdf/{arxiv_id}.pdf",
                "source": "arxiv",
            })
        logger.info(f"Fetched {len(papers)} from arXiv")
        return papers
    except Exception as e:
        logger.error(f"arXiv error: {e}")
        return []


def fetch_semantic_scholar_papers(query: str, limit: int = 20, retries: int = 3) -> List[dict]:
    url = "https://api.semanticscholar.org/graph/v1/paper/search"
    params = {
        "query": query,
        "limit": limit,
        "fields": "title,abstract,authors,year,url,paperId,citationCount",
    }
    for attempt in range(retries):
        try:
            response = requests.get(url, params=params, timeout=30)
            if response.status_code == 429:
                wait = 2 ** attempt
                logger.warning(f"Semantic Scholar rate limited. Retrying in {wait}s (attempt {attempt + 1}/{retries})")
                time.sleep(wait)
                continue
            response.raise_for_status()
            data = response.json()
            papers = []
            for item in data.get("data", []):
                abstract = item.get("abstract", "")
                if not abstract or len(abstract) < 50:
                    continue
                authors = [a.get("name", "") for a in item.get("authors", []) if a.get("name")]
                papers.append({
                    "id": item.get("paperId", ""),
                    "title": item["title"],
                    "abstract": abstract,
                    "authors": authors,
                    "published": str(item.get("year", "")),
                    "url": item.get("url", ""),
                    "source": "semantic_scholar",
                    "citation_count": item.get("citationCount", 0),
                })
            logger.info(f"Fetched {len(papers)} from Semantic Scholar")
            return papers
        except requests.exceptions.RequestException as e:
            logger.warning(f"Semantic Scholar request error (attempt {attempt + 1}/{retries}): {e}")
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
            continue
        except Exception as e:
            logger.error(f"Semantic Scholar processing error: {e}")
            return []
    logger.error("Semantic Scholar: max retries reached. Skipping.")
    return []


def fetch_all_papers(query: str, sources: List[str], max_results: int) -> List[dict]:
    """
    Fetch from all available sources. Priority order:
      1. OpenAlex  (free, no key, high volume)
      2. CrossRef  (free, no key, broad coverage)
      3. arXiv     (free, CS/physics/math focus)
      4. Semantic Scholar (may rate-limit aggressively)
    Results are deduplicated by normalised title.
    """
    all_papers: List[dict] = []
    per_source = max(max_results // 2, 15)   # fetch generously; dedup later

    # Always try OpenAlex and CrossRef — they are reliable and free
    all_papers.extend(fetch_openalex_papers(query, per_source))
    all_papers.extend(fetch_crossref_papers(query, per_source))

    # Try legacy sources only if explicitly requested or if primaries gave too little
    if "arxiv" in sources or len(all_papers) < 5:
        all_papers.extend(fetch_arxiv_papers(query, per_source))
    if "semantic_scholar" in sources or len(all_papers) < 5:
        all_papers.extend(fetch_semantic_scholar_papers(query, per_source))

    # Deduplicate by normalised title prefix
    seen: set = set()
    unique: List[dict] = []
    for p in all_papers:
        key = p["title"].lower().replace(" ", "").replace("-", "")[:60]
        if key not in seen:
            seen.add(key)
            unique.append(p)

    logger.info(f"Total unique papers after dedup: {len(unique)}")
    return unique[:max_results]


def build_faiss_index(papers: List[dict]):
    global faiss_index, paper_metadata
    embeddings, paper_metadata = [], []
    for p in papers:
        try:
            text = f"{p['title']}\n{p['abstract']}"
            embeddings.append(get_embedding(text))
            paper_metadata.append(p)
        except Exception as e:
            logger.warning(f"Skipped paper: {e}")
    if not embeddings:
        raise HTTPException(status_code=500, detail="Failed to generate embeddings")
    faiss_index = faiss.IndexFlatL2(EMBEDDING_DIM)
    faiss_index.add(np.array(embeddings, dtype=np.float32))
    return faiss_index, paper_metadata


def search_similar_papers(query: str, top_k: int = 10) -> List[dict]:
    if faiss_index is None:
        raise HTTPException(status_code=400, detail="Index not built. Fetch papers first.")
    q_vec = np.array([get_embedding(query)], dtype=np.float32)
    distances, indices = faiss_index.search(q_vec, min(top_k, faiss_index.ntotal))
    results = []
    for dist, idx in zip(distances[0], indices[0]):
        if idx < len(paper_metadata):
            paper = paper_metadata[idx].copy()
            paper["relevance_score"] = float(1 / (1 + dist))
            results.append(paper)
    return results


def explain_relevance(query: str, title: str, abstract: str) -> str:
    if not client:
        return "Relevant based on semantic similarity to your query."
    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": "You are an expert research assistant."},
                {"role": "user", "content": (
                    f'Query: "{query}"\nTitle: "{title}"\nAbstract: "{abstract[:500]}..."\n'
                    "Explain in 2 concise sentences why this paper is relevant."
                )},
            ],
            temperature=0.3,
            max_tokens=100,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Explanation failed: {e}")
        return "Relevant based on semantic similarity."


# ── API Endpoints ──────────────────────────────────────────────────────────────

@app.get("/")
def health_check():
    return {
        "status": "running",
        "service": "PaperMind Analyst API",
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat(),
        "features": ["semantic_search", "chunked_rag", "cited_synthesis"],
    }


@app.post("/recommend", response_model=RecommendationResponse)
async def recommend_papers(query: Query):
    """Fetch and rank papers by semantic similarity."""
    start = time.time()
    if not query.text.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    papers = fetch_all_papers(query.text, query.sources, query.max_results * 2)
    if not papers:
        return RecommendationResponse(
            papers=[],
            query=query.text,
            total_found=0,
            processing_time=round(time.time() - start, 2),
        )

    build_faiss_index(papers)
    similar = search_similar_papers(query.text, query.max_results)

    result_papers = []
    for paper in similar[:5]:
        paper["explanation"] = explain_relevance(query.text, paper["title"], paper["abstract"])
        result_papers.append(Paper(**{k: paper.get(k) for k in Paper.__fields__}))
    for paper in similar[5:]:
        result_papers.append(Paper(**{k: paper.get(k) for k in Paper.__fields__}))

    return RecommendationResponse(
        papers=result_papers,
        query=query.text,
        total_found=len(similar),
        processing_time=round(time.time() - start, 2),
    )


@app.post("/ask", response_model=AnalystAnswer)
async def ask_papers(req: AnalystQuestion):
    """
    RAG endpoint: chunk the session papers, retrieve relevant passages,
    synthesise a cited answer using GPT.
    """
    start = time.time()
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")
    if not req.session_papers:
        raise HTTPException(status_code=400, detail="No papers provided in session")

    try:
        # Build a fresh chunk index for this request (stateless, fast for ≤100 papers)
        chunk_index, all_chunks = build_chunk_index(req.session_papers)

        # Retrieve top-k relevant chunks
        relevant_chunks, seen_papers = retrieve_relevant_chunks(
            req.question, chunk_index, all_chunks, top_k=req.top_k
        )

        # Synthesise answer with citations
        answer_text, citations = synthesise_answer(req.question, relevant_chunks)

        return AnalystAnswer(
            question=req.question,
            answer=answer_text,
            citations=citations,
            papers_consulted=len(seen_papers),
            processing_time=round(time.time() - start, 2),
        )
    except Exception as e:
        logger.error(f"Ask endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/upload-document")
async def upload_document(file: UploadFile = File(...)):
    """Upload a document and find related papers."""
    if not file.filename.endswith(('.txt', '.pdf', '.md')):
        raise HTTPException(status_code=400, detail="Only .txt, .pdf, and .md files are supported")

    content = await file.read()
    text_content = content.decode('utf-8', errors='ignore')

    if client:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": "Extract 3-5 key research terms from this document, comma-separated, no extra text."},
                {"role": "user", "content": text_content[:2000]},
            ],
            temperature=0.3,
            max_tokens=80,
        )
        extracted_terms = response.choices[0].message.content.strip()
    else:
        words = [w for w in text_content.lower().split() if len(w) > 5]
        extracted_terms = ", ".join(list(dict.fromkeys(words))[:5])

    query = Query(text=extracted_terms, max_results=15)
    recommendations = await recommend_papers(query)
    return {
        "filename": file.filename,
        "extracted_terms": extracted_terms,
        "recommendations": recommendations,
    }


@app.get("/api/jobs")
def get_jobs():
    """Job status endpoint — currently no async jobs; returns empty list."""
    return {"jobs": [], "status": "ok"}


@app.get("/stats")
def get_stats():
    return {
        "indexed_papers": faiss_index.ntotal if faiss_index else 0,
        "embedding_model": "all-MiniLM-L6-v2",
        "available_sources": ["openalex", "crossref", "arxiv", "semantic_scholar"],
        "endpoints": ["/recommend", "/ask", "/upload-document"],
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)