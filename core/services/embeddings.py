"""
Embedding service for LegalAI RAG pipeline.

Uses sentence-transformers/all-MiniLM-L6-v2 as a local embedding model.
The model is loaded once as a module-level singleton to avoid reloading
on every request.
"""

import logging
import re

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Singleton: loaded once when this module is first imported
# ---------------------------------------------------------------------------
_embedding_model = None


def _get_model():
    """Lazily load and cache the SentenceTransformer model."""
    global _embedding_model
    if _embedding_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            logger.info("Loading sentence-transformer model all-MiniLM-L6-v2 ...")
            _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
            logger.info("Embedding model loaded successfully.")
        except Exception as exc:
            logger.error("Failed to load embedding model: %s", exc)
            raise
    return _embedding_model


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def get_embedding(text: str) -> list:
    """
    Generate a single embedding vector for *text*.

    Returns a Python list of floats suitable for ChromaDB.
    """
    model = _get_model()
    vector = model.encode(text, convert_to_numpy=True)
    return vector.tolist()


def get_embeddings(texts: list) -> list:
    """
    Batch-generate embedding vectors for a list of strings.

    Returns a list of lists (one inner list per text).
    """
    if not texts:
        return []
    model = _get_model()
    vectors = model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
    return [v.tolist() for v in vectors]


def prepare_document_text(doc) -> str:
    """
    Build a rich, normalised text representation of a LegalDocument
    for embedding.  Combining multiple fields improves semantic search.

    Field names are taken from the actual LegalDocument model:
        doc_type, title, summary, content
    """
    parts = []

    if doc.doc_type:
        parts.append(f"Law Type: {doc.doc_type.strip()}")

    if doc.title:
        parts.append(f"Title: {doc.title.strip()}")

    if doc.summary:
        parts.append(f"Summary: {doc.summary.strip()}")

    if doc.content:
        # Truncate very long content to keep embedding text manageable
        content_excerpt = doc.content.strip()[:1500]
        parts.append(f"Content: {content_excerpt}")

    raw = " | ".join(parts)

    # Collapse runs of whitespace / newlines
    normalised = re.sub(r"\s+", " ", raw).strip()
    return normalised

