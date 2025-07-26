import openai
import numpy as np
import faiss
import logging
from typing import List, Dict, Tuple
import json
from pathlib import Path
import pickle

logger = logging.getLogger( __name__ )


class EmbeddingService :
    """Service for handling embeddings and vector search"""

    def __init__ ( self, api_key: str, model: str = "text-embedding-3-small" ) :
        openai.api_key = api_key
        self.model = model
        self.dimension = 1536 if "3-small" in model else 1536
        self.index = None
        self.metadata = []

        # Cache for embeddings
        self.embedding_cache = {}

    def get_embedding ( self, text: str, use_cache: bool = True ) -> List[float] :
        """Generate embedding with caching and error handling"""
        if use_cache and text in self.embedding_cache :
            return self.embedding_cache[text]

        try :
            # Clean and truncate text
            cleaned_text = text.replace( '\n', ' ' ).strip()
            if len( cleaned_text ) > 8000 :
                cleaned_text = cleaned_text[:8000]

            response = openai.Embedding.create(
                input=cleaned_text,
                model=self.model
            )

            embedding = response['data'][0]['embedding']

            if use_cache :
                self.embedding_cache[text] = embedding

            return embedding

        except Exception as e :
            logger.error( f"Embedding generation failed: {e}" )
            raise

    def build_index ( self, papers: List[Dict] ) -> Tuple[faiss.Index, List[Dict]] :
        """Build FAISS index from papers"""
        if not papers :
            raise ValueError( "No papers provided for indexing" )

        embeddings = []
        valid_metadata = []

        logger.info( f"Building index for {len( papers )} papers..." )

        for i, paper in enumerate( papers ) :
            try :
                # Combine title and abstract for better representation
                text = f"Title: {paper['title']}\n\nAbstract: {paper['abstract']}"

                embedding = self.get_embedding( text )
                embeddings.append( embedding )
                valid_metadata.append( paper )

                if (i + 1) % 10 == 0 :
                    logger.info( f"Processed {i + 1}/{len( papers )} papers" )

            except Exception as e :
                logger.warning( f"Failed to process paper {i}: {e}" )
                continue

        if not embeddings :
            raise ValueError( "No valid embeddings generated" )

        # Create FAISS index
        embeddings_array = np.array( embeddings, dtype=np.float32 )
        index = faiss.IndexFlatL2( self.dimension )
        index.add( embeddings_array )

        self.index = index
        self.metadata = valid_metadata

        logger.info( f"Index built with {index.ntotal} vectors" )
        return index, valid_metadata

    def search ( self, query: str, k: int = 10 ) -> List[Tuple[Dict, float]] :
        """Search for similar papers"""
        if self.index is None :
            raise ValueError( "Index not built. Call build_index first." )

        query_embedding = self.get_embedding( query )
        query_vector = np.array( [query_embedding], dtype=np.float32 )

        # Search
        distances, indices = self.index.search( query_vector, min( k, self.index.ntotal ) )

        results = []
        for distance, idx in zip( distances[0], indices[0] ) :
            if idx < len( self.metadata ) :
                paper = self.metadata[idx].copy()
                # Convert distance to similarity score (0-1)
                similarity = 1 / (1 + distance)
                results.append( (paper, float( similarity )) )

        return results

    def save_index ( self, filepath: str ) :
        """Save index and metadata to disk"""
        if self.index is None :
            raise ValueError( "No index to save" )

        path = Path( filepath )
        path.parent.mkdir( parents=True, exist_ok=True )

        # Save FAISS index
        faiss.write_index( self.index, str( path.with_suffix( '.index' ) ) )

        # Save metadata
        with open( path.with_suffix( '.metadata' ), 'wb' ) as f :
            pickle.dump( self.metadata, f )

        # Save embedding cache
        with open( path.with_suffix( '.cache' ), 'wb' ) as f :
            pickle.dump( self.embedding_cache, f )

        logger.info( f"Index saved to {filepath}" )

    def load_index ( self, filepath: str ) :
        """Load index and metadata from disk"""
        path = Path( filepath )

        # Load FAISS index
        index_file = path.with_suffix( '.index' )
        if index_file.exists() :
            self.index = faiss.read_index( str( index_file ) )

        # Load metadata
        metadata_file = path.with_suffix( '.metadata' )
        if metadata_file.exists() :
            with open( metadata_file, 'rb' ) as f :
                self.metadata = pickle.load( f )

        # Load embedding cache
        cache_file = path.with_suffix( '.cache' )
        if cache_file.exists() :
            with open( cache_file, 'rb' ) as f :
                self.embedding_cache = pickle.load( f )

        logger.info( f"Index loaded from {filepath}" )
