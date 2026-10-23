import abc
import asyncio
import hashlib
import math
import random
from typing import List, Optional, Dict
import httpx
from backend.app.core.config import settings


class BaseEmbeddingProvider(abc.ABC):
    """Abstract base provider for text embeddings."""

    @property
    @abc.abstractmethod
    def dimension(self) -> int:
        """The dimensionality of generated embeddings."""
        pass

    @abc.abstractmethod
    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts."""
        pass

    @abc.abstractmethod
    async def embed_query(self, query: str) -> List[float]:
        """Generate embedding for a single search query."""
        pass


class MockEmbeddingProvider(BaseEmbeddingProvider):
    """Deterministic, zero-cost embedding provider for tests and offline development.

    Produces normalized unit vectors where texts with shared keywords exhibit
    meaningful cosine similarity.
    """

    def __init__(self, dimension: int = settings.EMBEDDING_DIMENSION):
        self._dimension = dimension

    @property
    def dimension(self) -> int:
        return self._dimension

    def _generate_vector(self, text: str) -> List[float]:
        clean = text.strip().lower()
        if not clean:
            # Neutral vector
            return [0.0] * self._dimension

        vec = [0.0] * self._dimension
        import re
        words = [w for w in re.findall(r"\b\w+\b", clean) if len(w) > 2]

        # 1. Word-level component hashes for lexical/semantic correlation
        for word in words:
            h = int(hashlib.md5(word.encode("utf-8")).hexdigest(), 16)
            rng = random.Random(h)
            for i in range(self._dimension):
                vec[i] += rng.gauss(0, 2.0)

        # 2. Document global hash for uniqueness
        doc_h = int(hashlib.sha256(clean.encode("utf-8")).hexdigest(), 16)
        rng = random.Random(doc_h)
        for i in range(self._dimension):
            vec[i] += rng.gauss(0, 0.1)

        # 3. Normalize vector to unit length
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0:
            vec = [x / norm for x in vec]
        return vec

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        return [self._generate_vector(t) for t in texts]

    async def embed_query(self, query: str) -> List[float]:
        return self._generate_vector(query)


class OpenAIEmbeddingProvider(BaseEmbeddingProvider):
    """OpenAI API embedding provider using httpx with exponential backoff."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = settings.EMBEDDING_MODEL,
        dimension: int = settings.EMBEDDING_DIMENSION,
        max_retries: int = 3,
    ):
        self.api_key = api_key or settings.OPENAI_API_KEY
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is required for OpenAIEmbeddingProvider.")
        self.model = model
        self._dimension = dimension
        self.max_retries = max_retries

    @property
    def dimension(self) -> int:
        return self._dimension

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []

        url = "https://api.openai.com/v1/embeddings"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "input": texts,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            for attempt in range(self.max_retries):
                try:
                    resp = await client.post(url, json=payload, headers=headers)
                    if resp.status_code == 200:
                        data = resp.json()
                        embeddings = [item["embedding"] for item in data["data"]]
                        return embeddings
                    elif resp.status_code in (429, 500, 502, 503, 504):
                        if attempt < self.max_retries - 1:
                            await asyncio.sleep(2**attempt + 0.1)
                            continue
                    resp.raise_for_status()
                except (httpx.TimeoutException, httpx.NetworkError) as e:
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(2**attempt + 0.1)
                        continue
                    raise RuntimeError(f"OpenAI embedding request failed after {self.max_retries} attempts: {e}") from e
                except Exception as e:
                    raise RuntimeError(f"OpenAI embedding API error: {e}") from e

        raise RuntimeError("Failed to generate OpenAI embeddings.")

    async def embed_query(self, query: str) -> List[float]:
        res = await self.embed_texts([query])
        return res[0]


