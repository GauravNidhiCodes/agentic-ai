"""
Memory Manager
- Short-term: last N messages (handled in agent.py via DB)
- Long-term: FAISS vector store per chat_id
- Embeddings: sentence-transformers (local, free)
"""
 
import os
import json
import pickle
from pathlib import Path
 
MEMORY_DIR = Path("./memory_store")
MEMORY_DIR.mkdir(exist_ok=True)
 
# Lazy imports — only load heavy libs when needed
_embedder = None
_faiss = None
 
 
def _get_embedder():
    global _embedder
    if _embedder is None:
        try:
            from sentence_transformers import SentenceTransformer
            _embedder = SentenceTransformer("all-MiniLM-L6-v2")
        except ImportError:
            _embedder = None
    return _embedder
 
 
def _get_faiss():
    global _faiss
    if _faiss is None:
        try:
            import faiss
            _faiss = faiss
        except ImportError:
            _faiss = None
    return _faiss
 
 
class MemoryManager:
    def __init__(self):
        self.embedder = _get_embedder()
        self.faiss = _get_faiss()
        self._available = self.embedder is not None and self.faiss is not None
 
    def _index_path(self, chat_id: str):
        return MEMORY_DIR / f"{chat_id}.index"
 
    def _meta_path(self, chat_id: str):
        return MEMORY_DIR / f"{chat_id}.meta"
 
    def _load_index(self, chat_id: str):
        ip = self._index_path(chat_id)
        mp = self._meta_path(chat_id)
        if ip.exists() and mp.exists():
            index = self.faiss.read_index(str(ip))
            with open(mp, "rb") as f:
                meta = pickle.load(f)
            return index, meta
        # New index
        import numpy as np
        dim = 384  # all-MiniLM-L6-v2 dimension
        index = self.faiss.IndexFlatL2(dim)
        return index, []
 
    def _save_index(self, chat_id: str, index, meta: list):
        self.faiss.write_index(index, str(self._index_path(chat_id)))
        with open(self._meta_path(chat_id), "wb") as f:
            pickle.dump(meta, f)
 
    def store(self, chat_id: str, text: str):
        """Embed and store a memory chunk."""
        if not self._available:
            return  # Silently skip if libs not available
 
        import numpy as np
        embedding = self.embedder.encode([text], convert_to_numpy=True).astype("float32")
        index, meta = self._load_index(chat_id)
        index.add(embedding)
        meta.append(text)
        self._save_index(chat_id, index, meta)
 
    def search(self, chat_id: str, query: str, k: int = 3) -> list:
        """Return top-k most relevant memory strings."""
        if not self._available:
            return []
 
        import numpy as np
        index, meta = self._load_index(chat_id)
 
        if index.ntotal == 0:
            return []
 
        query_vec = self.embedder.encode([query], convert_to_numpy=True).astype("float32")
        k = min(k, index.ntotal)
        distances, indices = index.search(query_vec, k)
 
        results = []
        for idx in indices[0]:
            if 0 <= idx < len(meta):
                results.append(meta[idx])
        return results
 
    def store_conversation_turn(self, chat_id: str, user_input: str, ai_response: str):
        """Store a conversation turn as a combined memory chunk."""
        chunk = f"User: {user_input}\nAssistant: {ai_response}"
        self.store(chat_id, chunk)
 