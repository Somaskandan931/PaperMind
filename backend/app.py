from fastapi import FastAPI, HTTPException, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import requests
import os
import faiss
import numpy as np
from dotenv import load_dotenv
from openai import OpenAI
import json
import time
import logging
from pathlib import Path
import xml.etree.ElementTree as ET
from datetime import datetime
import asyncio
from sentence_transformers import SentenceTransformer

# Configure logging
logging.basicConfig( level=logging.INFO )
logger = logging.getLogger( __name__ )

# Load environment variables
load_dotenv()
api_key = os.getenv( "OPENAI_API_KEY" )

# Initialize OpenAI client (optional, only for explanations)
client = None
if api_key :
    client = OpenAI( api_key=api_key )

# Initialize local embedding model (free alternative)
embedding_model = SentenceTransformer( 'all-MiniLM-L6-v2' )  # Free, lightweight model

# Initialize FastAPI
app = FastAPI(
    title="PaperMind API",
    description="AI-powered research paper recommender system",
    version="1.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models
class Query( BaseModel ) :
    text: str
    max_results: Optional[int] = 10
    sources: Optional[List[str]] = ["semantic_scholar", "arxiv"]


class Paper( BaseModel ) :
    id: str
    title: str
    abstract: str
    authors: List[str]
    published: Optional[str] = None
    url: str
    source: str
    relevance_score: Optional[float] = None
    explanation: Optional[str] = None


class RecommendationResponse( BaseModel ) :
    papers: List[Paper]
    query: str
    total_found: int
    processing_time: float


# Global cache and configuration
paper_cache = {}
embeddings_cache = {}
faiss_index = None
paper_metadata = []
EMBEDDING_MODEL = "all-MiniLM-L6-v2"  # Free local model
EMBEDDING_DIM = 384  # Dimension for all-MiniLM-L6-v2
DATA_DIR = Path( "data" )
DATA_DIR.mkdir( exist_ok=True )


# ------------------------
# Utility Functions
# ------------------------

def get_embedding ( text: str, max_retries: int = 3 ) -> List[float] :
    """Generate embedding using local Sentence Transformer model"""
    try :
        # Clean and truncate text if too long
        cleaned_text = text.replace( '\n', ' ' ).strip()[:512]  # Shorter for local model

        # Use local model (no API calls, completely free)
        embedding = embedding_model.encode( cleaned_text, convert_to_tensor=False )
        return embedding.tolist()
    except Exception as e :
        logger.error( f"Local embedding failed: {e}" )
        raise HTTPException( status_code=500, detail=f"Embedding failed: {str( e )}" )


def explain_relevance ( query: str, title: str, abstract: str ) -> str :
    """Generate explanation for paper relevance"""
    if not client :
        return "This paper appears relevant based on semantic similarity to your query."

    try :
        prompt = f"""
        Query: "{query}"

        Paper Title: "{title}"
        Abstract: "{abstract[:500]}..."

        Explain in 2 concise sentences why this paper is relevant to the query.
        """

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role" : "system", "content" : "You are an expert research assistant."},
                {"role" : "user", "content" : prompt}
            ],
            temperature=0.3,
            max_tokens=100
        )
        return response.choices[0].message.content.strip()
    except Exception as e :
        logger.error( f"Explanation generation failed: {e}" )
        return "This paper appears relevant based on semantic similarity to your query."


# ------------------------
# Data Fetching Functions
# ------------------------

def fetch_semantic_scholar_papers ( query: str, limit: int = 20 ) -> List[dict] :
    """Fetch papers from Semantic Scholar API"""
    try :
        url = "https://api.semanticscholar.org/graph/v1/paper/search"
        params = {
            "query" : query,
            "limit" : limit,
            "fields" : "title,abstract,authors,year,url,paperId"
        }

        response = requests.get( url, params=params, timeout=30 )
        response.raise_for_status()

        data = response.json()
        papers = []

        for item in data.get( "data", [] ) :
            if item.get( "abstract" ) and len( item["abstract"] ) > 50 :
                authors = [author.get( "name", "Unknown" ) for author in item.get( "authors", [] )]
                papers.append( {
                    "id" : item.get( "paperId", "" ),
                    "title" : item["title"],
                    "abstract" : item["abstract"],
                    "authors" : authors,
                    "published" : str( item.get( "year", "" ) ),
                    "url" : item.get( "url", "" ),
                    "source" : "semantic_scholar"
                } )

        logger.info( f"Fetched {len( papers )} papers from Semantic Scholar" )
        return papers

    except Exception as e :
        logger.error( f"Semantic Scholar API error: {e}" )
        return []


