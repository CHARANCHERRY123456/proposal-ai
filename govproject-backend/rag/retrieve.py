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
    store = _get_store()
    result = store.query(query_text, top_k=top_k * 2)
    matches = result.get("matches") or []
    out = []
    for m in matches:
        meta = m.get("metadata") or {}
        if notice_id and meta.get("noticeId") != notice_id:
            continue
        chunk_id = m.get("id") or meta.get("chunk_id")
        if not chunk_id:
            continue
        
        from db import db
        chunk_doc = await db.chunks.find_one({"chunk_id": chunk_id, "is_latest_version": True})
        if not chunk_doc:
            continue
        
        out.append({
            "id": chunk_id,
            "score": m.get("score"),
            "text": chunk_doc.get("text", ""),
            "metadata": meta,
        })
        if len(out) >= top_k:
            break
    return out


def _get_store():
    from vector_db.pinecone_gemini import GeminiPineconeVectorStore
    return GeminiPineconeVectorStore()
