"""
Ingest: list files in downloads/<notice_id>/, parse, chunk, embed, upsert to Pinecone.
"""

import os
from pathlib import Path

from rag.parsers import parse_file
from rag.chunker import chunk_by_structure
from db import db

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

async def run_ingest(
    notice_id: str,
    chunk_size: int = 500,
    overlap: int = 50,
):
    """
    For the given notice_id, read all supported files under downloads/<notice_id>/,
    chunk them, and upsert to the vector store. Returns number of chunks upserted.
    Skips if chunks already exist for this notice_id.
    """
    existing_count = await db.chunks.count_documents({"noticeId": notice_id})
    if existing_count > 0:
        return existing_count
    
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
        
        chunks = chunk_by_structure(
            text,
            metadata={"noticeId": notice_id, "filename": name},
            min_tokens=400,
            max_tokens=600,
        )
        
        for c in chunks:
            meta = c["metadata"]
            safe_name = name.replace(" ", "_")[:80]
            chunk_id = f"{notice_id}_{safe_name}_{meta['chunk_index']}"
            
            chunk_doc = {
                "chunk_id": chunk_id,
                "noticeId": notice_id,
                "filename": name,
                "text": c["text"],
                "section_name": meta.get("section_name", ""),
                "section_type": meta.get("section_type", "other"),
                "is_critical": meta.get("is_critical", False),
                "chunk_index": meta["chunk_index"],
            }
            
            await db.chunks.replace_one(
                {"chunk_id": chunk_id},
                chunk_doc,
                upsert=True
            )
            
            doc_meta = {
                "chunk_id": chunk_id,
                "noticeId": str(notice_id),
                "filename": str(name),
                "section_type": meta.get("section_type", "other"),
                "is_critical": str(meta.get("is_critical", False)),
            }
            docs.append({"id": chunk_id, "text": c["text"], "meta": doc_meta})

    if not docs:
        return 0
    store.upsert_documents(docs)
    return len(docs)


def _get_store():
    from vector_db.pinecone_gemini import GeminiPineconeVectorStore
    return GeminiPineconeVectorStore()
