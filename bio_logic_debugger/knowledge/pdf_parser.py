"""
PDF 文本提取模块

支持从 PDF 文件中提取纯文本内容，用于后续的文献分析。
"""
from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def extract_text(pdf_bytes: bytes, max_chars: int = 50000) -> str:
    """从 PDF 字节数据中提取文本"""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        raise ImportError("需要安装 PyMuPDF: pip install PyMuPDF>=1.23.0")

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages_text = []
    total = 0
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        text = page.get_text()
        pages_text.append(text)
        total += len(text)
        if total >= max_chars:
            logger.info(f"达到最大字符限制 {max_chars}，停止提取")
            break

    doc.close()
    return "\n".join(pages_text)


def extract_text_from_path(path: str, max_chars: int = 50000) -> str:
    """从文件路径提取 PDF 文本"""
    try:
        import fitz
    except ImportError:
        raise ImportError("需要安装 PyMuPDF: pip install PyMuPDF>=1.23.0")

    doc = fitz.open(path)
    pages_text = []
    total = 0
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        text = page.get_text()
        pages_text.append(text)
        total += len(text)
        if total >= max_chars:
            break

    doc.close()
    return "\n".join(pages_text)
