"""
Parse downloaded files to plain text. One entry: parse_file(path) -> str.
"""

import os


def parse_file(path: str) -> str:
    """
    Return full text of the file. Supports .pdf, .xlsx, .txt.
    Raises ValueError for unsupported type or read error.
    """
    path = os.path.normpath(path)
    if not os.path.isfile(path):
        raise ValueError(f"Not a file: {path}")
    ext = (os.path.splitext(path)[1] or "").lower()
    if ext == ".pdf":
        return _parse_pdf(path)
    if ext == ".xlsx":
        return _parse_xlsx(path)
    if ext == ".txt":
        return _parse_txt(path)
    raise ValueError(f"Unsupported type: {ext}")


def _parse_txt(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def _parse_pdf(path: str) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        raise ValueError("PDF support requires: pip install pypdf")
    reader = PdfReader(path)
    parts = []
    for page in reader.pages:
        t = page.extract_text()
        if t:
            parts.append(t)
    return "\n".join(parts)


def _parse_xlsx(path: str) -> str:
    try:
        import openpyxl
    except ImportError:
        raise ValueError("XLSX support requires: pip install openpyxl")
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    parts = []
    for sheet in wb.worksheets:
        for row in sheet.iter_rows(values_only=True):
            line = " ".join(str(c) if c is not None else "" for c in row).strip()
            if line:
                parts.append(line)
    wb.close()
    return "\n".join(parts)
