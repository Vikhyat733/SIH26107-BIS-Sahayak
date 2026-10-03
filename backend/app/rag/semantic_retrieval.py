import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from ..core.config import DATA_DIR
from .embeddings import get_embedding_provider
from .retrieval import Document, _store as bm25_store

logger = logging.getLogger(__name__)

INDEX_FILE = DATA_DIR / "semantic_index.json"

def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    dot = sum(x * y for x, y in zip(v1, v2))
    mag1 = sum(x * x for x in v1) ** 0.5
    mag2 = sum(x * x for x in v2) ** 0.5
    if mag1 == 0 or mag2 == 0:
        return 0.0
    return dot / (mag1 * mag2)

class SemanticStore:
    def __init__(self):
        self.provider = get_embedding_provider()
        self.embeddings: Dict[str, List[float]] = {}
        # We hold a reference to documents from bm25_store to avoid duplication in memory
        self.documents: Dict[str, Document] = {}
        self.is_ready = False
        
    def initialize(self):
        """Loads or builds the semantic index. Designed to be deterministic and safe."""
        if type(self.provider).__name__ == "NoOpEmbeddingProvider":
            logger.warning("No embedding provider available. Semantic retrieval disabled.")
            return

        for doc in bm25_store.documents:
            self.documents[doc.document_id] = doc

        if INDEX_FILE.exists():
            try:
                data = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
                self.embeddings = data
                self.is_ready = True
                logger.info(f"Loaded semantic index with {len(self.embeddings)} documents.")
                return
            except Exception as e:
                logger.error(f"Failed to load semantic index: {e}")
                
        # If no index exists, build it
        self.build_index()

    def build_index(self):
        logger.info("Building semantic index...")
        if not self.documents:
            return
            
        docs_to_embed = list(self.documents.values())
        texts = [f"{d.title}\n{d.content}" for d in docs_to_embed]
        
        try:
            vectors = self.provider.embed_documents(texts)
            if not vectors or len(vectors) != len(docs_to_embed):
                logger.error("Embedding generation failed or returned mismatched counts.")
                return
                
            for doc, vec in zip(docs_to_embed, vectors):
                self.embeddings[doc.document_id] = vec
                
            # Persist
            INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)
            INDEX_FILE.write_text(json.dumps(self.embeddings), encoding="utf-8")
            self.is_ready = True
            logger.info(f"Successfully built and saved semantic index for {len(self.embeddings)} documents.")
            
        except Exception as e:
            logger.error(f"Failed to build semantic index: {e}")

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        if not self.is_ready or not self.embeddings:
            return []
            
        try:
            q_vec = self.provider.embed_query(query)
            if not q_vec:
                return []
                
            results = []
            for doc_id, doc_vec in self.embeddings.items():
                if doc_id not in self.documents:
                    continue
                score = cosine_similarity(q_vec, doc_vec)
                results.append({
                    "score": round(score, 4),
                    "document": self.documents[doc_id],
                    "method": "semantic_cosine"
                })
                
            results.sort(key=lambda x: x["score"], reverse=True)
            return results[:top_k]
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return []

# Singleton instance
_semantic_store = SemanticStore()

def init_semantic_store():
    _semantic_store.initialize()

def retrieve_semantic_documents(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """
    Returns multiple candidates using semantic retrieval.
    Safe fallback: Returns empty list if disabled or fails.
    """
    results = _semantic_store.search(query, top_k=top_k)
    candidates = []
    for r in results:
        doc = r["document"]
        candidates.append({
            "document": doc,
            "retrieval_score": r["score"],
            "retrieval_method": r["method"],
            "provenance": {
                "source": doc.authority,
                "url": doc.source_url
            }
        })
    return candidates
