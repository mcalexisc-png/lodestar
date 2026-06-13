# services/docs/__init__.py
"""Docs service — personal document RAG with ChromaDB.

Thin facade: DocsService lives here, RAGManager/VectorRAG are re-exported
from the canonical implementations in src/.
"""

from .service import DocsService, DocChunk, IndexResult

__all__ = [
    "DocsService",
    "DocChunk",
    "IndexResult",
    "RAGManager",
    "VectorRAG",
]


def __getattr__(name):
    """Lazy re-export of heavy src modules (numpy, chromadb).

    ``src.rag_vector`` imports ``numpy`` at module level (~35 MB RSS).
    Eagerly importing it here when ``services`` is first pulled in (via
    ``from services.youtube import init_youtube`` in ``app.py``) regresses
    full-mode idle RSS by ~145 MB.  Defer to first actual use.
    """
    if name == "RAGManager":
        from src.rag_manager import RAGManager
        return RAGManager
    if name == "VectorRAG":
        from src.rag_vector import VectorRAG
        return VectorRAG
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
