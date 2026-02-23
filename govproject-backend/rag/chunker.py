from rag.utils import count_tokens, is_heading, classify_section, has_requirement_keywords

def chunk_by_structure(
    text: str,
    metadata: dict | None = None,
    min_tokens: int = 400,
    max_tokens: int = 600,
) -> list[dict]:
    if not text:
        return []
    
    meta = dict(metadata) if metadata else {}
    chunks = []
    lines = text.split("\n")
    
    current_section = {"heading": "", "content": [], "section_type": "other", "is_critical": False}
    index = 0
    
    for line in lines:
        if is_heading(line):
            if current_section["content"]:
                section_text = "\n".join(current_section["content"]).strip()
                if section_text:
                    section_chunks = _split_section(section_text, current_section, meta, index, min_tokens, max_tokens)
                    chunks.extend(section_chunks)
                    index += len(section_chunks)
            
            section_type, is_critical = classify_section(line)
            current_section = {
                "heading": line,
                "content": [],
                "section_type": section_type,
                "is_critical": is_critical
            }
        else:
            current_section["content"].append(line)
    
    if current_section["content"]:
        section_text = "\n".join(current_section["content"]).strip()
        if section_text:
            section_chunks = _split_section(section_text, current_section, meta, index, min_tokens, max_tokens)
            chunks.extend(section_chunks)
    
    if not chunks and text:
        chunks = _semantic_fallback(text, meta, min_tokens, max_tokens)
    
    return chunks

def _semantic_fallback(text: str, base_meta: dict, min_tokens: int, max_tokens: int) -> list[dict]:
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        return []
    
    chunks = []
    current_chunk = []
    current_tokens = 0
    index = 0
    
    for para in paragraphs:
        para_tokens = count_tokens(para)
        
        if current_tokens + para_tokens > max_tokens and current_chunk:
            chunk_text = "\n\n".join(current_chunk)
            requirement_flag = has_requirement_keywords(chunk_text)
            chunks.append({
                "text": chunk_text,
                "metadata": {
                    **base_meta,
                    "chunk_index": index,
                    "section_name": "",
                    "section_type": "other",
                    "is_critical": False,
                    "requirement_flag": requirement_flag
                }
            })
            index += 1
            current_chunk = [para]
            current_tokens = para_tokens
        else:
            current_chunk.append(para)
            current_tokens += para_tokens
    
    if current_chunk:
        chunk_text = "\n\n".join(current_chunk)
        requirement_flag = has_requirement_keywords(chunk_text)
        chunks.append({
            "text": chunk_text,
            "metadata": {
                **base_meta,
                "chunk_index": index,
                "section_name": "",
                "section_type": "other",
                "is_critical": False,
                "requirement_flag": requirement_flag
            }
        })
    
    return chunks

def _split_section(text: str, section_info: dict, base_meta: dict, start_index: int, min_tokens: int, max_tokens: int) -> list[dict]:
    tokens = count_tokens(text)
    
    requirement_flag = has_requirement_keywords(text)
    
    if tokens <= max_tokens:
        return [{
            "text": text,
            "metadata": {
                **base_meta,
                "chunk_index": start_index,
                "section_name": section_info["heading"],
                "section_type": section_info["section_type"],
                "is_critical": section_info["is_critical"],
                "requirement_flag": requirement_flag
            }
        }]
    
    chunks = []
    paragraphs = text.split("\n\n")
    current_chunk = []
    current_tokens = 0
    chunk_index = start_index
    
    for para in paragraphs:
        para_tokens = count_tokens(para)
        
        if current_tokens + para_tokens > max_tokens and current_chunk:
            chunk_text = "\n\n".join(current_chunk)
            requirement_flag = has_requirement_keywords(chunk_text)
            chunks.append({
                "text": chunk_text,
                "metadata": {
                    **base_meta,
                    "chunk_index": chunk_index,
                    "section_name": section_info["heading"],
                    "section_type": section_info["section_type"],
                    "is_critical": section_info["is_critical"],
                    "requirement_flag": requirement_flag
                }
            })
            chunk_index += 1
            current_chunk = [para]
            current_tokens = para_tokens
        else:
            current_chunk.append(para)
            current_tokens += para_tokens
    
    if current_chunk:
        chunk_text = "\n\n".join(current_chunk)
        requirement_flag = has_requirement_keywords(chunk_text)
        chunks.append({
            "text": chunk_text,
            "metadata": {
                **base_meta,
                "chunk_index": chunk_index,
                "section_name": section_info["heading"],
                "section_type": section_info["section_type"],
                "is_critical": section_info["is_critical"],
                "requirement_flag": requirement_flag
            }
        })
    
    return chunks

def chunk_text(
    text: str,
    metadata: dict | None = None,
    chunk_size: int = 500,
    overlap: int = 50,
) -> list[dict]:
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
