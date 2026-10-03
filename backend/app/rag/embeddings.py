from typing import List
from abc import ABC, abstractmethod

class EmbeddingProvider(ABC):
    @abstractmethod
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        pass

    @abstractmethod
    def embed_query(self, text: str) -> List[float]:
        pass

class NoOpEmbeddingProvider(EmbeddingProvider):
    """
    Fallback embedding provider for when semantic retrieval is disabled 
    or dependencies are not available. Returns empty vectors.
    """
    def __init__(self, dimension: int = 768):
        self.dimension = dimension

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [[0.0] * self.dimension for _ in texts]

    def embed_query(self, text: str) -> List[float]:
        return [0.0] * self.dimension

import os
import logging

logger = logging.getLogger(__name__)

class FastEmbedProvider(EmbeddingProvider):
    """
    Lightweight embedding provider using FastEmbed (ONNX).
    Runs completely locally without requiring API keys or heavy PyTorch dependencies.
    """
    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5"):
        try:
            from fastembed import TextEmbedding
            self.model = TextEmbedding(model_name=model_name)
            self.dimension = 384
            self.is_ready = True
            logger.info(f"FastEmbed initialized with model: {model_name}")
        except ImportError:
            logger.error("fastembed not installed. Semantic retrieval will fail or fallback.")
            self.is_ready = False
        except Exception as e:
            logger.error(f"Failed to initialize FastEmbed: {e}")
            self.is_ready = False
            
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not self.is_ready or not texts:
            return []
        try:
            embeddings = list(self.model.embed(texts))
            # Convert from numpy arrays to list of floats for JSON serialization
            return [e.tolist() for e in embeddings]
        except Exception as e:
            logger.error(f"Embedding API failed: {e}")
            return []

    def embed_query(self, text: str) -> List[float]:
        if not self.is_ready:
            return []
        try:
            # fastembed returns an iterator of numpy arrays
            embeddings = list(self.model.embed([text]))
            return embeddings[0].tolist() if embeddings else []
        except Exception as e:
            logger.error(f"Query embedding failed: {e}")
            return []

def get_embedding_provider() -> EmbeddingProvider:
    try:
        import fastembed
        return FastEmbedProvider()
    except ImportError:
        return NoOpEmbeddingProvider()

