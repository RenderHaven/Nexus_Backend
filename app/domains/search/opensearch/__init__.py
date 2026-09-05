from .client import close_opensearch, get_opensearch, is_configured
from .indexes import MAPPINGS, SearchIndexes

__all__ = [
    "close_opensearch",
    "get_opensearch",
    "is_configured",
    "MAPPINGS",
    "SearchIndexes",
]
