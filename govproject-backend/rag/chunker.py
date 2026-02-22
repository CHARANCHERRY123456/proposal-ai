"""
Chunk long text into overlapping segments. Input: text + optional metadata. Output: list of {text, metadata}.
"""


def chunk_text(
    text: str,
    metadata: dict | None = None,
    chunk_size: int = 500,
    overlap: int = 50,
) -> list[dict]:
    """
    Split text into chunks of chunk_size chars with overlap chars between chunks.
    Each item is {"text": str, "metadata": dict} (metadata includes chunk_index and any passed-in metadata).
    """
    if not text or chunk_size <= 0:
        return []
    if overlap >= chunk_size:
        overlap = chunk_size - 1
    meta = dict(metadata) if metadata else {}
    chunks = []
    start = 0
    index = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        if chunk.strip():
            m = {**meta, "chunk_index": index}
            chunks.append({"text": chunk, "metadata": m})
            index += 1
        start = end - overlap
    return chunks
