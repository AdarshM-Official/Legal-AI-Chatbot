"""
RAG (Retrieval-Augmented Generation) service for LegalAI.

Provides:
    - get_chroma_collection()      – returns (or creates) the persistent ChromaDB collection
    - retrieve_legal_documents()   – semantic search → Django LegalDocument objects

Design decisions:
    - ChromaDB client and collection are cached at module level after first use.
    - Distance threshold and top-k are read from Django settings so they can be
      tuned without changing code.
    - All retrieval logic lives here, not in views.py.
"""

import logging

from django.conf import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level cache so we don't re-open ChromaDB on every request
# ---------------------------------------------------------------------------
_chroma_client = None
_chroma_collection = None

COLLECTION_NAME = "legal_documents"


def get_chroma_collection():
    """
    Return the persistent ChromaDB collection, creating the client
    and collection on first call.

    Storage path is read from settings.CHROMA_DB_PATH (a Path object).
    """
    global _chroma_client, _chroma_collection

    if _chroma_collection is not None:
        return _chroma_collection

    try:
        import chromadb

        chroma_path = str(settings.CHROMA_DB_PATH)
        logger.info("Opening ChromaDB at: %s", chroma_path)

        _chroma_client = chromadb.PersistentClient(path=chroma_path)
        _chroma_collection = _chroma_client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "l2"},   # L2 distance (lower = more similar)
        )

        count = _chroma_collection.count()
        logger.info(
            "ChromaDB collection '%s' opened — %d document(s) indexed.",
            COLLECTION_NAME,
            count,
        )
        return _chroma_collection

    except Exception as exc:
        logger.error("Failed to open ChromaDB collection: %s", exc)
        raise


def reset_collection_cache():
    """
    Force the next call to get_chroma_collection() to re-open the DB.
    Useful after re-indexing from a management command in the same process.
    """
    global _chroma_client, _chroma_collection
    _chroma_client = None
    _chroma_collection = None


def retrieve_legal_documents(query: str, top_k: int = None) -> list:
    """
    Perform semantic search over the ChromaDB legal document collection.

    Parameters
    ----------
    query : str
        The user's natural-language legal question.
    top_k : int, optional
        Number of candidates to fetch.  Defaults to settings.RAG_TOP_K.

    Returns
    -------
    list of dict
        Each dict has:
            "document"      : LegalDocument Django ORM object (or None if not found)
            "distance"      : float  (L2 distance — lower is more similar)
            "django_id"     : int
            "law_type"      : str
            "title"         : str
            "chroma_id"     : str
        Only results whose distance is ≤ settings.RAG_RELEVANCE_THRESHOLD are included.
        Returns an empty list if ChromaDB is empty or on error.
    """
    from core.models import LegalDocument  # avoid circular import at module load

    if top_k is None:
        top_k = getattr(settings, "RAG_TOP_K", 5)

    threshold = getattr(settings, "RAG_RELEVANCE_THRESHOLD", 1.2)

    # ── 1. Generate query embedding ──────────────────────────────────────────
    try:
        from core.services.embeddings import get_embedding
        query_embedding = get_embedding(query)
    except Exception as exc:
        logger.error("Embedding generation failed for query '%s': %s", query, exc)
        return []

    # ── 2. Search ChromaDB ───────────────────────────────────────────────────
    try:
        collection = get_chroma_collection()

        if collection.count() == 0:
            logger.warning("ChromaDB collection is empty — no documents indexed yet.")
            return []

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, collection.count()),
            include=["metadatas", "distances"],
        )
    except Exception as exc:
        logger.error("ChromaDB query failed: %s", exc)
        return []

    # ── 3. Unpack results ────────────────────────────────────────────────────
    ids = results.get("ids", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    if not ids:
        return []

    # ── 4. Apply relevance threshold & resolve to Django ORM objects ─────────
    django_ids_needed = []
    raw_hits = []

    for chroma_id, meta, dist in zip(ids, metadatas, distances):
        if dist > threshold:
            continue   # too weak — skip

        django_id = meta.get("django_id")
        if django_id is None:
            continue

        django_ids_needed.append(int(django_id))
        raw_hits.append({
            "chroma_id": chroma_id,
            "django_id": int(django_id),
            "law_type": meta.get("law_type", ""),
            "title": meta.get("title", ""),
            "distance": dist,
        })

    if not django_ids_needed:
        return []

    # Bulk fetch from SQLite — one query, preserve order via dict
    try:
        qs = LegalDocument.objects.filter(id__in=django_ids_needed)
        doc_map = {doc.id: doc for doc in qs}
    except Exception as exc:
        logger.error("SQLite lookup failed for django_ids %s: %s", django_ids_needed, exc)
        return []

    # ── 5. Build final result list ───────────────────────────────────────────
    output = []
    for hit in raw_hits:
        doc = doc_map.get(hit["django_id"])
        output.append({
            "document": doc,          # may be None if DB record was deleted
            "distance": hit["distance"],
            "django_id": hit["django_id"],
            "law_type": hit["law_type"],
            "title": hit["title"],
            "chroma_id": hit["chroma_id"],
        })

    return output