def fetch_arxiv_papers ( query: str, limit: int = 20 ) -> List[dict] :
    """Fetch papers from arXiv API"""
    try :
        arxiv_url = "http://export.arxiv.org/api/query"
        params = {
            "search_query" : f"all:{query}",
            "start" : 0,
            "max_results" : limit,
            "sortBy" : "relevance",
            "sortOrder" : "descending"
        }

        response = requests.get( arxiv_url, params=params, timeout=30 )
        response.raise_for_status()

        papers = []
        root = ET.fromstring( response.text )
        namespace = {"atom" : "http://www.w3.org/2005/Atom"}

        for entry in root.findall( "atom:entry", namespace ) :
            title_elem = entry.find( "atom:title", namespace )
            summary_elem = entry.find( "atom:summary", namespace )
            id_elem = entry.find( "atom:id", namespace )
            published_elem = entry.find( "atom:published", namespace )

            if title_elem is not None and summary_elem is not None :
                authors = []
                for author in entry.findall( "atom:author", namespace ) :
                    name_elem = author.find( "atom:name", namespace )
                    if name_elem is not None :
                        authors.append( name_elem.text )

                # Extract arXiv ID and create URL
                arxiv_id = id_elem.text.split( '/' )[-1] if id_elem is not None else ""
                url = f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else ""

                papers.append( {
                    "id" : arxiv_id,
                    "title" : title_elem.text.strip().replace( '\n', ' ' ),
                    "abstract" : summary_elem.text.strip().replace( '\n', ' ' ),
                    "authors" : authors,
                    "published" : published_elem.text[:10] if published_elem is not None else "",
                    "url" : url,
                    "source" : "arxiv"
                } )

        logger.info( f"Fetched {len( papers )} papers from arXiv" )
        return papers

    except Exception as e :
        logger.error( f"arXiv API error: {e}" )
        return []


def fetch_all_papers ( query: str, sources: List[str], max_results: int ) -> List[dict] :
    """Fetch papers from multiple sources"""
    all_papers = []
    results_per_source = max_results // len( sources )

    if "semantic_scholar" in sources :
        all_papers.extend( fetch_semantic_scholar_papers( query, results_per_source ) )

    if "arxiv" in sources :
        all_papers.extend( fetch_arxiv_papers( query, results_per_source ) )

    # Remove duplicates based on title similarity
    unique_papers = []
    seen_titles = set()

    for paper in all_papers :
        title_key = paper["title"].lower().replace( " ", "" )[:50]
        if title_key not in seen_titles :
            seen_titles.add( title_key )
            unique_papers.append( paper )

    return unique_papers[:max_results]


# ------------------------
# Vector Search Functions
# ------------------------

def build_faiss_index ( papers: List[dict] ) -> tuple :
    """Build FAISS index from papers"""
    global faiss_index, paper_metadata

    if not papers :
        raise HTTPException( status_code=404, detail="No papers to index" )

    embeddings = []
    paper_metadata = []

    logger.info( f"Building FAISS index for {len( papers )} papers..." )

    for i, paper in enumerate( papers ) :
        try :
            # Combine title and abstract for embedding
            text = f"{paper['title']}\n{paper['abstract']}"
            embedding = get_embedding( text )
            embeddings.append( embedding )
            paper_metadata.append( paper )

            if i % 10 == 0 :
                logger.info( f"Processed {i + 1}/{len( papers )} papers" )

        except Exception as e :
            logger.error( f"Error processing paper {i}: {e}" )
            continue

    if not embeddings :
        raise HTTPException( status_code=500, detail="Failed to generate embeddings" )

    # Create FAISS index
    faiss_index = faiss.IndexFlatL2( EMBEDDING_DIM )
    embeddings_array = np.array( embeddings ).astype( 'float32' )
    faiss_index.add( embeddings_array )

    logger.info( f"FAISS index built with {faiss_index.ntotal} vectors" )
    return faiss_index, paper_metadata


def search_similar_papers ( query: str, top_k: int = 10 ) -> List[tuple] :
    """Search for similar papers using FAISS"""
    if faiss_index is None :
        raise HTTPException( status_code=400, detail="Index not built. Please fetch papers first." )

    query_embedding = get_embedding( query )
    query_vector = np.array( [query_embedding] ).astype( 'float32' )

    # Search in FAISS index
    distances, indices = faiss_index.search( query_vector, min( top_k, faiss_index.ntotal ) )

    results = []
    for i, (distance, idx) in enumerate( zip( distances[0], indices[0] ) ) :
        if idx < len( paper_metadata ) :
            paper = paper_metadata[idx].copy()
            paper['relevance_score'] = float( 1 / (1 + distance) )  # Convert distance to similarity
            results.append( paper )

    return results


