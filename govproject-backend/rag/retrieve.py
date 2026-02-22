"""
Retrieval: query vector store, return top-k chunks with text for RAG context.
"""


def retrieve(query_text: str, top_k: int = 5, notice_id: str | None = None) -> list[dict]:
    """
    Search Pinecone for chunks matching query_text. Returns list of
    {"id", "score", "text", "metadata"} for use as RAG context.
    If notice_id is set, filter to that opportunity only.
    """
    store = _get_store()
    result = store.query(query_text, top_k=top_k)
    matches = result.get("matches") or []
    out = []
    for m in matches:
        meta = m.get("metadata") or {}
        if notice_id and meta.get("noticeId") != notice_id:
            continue
        out.append({
            "id": m.get("id"),
            "score": m.get("score"),
            "text": meta.get("text", ""),
            "metadata": meta,
        })
    return out


def _get_store():
    from vector_db.pinecone_gemini import GeminiPineconeVectorStore
    return GeminiPineconeVectorStore()
