from opensearchpy import AsyncOpenSearch

from app.config import settings

# Built lazily rather than at import time: OPENSEARCH_URL is optional, so the
# app must boot and serve every non-search route with no cluster configured.
_client: AsyncOpenSearch | None = None


def is_configured() -> bool:
    """Whether a cluster is reachable at all. Callers that must degrade
    gracefully (indexing on write) check this instead of catching."""
    return bool(settings.OPENSEARCH_URL)


def get_opensearch() -> AsyncOpenSearch:
    global _client

    if not settings.OPENSEARCH_URL:
        raise RuntimeError(
            "OPENSEARCH_URL is not set; search is unavailable in this environment"
        )

    if _client is None:
        _client = AsyncOpenSearch(
            hosts=[settings.OPENSEARCH_URL],
            http_compress=True,
            verify_certs=settings.OPENSEARCH_VERIFY_CERTS,
            ssl_show_warn=False,
            timeout=settings.OPENSEARCH_TIMEOUT,
            max_retries=3,
            retry_on_timeout=True,
        )

    return _client


async def close_opensearch() -> None:
    """Release the underlying aiohttp session. Wire into the FastAPI lifespan
    and call at the end of any script that opened a client."""
    global _client

    if _client is not None:
        await _client.close()
        _client = None
