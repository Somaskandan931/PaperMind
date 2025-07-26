class PaperMindException(Exception):
    """Base exception for PaperMind application"""
    pass

class APIException(PaperMindException):
    """Exception for API-related errors"""
    pass

class EmbeddingException(PaperMindException):
    """Exception for embedding-related errors"""
    pass

class IndexException(PaperMindException):
    """Exception for index-related errors"""
    pass

class DataSourceException(PaperMindException):
    """Exception for data source errors"""
    pass
