def count_tokens(text: str) -> int:
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except ImportError:
        return int(len(text.split()) * 1.3)

def is_heading(line: str) -> bool:
    line = line.strip()
    if not line or len(line) > 100:
        return False
    if line.isupper() and len(line) > 5:
        return True
    if any(line.startswith(prefix) for prefix in ["SECTION", "Section", "PART", "Part", "CHAPTER", "Chapter"]):
        return True
    if line.endswith(":") and len(line.split()) <= 10:
        return True
    return False

def classify_section(heading: str) -> tuple[str, bool]:
    heading_lower = heading.lower()
    if any(kw in heading_lower for kw in ["requirement", "shall", "must"]):
        return "requirement", True
    if any(kw in heading_lower for kw in ["specification", "spec", "technical spec"]):
        return "specification", True
    if any(kw in heading_lower for kw in ["condition", "terms", "clause"]):
        return "condition", True
    if any(kw in heading_lower for kw in ["evaluation", "criteria", "scoring"]):
        return "evaluation_criteria", True
    if any(kw in heading_lower for kw in ["scope", "statement of work", "sow"]):
        return "scope_of_work", True
    return "other", False

def has_requirement_keywords(text: str) -> bool:
    keywords = ["shall", "must", "required", "requirement", "mandatory"]
    text_lower = text.lower()
    return any(kw in text_lower for kw in keywords)

def is_table(text: str) -> bool:
    lines = text.strip().split("\n")
    if len(lines) < 3:
        return False
    if "|" in text or "\t" in text:
        return True
    if any("pricing" in line.lower() or "clin" in line.lower() or "line item" in line.lower() for line in lines[:5]):
        return True
    return False