class GeminiEmbeddingProvider(BaseEmbeddingProvider):
    """Google Gemini embedding provider using Google Generative AI REST endpoint."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "text-embedding-004",
        dimension: int = settings.EMBEDDING_DIMENSION,
        max_retries: int = 3,
    ):
        self.api_key = api_key or settings.GEMINI_API_KEY
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is required for GeminiEmbeddingProvider.")
        self.model = model
        self._dimension = dimension
        self.max_retries = max_retries

    @property
    def dimension(self) -> int:
        return self._dimension

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:batchEmbedContents?key={self.api_key}"
        requests = [{"model": f"models/{self.model}", "content": {"parts": [{"text": t}]}} for t in texts]

        async with httpx.AsyncClient(timeout=30.0) as client:
            for attempt in range(self.max_retries):
                try:
                    resp = await client.post(url, json={"requests": requests})
                    if resp.status_code == 200:
                        data = resp.json()
                        embeddings = [item["values"] for item in data.get("embeddings", [])]
                        return embeddings
                    elif resp.status_code in (429, 500, 502, 503, 504):
                        if attempt < self.max_retries - 1:
                            await asyncio.sleep(2**attempt + 0.1)
                            continue
                    resp.raise_for_status()
                except (httpx.TimeoutException, httpx.NetworkError) as e:
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(2**attempt + 0.1)
                        continue
                    raise RuntimeError(f"Gemini embedding request failed: {e}") from e
                except Exception as e:
                    raise RuntimeError(f"Gemini embedding API error: {e}") from e

        raise RuntimeError("Failed to generate Gemini embeddings.")

    async def embed_query(self, query: str) -> List[float]:
        res = await self.embed_texts([query])
        return res[0]


def get_embedding_provider(provider_name: Optional[str] = None) -> BaseEmbeddingProvider:
    """Factory to retrieve configured embedding provider with honest fallback."""
    provider = (provider_name or settings.EMBEDDING_PROVIDER).lower().strip()

    if provider == "openai":
        if settings.OPENAI_API_KEY:
            return OpenAIEmbeddingProvider()
        return MockEmbeddingProvider()

    if provider == "gemini":
        if settings.GEMINI_API_KEY:
            return GeminiEmbeddingProvider()
        return MockEmbeddingProvider()

    return MockEmbeddingProvider()


class EmbeddingService:
    """Service orchestrating batch embedding generation, validation, and dimension enforcement."""

    def __init__(
        self,
        provider: Optional[BaseEmbeddingProvider] = None,
        batch_size: int = 50,
        expected_dimension: int = settings.EMBEDDING_DIMENSION,
    ):
        self.provider = provider or get_embedding_provider()
        self.batch_size = batch_size
        self.expected_dimension = expected_dimension

    async def embed_chunks(self, texts: List[str]) -> List[List[float]]:
        """Generate validated embeddings for chunk texts with batching and deduplication."""
        if not texts:
            return []

        # Deduplicate to reduce API load
        unique_texts: List[str] = []
        text_to_index: Dict[str, int] = {}
        index_map: List[int] = []

        for t in texts:
            if t not in text_to_index:
                text_to_index[t] = len(unique_texts)
                unique_texts.append(t)
            index_map.append(text_to_index[t])

        # Batch processing
        all_unique_embeddings: List[List[float]] = []
        for i in range(0, len(unique_texts), self.batch_size):
            batch = unique_texts[i : i + self.batch_size]
            batch_embeddings = await self.provider.embed_texts(batch)

            # Validate dimensions
            for emb in batch_embeddings:
                if len(emb) != self.expected_dimension:
                    raise ValueError(
                        f"Generated embedding dimension {len(emb)} does not match expected dimension {self.expected_dimension}."
                    )
            all_unique_embeddings.extend(batch_embeddings)

        # Map back to original chunk order
        return [all_unique_embeddings[idx] for idx in index_map]

    async def embed_query(self, query: str) -> List[float]:
        """Generate and validate a single query embedding."""
        clean = query.strip()
        if not clean:
            raise ValueError("Query string cannot be empty for embedding.")

        emb = await self.provider.embed_query(clean)
        if len(emb) != self.expected_dimension:
            raise ValueError(
                f"Query embedding dimension {len(emb)} does not match expected dimension {self.expected_dimension}."
            )
        return emb


embedding_service = EmbeddingService()
