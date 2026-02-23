"""
Ingest: list files in downloads/<notice_id>/, parse, chunk, embed, upsert to Pinecone.
"""

import os
from pathlib import Path

from rag.parsers import parse_file
from rag.chunker import chunk_text

# Resolve downloads dir from project root so it works from any cwd
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
DOWNLOAD_DIR = _PROJECT_ROOT / "downloads"
SUPPORTED_EXT = (".pdf", ".xlsx", ".txt")

INCLUDE_KEYWORDS = ["scope", "requirement", "specification", "solicitation", "terms", "condition", "work", "technical", "statement", "criteria", "evaluation"]
EXCLUDE_KEYWORDS = ["questionnaire", "form", "template", "blank", "example", "sample"]


def _should_include_file(filename: str) -> bool:
    name_lower = filename.lower()
    for exclude in EXCLUDE_KEYWORDS:
        if exclude in name_lower:
            return False
    for include in INCLUDE_KEYWORDS:
        if include in name_lower:
            return True
    return True

def run_ingest(
    notice_id: str,
    chunk_size: int = 500,
    overlap: int = 50,
):
    """
    For the given notice_id, read all supported files under downloads/<notice_id>/,
    chunk them, and upsert to the vector store. Returns number of chunks upserted.
    """
    dir_path = DOWNLOAD_DIR / notice_id
    if not dir_path.is_dir():
        raise FileNotFoundError(f"Directory not found: {dir_path} (run from project root or ensure draft-proposal downloaded files first)")

    store = _get_store()
    docs = []

    for name in sorted(os.listdir(dir_path)):
        if (os.path.splitext(name)[1] or "").lower() not in SUPPORTED_EXT:
            continue
        if not _should_include_file(name):
            continue
        path = dir_path / name
        if not path.is_file():
            continue
        try:
            text = parse_file(str(path))
        except Exception as e:
            raise RuntimeError(f"Parse failed for {path}: {e}") from e
        chunks = chunk_text(
            text,
            metadata={"noticeId": notice_id, "filename": name},
            chunk_size=chunk_size,
            overlap=overlap,
        )
        for c in chunks:
            meta = c["metadata"]
            safe_name = name.replace(" ", "_")[:80]
            chunk_id = f"{notice_id}_{safe_name}_{meta['chunk_index']}"
            # Pinecone metadata: string values only (include text for RAG retrieval)
            doc_meta = {
                "noticeId": str(notice_id),
                "filename": str(name),
                "chunk_index": str(meta["chunk_index"]),
                "text": c["text"][:40000],  # Pinecone metadata limit; keep full chunk
            }
            docs.append({"id": chunk_id, "text": c["text"], "meta": doc_meta})

    if not docs:
        return 0
    store.upsert_documents(docs)
    return len(docs)


def _get_store():
    from vector_db.pinecone_gemini import GeminiPineconeVectorStore
    return GeminiPineconeVectorStore()
