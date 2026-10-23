import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx
from backend.app.core.config import settings
from backend.app.services.embedding_service import (
    MockEmbeddingProvider,
    OpenAIEmbeddingProvider,
    GeminiEmbeddingProvider,
    EmbeddingService,
    get_embedding_provider,
)


def cosine_similarity(v1, v2):
    dot = sum(a * b for a, b in zip(v1, v2))
    return dot


@pytest.mark.asyncio
async def test_mock_embedding_dimension_and_normalization():
    """Ensure mock embeddings produce normalized vectors matching configured dimension."""
    provider = MockEmbeddingProvider(dimension=settings.EMBEDDING_DIMENSION)
    texts = ["First research excerpt.", "Second methodology section."]
    embeddings = await provider.embed_texts(texts)

    assert len(embeddings) == 2
    for emb in embeddings:
        assert len(emb) == settings.EMBEDDING_DIMENSION
        # Check unit normalization: sum(x^2) ~= 1.0
        norm = sum(x * x for x in emb)
        assert pytest.approx(norm, rel=1e-4) == 1.0


@pytest.mark.asyncio
async def test_mock_embedding_deterministic_and_similarity():
    """Identical text must yield identical vectors (sim=1.0) and related text must have higher similarity."""
    provider = MockEmbeddingProvider()
    query = "deep learning neural network optimization"
    related = "neural network optimization techniques and deep learning"
    unrelated = "botanical classification of prehistoric ferns"

    vec_query = await provider.embed_query(query)
    vec_query_again = await provider.embed_query(query)
    vec_related = await provider.embed_query(related)
    vec_unrelated = await provider.embed_query(unrelated)

    sim_identical = cosine_similarity(vec_query, vec_query_again)
    sim_related = cosine_similarity(vec_query, vec_related)
    sim_unrelated = cosine_similarity(vec_query, vec_unrelated)

    assert pytest.approx(sim_identical, rel=1e-4) == 1.0
    assert sim_related > 0.5
    assert sim_related > sim_unrelated


@pytest.mark.asyncio
async def test_embedding_service_batching_and_deduplication():
    """Ensure large chunk sets are batched and duplicates are cached to conserve compute."""
    mock_provider = MockEmbeddingProvider()
    service = EmbeddingService(provider=mock_provider, batch_size=25)

    # 60 texts with intentional duplicates
    texts = ["Unique text alpha"] * 20 + ["Unique text beta"] * 20 + [f"Dynamic text {i}" for i in range(20)]
    assert len(texts) == 60

    embeddings = await service.embed_chunks(texts)
    assert len(embeddings) == 60

    # Ensure duplicate items have identical embeddings
    assert embeddings[0] == embeddings[1] == embeddings[19]
    assert embeddings[20] == embeddings[21] == embeddings[39]


@pytest.mark.asyncio
async def test_embedding_dimension_mismatch_validation():
    """Service must reject provider output if dimension does not match configured vector size."""
    faulty_provider = MockEmbeddingProvider(dimension=512)
    service = EmbeddingService(provider=faulty_provider, expected_dimension=1536)

    with pytest.raises(ValueError, match="does not match expected dimension"):
        await service.embed_chunks(["Test excerpt"])

    with pytest.raises(ValueError, match="does not match expected dimension"):
        await service.embed_query("Test query")


@pytest.mark.asyncio
async def test_openai_embedding_provider_retry_on_rate_limit():
    """OpenAI provider must retry upon receiving 429 rate limit errors."""
    provider = OpenAIEmbeddingProvider(api_key="sk-test-mock-key", max_retries=3)

    mock_response_429 = MagicMock()
    mock_response_429.status_code = 429

    mock_response_200 = MagicMock()
    mock_response_200.status_code = 200
    mock_response_200.json.return_value = {
        "data": [{"embedding": [0.1] * settings.EMBEDDING_DIMENSION}]
    }

    with patch("httpx.AsyncClient.post", side_effect=[mock_response_429, mock_response_200]) as mock_post:
        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await provider.embed_texts(["Retry test text"])
            assert len(result) == 1
            assert len(result[0]) == settings.EMBEDDING_DIMENSION
            assert mock_post.call_count == 2


@pytest.mark.asyncio
async def test_provider_factory_fallback():
    """Factory should cleanly fall back to Mock provider when keys are not configured."""
    with patch.object(settings, "EMBEDDING_PROVIDER", "mock"):
        p1 = get_embedding_provider()
        assert isinstance(p1, MockEmbeddingProvider)

    with patch.object(settings, "EMBEDDING_PROVIDER", "openai"):
        with patch.object(settings, "OPENAI_API_KEY", None):
            p2 = get_embedding_provider()
            assert isinstance(p2, MockEmbeddingProvider)
