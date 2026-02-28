from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Tuple

from docx import Document

SUPPORTED_EXCEL_EXTS = {".xlsx", ".xls"}
SUPPORTED_TEXT_EXTS = {".txt"}
SUPPORTED_DOCX_EXTS = {".docx"}


def _normalize_uploaded_files(uploaded) -> List[str]:
    if not uploaded:
        return []
    if isinstance(uploaded, (list, tuple)):
        items = uploaded
    else:
        items = [uploaded]

    paths: List[str] = []
    for item in items:
        if not item:
            continue
        if isinstance(item, str):
            paths.append(item)
            continue
        if isinstance(item, dict):
            name = item.get("name") or item.get("path") or item.get("orig_name")
            if name:
                paths.append(str(name))
                continue
        if hasattr(item, "name"):
            paths.append(str(item.name))
    return paths


def _read_txt(path: str) -> str:
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read().strip()


def _read_docx(path: str) -> str:
    document = Document(path)
    lines = [p.text.strip() for p in document.paragraphs if p.text and p.text.strip()]
    return "\n".join(lines).strip()


def parse_uploads(uploaded) -> Tuple[Optional[str], str]:
    excel_path: Optional[str] = None
    context_parts: List[str] = []

    for path in _normalize_uploaded_files(uploaded):
        ext = Path(path).suffix.lower()
        if ext in SUPPORTED_EXCEL_EXTS and not excel_path:
            excel_path = path
            continue
        if ext in SUPPORTED_TEXT_EXTS:
            content = _read_txt(path)
            if content:
                context_parts.append(content)
            continue
        if ext in SUPPORTED_DOCX_EXTS:
            content = _read_docx(path)
            if content:
                context_parts.append(content)

    context_text = "\n\n".join(context_parts).strip()
    return excel_path, context_text


def build_raw_file_context_section(context_text: str, limit_chars: int) -> str:
    """构建用于注入 LLM 的「原始文件信息」上下文段。

    规则：
    - 文档原文长度 <= limit_chars：直接注入原始段落。
    - 文档原文长度 > limit_chars：该段落置空。
    """
    content = (context_text or "").strip()
    if not content or limit_chars <= 0 or len(content) > limit_chars:
        return ""
    return content
