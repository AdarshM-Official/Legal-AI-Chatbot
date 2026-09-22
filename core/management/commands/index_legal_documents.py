"""
Management command: index_legal_documents

Reads all LegalDocument records from SQLite, generates embeddings using the
local sentence-transformer model, and upserts them into the persistent
ChromaDB collection.

Usage:
    python manage.py index_legal_documents           # index new/changed docs
    python manage.py index_legal_documents --rebuild  # wipe collection and re-index all
"""

import logging

from django.core.management.base import BaseCommand
from django.conf import settings

logger = logging.getLogger(__name__)

BATCH_SIZE = 50   # documents per embedding batch


class Command(BaseCommand):
    help = "Index LegalDocument records into ChromaDB for semantic RAG retrieval."

    def add_arguments(self, parser):
        parser.add_argument(
            "--rebuild",
            action="store_true",
            default=False,
            help="Delete the existing ChromaDB collection and re-index everything from scratch.",
        )

    def handle(self, *args, **options):
        from core.models import LegalDocument
        from core.services.embeddings import prepare_document_text, get_embeddings
        from core.services.rag import get_chroma_collection, reset_collection_cache, COLLECTION_NAME
        import chromadb

        rebuild = options["rebuild"]

        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(self.style.SUCCESS("  LegalAI — Indexing Legal Documents into ChromaDB"))
        self.stdout.write(self.style.SUCCESS("=" * 60))

        # ── Handle --rebuild ─────────────────────────────────────────────────
        if rebuild:
            self.stdout.write(
                self.style.WARNING("--rebuild flag set: deleting existing collection...")
            )
            try:
                chroma_path = str(settings.CHROMA_DB_PATH)
                client = chromadb.PersistentClient(path=chroma_path)
                client.delete_collection(name=COLLECTION_NAME)
                reset_collection_cache()
                self.stdout.write(self.style.WARNING("Collection deleted. Re-indexing all documents."))
                # Clear vector_ids so they get re-populated
                LegalDocument.objects.all().update(vector_id=None)
            except Exception as exc:
                self.stderr.write(f"Could not delete collection (may not exist yet): {exc}")
                reset_collection_cache()

        # ── Load ChromaDB collection ─────────────────────────────────────────
        try:
            collection = get_chroma_collection()
        except Exception as exc:
            self.stderr.write(self.style.ERROR(f"Failed to open ChromaDB: {exc}"))
            return

        # ── Fetch documents ──────────────────────────────────────────────────
        if rebuild:
            queryset = LegalDocument.objects.all().order_by("id")
        else:
            # Only index documents that haven't been assigned a vector_id yet
            queryset = LegalDocument.objects.filter(
                vector_id__isnull=True
            ).order_by("id")

        total = queryset.count()

        if total == 0:
            self.stdout.write(
                self.style.WARNING(
                    "No documents to index. "
                    "Run load_ipc / load_new_laws first, or use --rebuild to re-index everything."
                )
            )
            return

        self.stdout.write(f"\nIndexing {total} document(s) in batches of {BATCH_SIZE}...\n")

        # ── Process in batches ───────────────────────────────────────────────
        indexed_count = 0
        error_count = 0

        docs_batch = []
        docs_all = list(queryset)   # materialise once

        for i, doc in enumerate(docs_all):
            docs_batch.append(doc)

            if len(docs_batch) == BATCH_SIZE or i == len(docs_all) - 1:
                # Prepare texts for the batch
                texts = []
                for d in docs_batch:
                    try:
                        texts.append(prepare_document_text(d))
                    except Exception as exc:
                        logger.error("prepare_document_text failed for doc %d: %s", d.id, exc)
                        texts.append(f"{d.doc_type} {d.title}")   # minimal fallback

                # Generate embeddings for the whole batch at once
                try:
                    embeddings = get_embeddings(texts)
                except Exception as exc:
                    self.stderr.write(
                        self.style.ERROR(
                            f"Embedding generation failed for batch starting at doc {docs_batch[0].id}: {exc}"
                        )
                    )
                    error_count += len(docs_batch)
                    docs_batch = []
                    continue

                # Upsert into ChromaDB
                chroma_ids = [f"doc_{d.id}" for d in docs_batch]
                metadatas = [
                    {
                        "django_id": d.id,
                        "law_type": d.doc_type or "",
                        "title": d.title or "",
                        "doc_type": d.doc_type or "",
                    }
                    for d in docs_batch
                ]

                try:
                    collection.upsert(
                        ids=chroma_ids,
                        embeddings=embeddings,
                        metadatas=metadatas,
                    )
                except Exception as exc:
                    self.stderr.write(
                        self.style.ERROR(f"ChromaDB upsert failed for batch: {exc}")
                    )
                    error_count += len(docs_batch)
                    docs_batch = []
                    continue

                # Update vector_id on the Django side and print progress
                for j, d in enumerate(docs_batch):
                    d.vector_id = chroma_ids[j]
                    indexed_count += 1
                    self.stdout.write(
                        f"  [{indexed_count}/{total}] Indexed {d.doc_type}: {d.title}"
                    )

                # Bulk update vector_id to avoid N+1 saves
                try:
                    LegalDocument.objects.bulk_update(docs_batch, ["vector_id"])
                except Exception as exc:
                    logger.warning("bulk_update vector_id failed: %s", exc)
                    # Fallback: individual saves
                    for d in docs_batch:
                        try:
                            d.save(update_fields=["vector_id"])
                        except Exception:
                            pass

                docs_batch = []

        # ── Summary ──────────────────────────────────────────────────────────
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(
            self.style.SUCCESS(f"  Successfully indexed {indexed_count} document(s).")
        )
        if error_count:
            self.stdout.write(
                self.style.WARNING(f"  {error_count} document(s) failed — check logs.")
            )
        self.stdout.write(
            self.style.SUCCESS(
                f"  ChromaDB collection '{COLLECTION_NAME}' total: {collection.count()} vectors."
            )
        )
        self.stdout.write(self.style.SUCCESS("=" * 60))

