"""
Retrieval: query vector store, return top-k chunks with text for RAG context.
"""


async def retrieve(query_text: str, top_k: int = 5, notice_id: str | None = None) -> list[dict]:
    """
    Search Pinecone for chunks matching query_text. Returns list of
    {"id", "score", "text", "metadata"} for use as RAG context.
    If notice_id is set, filter to that opportunity only.
    Only returns latest version chunks.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    store = _get_store()
    result = store.query(query_text, top_k=top_k * 2)
    matches = result.get("matches") or []
    logger.info(f"[CITATIONS] Retrieved {len(matches)} matches from Pinecone for query: {query_text[:50]}")
    
    out = []
    for m in matches:
        meta = m.get("metadata") or {}
        if notice_id and meta.get("noticeId") != notice_id:
            continue
        chunk_id = m.get("id") or meta.get("chunk_id")
        if not chunk_id:
            logger.warning(f"[CITATIONS] No chunk_id found in match: {m.get('id')}")
            continue
        
        from db import db
        chunk_doc = await db.chunks.find_one({"chunk_id": chunk_id, "is_latest_version": True})
        if not chunk_doc:
            logger.warning(f"[CITATIONS] Chunk not found in MongoDB: {chunk_id}")
            continue
        
        citation_meta = {
            **meta,
            "section_name": chunk_doc.get("section_name", ""),
            "section_type": chunk_doc.get("section_type", "other"),
            "requirement_flag": chunk_doc.get("requirement_flag", False),
            "is_critical": chunk_doc.get("is_critical", False),
            "chunk_index": chunk_doc.get("chunk_index", 0),
        }
        
        logger.info(f"[CITATIONS] Chunk {chunk_id}: filename={chunk_doc.get('filename')}, section={chunk_doc.get('section_name')}, type={chunk_doc.get('section_type')}, requirement={chunk_doc.get('requirement_flag')}")
        
        out.append({
            "id": chunk_id,
            "score": m.get("score"),
            "text": chunk_doc.get("text", ""),
            "metadata": citation_meta,
        })
        if len(out) >= top_k:
            break
    
    logger.info(f"[CITATIONS] Returning {len(out)} chunks with citation metadata")
    return out


def _get_store():
    from vector_db.pinecone_gemini import GeminiPineconeVectorStore
    return GeminiPineconeVectorStore()
