import os
from pathlib import Path
from typing import List


class Config :
    """Application configuration"""

    # API Configuration
    OPENAI_API_KEY = os.getenv( "OPENAI_API_KEY" )

    # Model Configuration
    EMBEDDING_MODEL = "text-embedding-3-small"
    CHAT_MODEL = "gpt-3.5-turbo"
    EMBEDDING_DIMENSION = 1536

    # Data Configuration
    DATA_DIR = Path( "data" )
    INDEX_FILE = DATA_DIR / "faiss_index"
    CACHE_FILE = DATA_DIR / "embeddings_cache.pkl"

    # API Limits
    MAX_PAPERS_PER_SOURCE = 50
    MAX_QUERY_LENGTH = 1000
    MAX_ABSTRACT_LENGTH = 2000

    # Search Configuration
    DEFAULT_SOURCES = ["semantic_scholar", "arxiv"]
    DEFAULT_MAX_RESULTS = 10
    DEFAULT_TOP_K = 5

    # Rate Limiting
    REQUESTS_PER_MINUTE = 60
    EMBEDDING_BATCH_SIZE = 20

    # Logging
    LOG_LEVEL = os.getenv( "LOG_LEVEL", "INFO" )

    @classmethod
    def validate ( cls ) :
        """Validate configuration"""
        if not cls.OPENAI_API_KEY :
            raise ValueError( "OPENAI_API_KEY environment variable is required" )

        cls.DATA_DIR.mkdir( exist_ok=True )

        return True