# ------------------------
# API Endpoints
# ------------------------

@app.get( "/" )
def health_check () :
    """Health check endpoint"""
    return {
        "status" : "running",
        "service" : "PaperMind API",
        "version" : "1.0.0",
        "timestamp" : datetime.now().isoformat()
    }


@app.post( "/recommend", response_model=RecommendationResponse )
async def recommend_papers ( query: Query ) :
    """Main recommendation endpoint"""
    start_time = time.time()

    try :
        # Validate input
        if not query.text.strip() :
            raise HTTPException( status_code=400, detail="Query text cannot be empty" )

        # Fetch papers from specified sources
        papers = fetch_all_papers( query.text, query.sources, query.max_results )

        if not papers :
            raise HTTPException( status_code=404, detail="No papers found for the given query" )

        # Build or rebuild index
        build_faiss_index( papers )

        # Search for similar papers
        similar_papers = search_similar_papers( query.text, query.max_results )

        # Generate explanations for top papers
        result_papers = []
        for paper in similar_papers[:5] :  # Generate explanations for top 5
            try :
                explanation = explain_relevance( query.text, paper['title'], paper['abstract'] )
                paper['explanation'] = explanation
            except Exception as e :
                logger.error( f"Failed to generate explanation: {e}" )
                paper['explanation'] = "Relevance explanation unavailable"

            result_papers.append( Paper( **paper ) )

        # Add remaining papers without explanations
        for paper in similar_papers[5 :] :
            result_papers.append( Paper( **paper ) )

        processing_time = time.time() - start_time

        return RecommendationResponse(
            papers=result_papers,
            query=query.text,
            total_found=len( similar_papers ),
            processing_time=round( processing_time, 2 )
        )

    except HTTPException :
        raise
    except Exception as e :
        logger.error( f"Recommendation error: {e}" )
        raise HTTPException( status_code=500, detail=f"Internal server error: {str( e )}" )


@app.post( "/upload-document" )
async def upload_document ( file: UploadFile = File( ... ) ) :
    """Upload and analyze a document for paper recommendations"""
    try :
        if not file.filename.endswith( ('.txt', '.pdf', '.md') ) :
            raise HTTPException( status_code=400, detail="Only .txt, .pdf, and .md files are supported" )

        # Read file content
        content = await file.read()
        text_content = content.decode( 'utf-8' ) if file.filename.endswith( '.txt' ) else str( content )

        # Extract key terms/summary for search
        if not client :
            # Simple keyword extraction without OpenAI
            words = text_content.lower().split()
            # Get most common meaningful words (simple approach)
            common_words = ['the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by']
            keywords = [word for word in set( words ) if len( word ) > 4 and word not in common_words]
            extracted_terms = ', '.join( list( keywords )[:5] )
        else :
            summary_prompt = f"""
            Analyze this document and extract 3-5 key research topics or terms that could be used to find related academic papers:

            Document content (first 2000 chars):
            {text_content[:2000]}

            Return only the key terms separated by commas.
            """

            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role" : "system", "content" : "You are a research assistant that extracts key academic terms."},
                    {"role" : "user", "content" : summary_prompt}
                ],
                temperature=0.3,
                max_tokens=100
            )

            extracted_terms = response.choices[0].message.content.strip()

        # Use extracted terms as query
        query = Query( text=extracted_terms, max_results=15 )
        recommendations = await recommend_papers( query )

        return {
            "filename" : file.filename,
            "extracted_terms" : extracted_terms,
            "recommendations" : recommendations
        }

    except Exception as e :
        logger.error( f"Document upload error: {e}" )
        raise HTTPException( status_code=500, detail=f"Failed to process document: {str( e )}" )


@app.get( "/stats" )
def get_stats () :
    """Get system statistics"""
    return {
        "indexed_papers" : faiss_index.ntotal if faiss_index else 0,
        "embedding_model" : EMBEDDING_MODEL,
        "available_sources" : ["semantic_scholar", "arxiv"],
        "cache_size" : len( paper_cache )
    }


if __name__ == "__main__" :
    import uvicorn

    uvicorn.run( app, host="0.0.0.0", port=8000, reload=True )