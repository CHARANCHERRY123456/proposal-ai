"""
Ingest: list files in downloads/<notice_id>/, parse, chunk, embed, upsert to Pinecone.
"""

import os
from pathlib import Path

from rag.parsers import parse_file
from rag.chunker import chunk_by_structure
from rag.utils import is_table
from db import db

# Resolve downloads dir from project root so it works from any cwd
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
DOWNLOAD_DIR = _PROJECT_ROOT / "downloads"
SUPPORTED_EXT = (".pdf", ".xlsx", ".txt")

# Only exclude these - include everything else
EXCLUDE_KEYWORDS = ["questionnaire", "form", "template", "blank", "example", "sample"]


def _should_include_file(filename: str) -> bool:
    """
    For now, include ALL files except explicit exclusions (questionnaires, forms, templates).
    This ensures we don't miss important documents.
    """
    name_lower = filename.lower()
    # Only exclude if it's clearly a questionnaire/form/template
    for exclude in EXCLUDE_KEYWORDS:
        if exclude in name_lower:
            import logging
            logging.getLogger(__name__).info(f"[INGEST] Excluding file (matches exclude keyword '{exclude}'): {filename}")
            return False
    # Include everything else
    import logging
    logging.getLogger(__name__).info(f"[INGEST] Including file: {filename}")
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
    import logging
    logger = logging.getLogger(__name__)
    
    existing_count = await db.chunks.count_documents({"noticeId": notice_id, "is_latest_version": True})
    logger.info(f"[INGEST] Existing chunks for {notice_id}: {existing_count}")
    if existing_count > 0:
        logger.info(f"[INGEST] Skipping ingestion - chunks already exist. Returning {existing_count}")
        return existing_count
    
    await db.chunks.update_many(
        {"noticeId": notice_id},
        {"$set": {"is_latest_version": False}}
    )
    
    latest_amendment = await db.chunks.find_one(
        {"noticeId": notice_id},
        sort=[("amendment_number", -1)]
    )
    amendment_number = (latest_amendment.get("amendment_number", -1) + 1) if latest_amendment else 0
    logger.info(f"[INGEST] Amendment number: {amendment_number}")
    
    dir_path = DOWNLOAD_DIR / notice_id
    if not dir_path.is_dir():
        logger.warning(f"[INGEST] Directory not found: {dir_path}")
        return 0

    store = _get_store()
    docs = []
    total_chunks_created = 0
    
    all_files = sorted(os.listdir(dir_path))
    logger.info(f"[INGEST] Found {len(all_files)} files in {dir_path}")
    
    for name in all_files:
        ext = (os.path.splitext(name)[1] or "").lower()
        if ext not in SUPPORTED_EXT:
            logger.info(f"[INGEST] Skipping {name} - unsupported extension: {ext}")
            continue
        if not _should_include_file(name):
            continue
        path = dir_path / name
        if not path.is_file():
            logger.warning(f"[INGEST] Skipping {name} - not a file")
            continue
        try:
            logger.info(f"[INGEST] Parsing file: {name}")
            text = parse_file(str(path))
            logger.info(f"[INGEST] Parsed {name}: {len(text)} characters")
        except Exception as e:
            logger.error(f"[INGEST] Parse failed for {path}: {e}", exc_info=True)
            raise RuntimeError(f"Parse failed for {path}: {e}") from e
        
        chunks = chunk_by_structure(
            text,
            metadata={"noticeId": notice_id, "filename": name},
            min_tokens=400,
            max_tokens=600,
        )
        logger.info(f"[INGEST] Created {len(chunks)} chunks from {name}")
        
        for c in chunks:
            meta = c["metadata"]
            safe_name = name.replace(" ", "_")[:80]
            chunk_id = f"{notice_id}_{safe_name}_{meta['chunk_index']}"
            
            is_table_chunk = is_table(c["text"])
            requirement_flag = meta.get("requirement_flag", False)
            
            chunk_doc = {
                "chunk_id": chunk_id,
                "noticeId": notice_id,
                "filename": name,
                "text": c["text"],
                "section_name": meta.get("section_name", ""),
                "section_type": meta.get("section_type", "other"),
                "is_critical": meta.get("is_critical", False),
                "requirement_flag": requirement_flag,
                "is_table": is_table_chunk,
                "chunk_index": meta["chunk_index"],
                "amendment_number": amendment_number,
                "is_latest_version": True,
            }
            
            await db.chunks.replace_one(
                {"chunk_id": chunk_id},
                chunk_doc,
                upsert=True
            )
            
            if not is_table_chunk:
                doc_meta = {
                    "chunk_id": chunk_id,
                    "noticeId": str(notice_id),
                    "filename": str(name),
                    "section_type": meta.get("section_type", "other"),
                    "is_critical": str(meta.get("is_critical", False)),
                    "requirement_flag": str(requirement_flag),
                }
                docs.append({"id": chunk_id, "text": c["text"], "meta": doc_meta})
            total_chunks_created += 1

    logger.info(f"[INGEST] Total chunks created: {total_chunks_created}")
    logger.info(f"[INGEST] Total chunks for Pinecone (non-table): {len(docs)}")
    
    if not docs:
        logger.warning(f"[INGEST] No documents to upsert to Pinecone!")
        return 0
    
    logger.info(f"[INGEST] Upserting {len(docs)} documents to Pinecone...")
    store.upsert_documents(docs)
    logger.info(f"[INGEST] Successfully upserted {len(docs)} documents to Pinecone")
    return len(docs)


def _get_store():
    from vector_db.pinecone_gemini import GeminiPineconeVectorStore
    return GeminiPineconeVectorStore()
