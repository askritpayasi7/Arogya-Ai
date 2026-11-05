import hashlib
import logging
import re
import time
from abc import ABC, abstractmethod
from typing import List, Tuple
import requests

from health_app.config import settings

logger = logging.getLogger(__name__)

# In-memory cooldown tracking to prevent blocking when Ollama is unavailable
_OLLAMA_FAILED_UNTIL: float = 0.0
_OLLAMA_COOLDOWN_SECONDS: float = 60.0


def mark_ollama_failure(cooldown_seconds: float = _OLLAMA_COOLDOWN_SECONDS) -> None:
    """Mark Ollama as temporarily unreachable to bypass repeated connection timeouts."""
    global _OLLAMA_FAILED_UNTIL
    _OLLAMA_FAILED_UNTIL = time.time() + cooldown_seconds


def is_ollama_in_cooldown() -> bool:
    """Check if Ollama failure cooldown is currently active."""
    global _OLLAMA_FAILED_UNTIL
    return time.time() < _OLLAMA_FAILED_UNTIL


class BaseEmbeddingProvider(ABC):
    """Abstract base class for text embedding generation."""

    @abstractmethod
    def embed_query(self, text: str) -> List[float]:
        """Generate embedding vector for a single query text."""
        pass

    @abstractmethod
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Generate embedding vectors for a list of documents."""
        pass

    @abstractmethod
    def check_connection(self) -> Tuple[bool, str]:
        """Check if embedding service and model are ready. Returns (is_ready, message)."""
        pass


class OllamaEmbeddingProvider(BaseEmbeddingProvider):
    """Embedding provider using Ollama HTTP API."""

    def __init__(self, base_url: str | None = None, model: str | None = None, timeout: int = 3):
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self.model = model or settings.ollama_embed_model
        self.timeout = timeout

    def check_connection(self) -> Tuple[bool, str]:
        """Verify Ollama server is running and model is available."""
        if is_ollama_in_cooldown():
            return False, f"Ollama is in cooling-down state. Retry in {int(_OLLAMA_FAILED_UNTIL - time.time())}s."
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=2)
            if resp.status_code != 200:
                mark_ollama_failure()
                return False, f"Ollama returned HTTP status {resp.status_code}."

            data = resp.json()
            models = [m.get("name", "") for m in data.get("models", [])]
            # Match model name either exact or prefix (e.g. nomic-embed-text:latest)
            matched = any(self.model in m or m.startswith(self.model) for m in models)
            if not matched:
                return False, (
                    f"Ollama server is active, but model '{self.model}' was not found. "
                    f"Run `ollama pull {self.model}` in your terminal."
                )
            return True, f"Ollama server is connected and model '{self.model}' is ready."
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            mark_ollama_failure()
            return False, (
                f"Cannot connect to Ollama at {self.base_url}: {e}. "
                "Ensure Ollama is installed and running (`ollama serve`)."
            )
        except Exception as e:
            mark_ollama_failure()
            return False, f"Ollama health check error: {str(e)}"

    def embed_query(self, text: str) -> List[float]:
        """Embed a single query."""
        results = self.embed_documents([text])
        return results[0]

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using Ollama's /api/embeddings or /api/embed."""
        if not texts:
            return []

        if is_ollama_in_cooldown():
            raise ConnectionError(
                f"Ollama is temporarily offline/timing out. Cool-down active for {int(_OLLAMA_FAILED_UNTIL - time.time())}s."
            )

        embeddings: List[List[float]] = []

        # Try /api/embed first (newer Ollama batch API)
        try:
            resp = requests.post(
                f"{self.base_url}/api/embed",
                json={"model": self.model, "input": texts},
                timeout=self.timeout
            )
            if resp.status_code == 200:
                payload = resp.json()
                if "embeddings" in payload:
                    return payload["embeddings"]
            elif resp.status_code in (404, 500):
                logger.debug(f"/api/embed returned HTTP {resp.status_code}. Trying /api/embeddings.")
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            mark_ollama_failure()
            raise ConnectionError(
                f"Ollama connection error/timeout ({self.base_url}): {e}. "
                f"Ensure Ollama is running and `{self.model}` is pulled (`ollama pull {self.model}`)."
            ) from e
        except Exception as e:
            logger.debug(f"/api/embed not available or failed: {e}. Falling back to /api/embeddings per item.")

        # Fallback to /api/embeddings item by item
        for text in texts:
            try:
                resp = requests.post(
                    f"{self.base_url}/api/embeddings",
                    json={"model": self.model, "prompt": text},
                    timeout=self.timeout
                )
                resp.raise_for_status()
                data = resp.json()
                embedding = data.get("embedding")
                if not embedding:
                    raise ValueError(f"No embedding returned from Ollama for text: {text[:40]}...")
                embeddings.append(embedding)
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                mark_ollama_failure()
                raise ConnectionError(
                    f"Failed to fetch embedding from Ollama ({self.base_url}): {e}. "
                    f"Ensure Ollama is running and `{self.model}` is pulled (`ollama pull {self.model}`)."
                ) from e
            except requests.exceptions.RequestException as e:
                mark_ollama_failure()
                raise ConnectionError(
                    f"Failed to fetch embedding from Ollama ({self.base_url}): {e}. "
                    f"Ensure Ollama is running and `{self.model}` is pulled (`ollama pull {self.model}`)."
                ) from e

        return embeddings


class MockEmbeddingProvider(BaseEmbeddingProvider):
    """Deterministic mock embedding provider for tests and offline dry-runs."""

    def __init__(self, dimension: int = 128):
        self.dimension = dimension

    def check_connection(self) -> Tuple[bool, str]:
        return True, "Mock embedding provider is always ready."

    def embed_query(self, text: str) -> List[float]:
        return self._generate_vector(text)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self._generate_vector(t) for t in texts]

    def _generate_vector(self, text: str) -> List[float]:
        """Generate a deterministic token-frequency normalized vector."""
        words = re.findall(r'\w+', text.lower())
        vector = [0.0] * self.dimension
        if not words:
            return vector
        for word in words:
            idx = int(hashlib.md5(word.encode("utf-8")).hexdigest(), 16) % self.dimension
            vector[idx] += 1.0
        norm = sum(x * x for x in vector) ** 0.5 or 1.0
        return [x / norm for x in vector]


def get_embedding_provider(provider_type: str = "ollama") -> BaseEmbeddingProvider:
    """Factory to get the appropriate embedding provider."""
    if provider_type.lower() == "mock":
        return MockEmbeddingProvider()
    if is_ollama_in_cooldown():
        return MockEmbeddingProvider()
    return OllamaEmbeddingProvider()
