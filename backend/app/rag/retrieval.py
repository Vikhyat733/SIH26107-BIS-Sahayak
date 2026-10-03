import math
import json
import logging
from typing import List, Dict, Any, Optional
from collections import Counter
from pydantic import BaseModel
from pathlib import Path
from ..core.config import STANDARDS_DIR, QCO_FILE
from ..services.bis_general_service import DEFAULT_KB

logger = logging.getLogger(__name__)

class Document(BaseModel):
    document_id: str
    source_type: str  # 'standard', 'qco', 'general'
    title: str
    standard_number: Optional[str] = None
    section: Optional[str] = None
    content: str
    aliases: List[str] = []
    metadata: Dict[str, Any] = {}
    source_url: str
    authority: str

class BM25Okapi:
    def __init__(self, corpus: List[List[str]], k1: float = 1.5, b: float = 0.75):
        self.corpus_size = len(corpus)
        self.avgdl = sum(len(doc) for doc in corpus) / self.corpus_size if self.corpus_size else 0
        self.doc_freqs = []
        self.idf = {}
        self.doc_len = []
        self.k1 = k1
        self.b = b
        
        # Calculate IDF and document frequencies
        df = Counter()
        for document in corpus:
            self.doc_len.append(len(document))
            frequencies = Counter(document)
            self.doc_freqs.append(frequencies)
            for word in frequencies:
                df[word] += 1
                
        for word, freq in df.items():
            # Standard BM25 IDF
            self.idf[word] = math.log(1 + (self.corpus_size - freq + 0.5) / (freq + 0.5))

    def get_scores(self, query: List[str]) -> List[float]:
        scores = [0.0] * self.corpus_size
        for q in query:
            q_idf = self.idf.get(q, 0)
            if q_idf == 0:
                continue
            for i in range(self.corpus_size):
                f = self.doc_freqs[i].get(q, 0)
                if f > 0:
                    score = q_idf * (f * (self.k1 + 1)) / (f + self.k1 * (1 - self.b + self.b * self.doc_len[i] / self.avgdl))
                    scores[i] += score
        return scores

def tokenize(text: str) -> List[str]:
    # Simple whitespace and punctuation tokenizer
    text = text.lower()
    for p in "?.,!;:()[]{}|\"'-":
        text = text.replace(p, " ")
    return [w for w in text.split() if w]

class RetrievalStore:
    def __init__(self):
        self.documents: List[Document] = []
        self.corpus: List[List[str]] = []
        self.bm25: Optional[BM25Okapi] = None
        self._load_all()
        
    def _load_all(self):
        self.documents = []
        
        # Load Standards
        if STANDARDS_DIR.exists():
            for path in STANDARDS_DIR.glob("*.json"):
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                    # Extract text blob for indexing
                    content_blob = json.dumps(data, ensure_ascii=False)
                    std_no = data.get("standard_code", data.get("standard", path.stem.replace("_", ":", 1)))
                    self.documents.append(Document(
                        document_id=path.stem,
                        source_type="standard",
                        title=data.get("title", path.stem),
                        standard_number=std_no,
                        content=content_blob,
                        aliases=[], # Handled in reranker
                        source_url=data.get("source_url", "https://www.bis.gov.in/"),
                        authority=data.get("source", "Bureau of Indian Standards")
                    ))
                except Exception as e:
                    logger.error(f"Error loading standard {path}: {e}")
                    
        # Load QCOs
        if QCO_FILE.exists():
            try:
                registry = json.loads(QCO_FILE.read_text(encoding="utf-8"))
                for i, qco in enumerate(registry):
                    content_blob = json.dumps(qco, ensure_ascii=False)
                    self.documents.append(Document(
                        document_id=f"qco_{i}",
                        source_type="qco",
                        title=qco.get("title", qco.get("product_name", "Unknown QCO")),
                        standard_number=None,
                        content=content_blob,
                        source_url=qco.get("source_url", "https://www.bis.gov.in/quality-control-orders/"),
                        authority="Bureau of Indian Standards"
                    ))
            except Exception as e:
                logger.error(f"Error loading QCOs: {e}")
                
        # Load General KB
        for item in DEFAULT_KB:
            self.documents.append(Document(
                document_id=item['id'],
                source_type="general",
                title=item['title'],
                section=item.get("section"),
                content=item['title'] + " " + item['content'],
                aliases=item.get("search_queries", []),
                source_url=item.get('source_url', 'https://www.bis.gov.in/'),
                authority=item.get('source', 'Bureau of Indian Standards')
            ))
            
        self.corpus = [tokenize(doc.content) for doc in self.documents]
        if self.corpus:
            self.bm25 = BM25Okapi(self.corpus)
            
    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        if not self.bm25 or not self.documents:
            return []
            
        tokenized_query = tokenize(query)
        stopwords = {"which", "standard", "standards", "applies", "to", "for", "the", "a", "an", "is", "what", "are", 
                     "does", "do", "require", "get", "how", "need", "product", "products"}
        tokenized_query = [q for q in tokenized_query if q not in stopwords]
        
        if not tokenized_query:
            return []
            
        scores = self.bm25.get_scores(tokenized_query)
        
        results = []
        for i, score in enumerate(scores):
            if score > 0:
                results.append({
                    "score": round(score, 4),
                    "document": self.documents[i],
                    "method": "bm25_lexical"
                })
                
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

# Singleton instance
_store = RetrievalStore()

def retrieve_documents(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """
    Returns multiple candidates using BM25 lexical retrieval.
    Each candidate contains: document, retrieval score, retrieval method, provenance.
    """
    logger.info(f"Retrieving top {top_k} documents for query: {query}")
    results = _store.search(query, top_k=top_k*2) # Retrieve more for reranking
    
    # Format to preserve the exact required candidate structure
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
