"""
DOI / 论文标题检索模块

通过免费 API（Crossref）搜索论文元数据。
"""
from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

CROSSREF_BASE = "https://api.crossref.org/works"
USER_AGENT = "BioLogicDebugger/1.0 (mailto:user@example.com)"


def _build_headers() -> dict[str, str]:
    return {"User-Agent": USER_AGENT}


def search_by_keywords(
    keywords: list[str],
    rows: int = 8,
) -> list[dict[str, Any]]:
    """按关键词批量搜索论文（使用 query.bibliographic）"""
    try:
        import httpx
    except ImportError:
        raise ImportError("需要安装 httpx: pip install httpx>=0.25.0")

    query = " ".join(keywords)
    params = {
        "query.bibliographic": query,
        "rows": min(rows, 20),
    }
    try:
        resp = httpx.get(
            CROSSREF_BASE,
            params=params,
            headers=_build_headers(),
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        items = data.get("message", {}).get("items", [])
        return [_parse_crossref_item(item) for item in items]
    except Exception as e:
        logger.warning(f"CrossRef 关键词检索失败: {e}")
        return []


def search_by_title(title: str) -> Optional[dict[str, Any]]:
    """按论文标题搜索，返回第一条匹配的元数据"""
    try:
        import httpx
    except ImportError:
        raise ImportError("需要安装 httpx: pip install httpx>=0.25.0")

    params = {
        "query.title": title,
        "rows": 5,
    }
    try:
        resp = httpx.get(
            CROSSREF_BASE,
            params=params,
            headers=_build_headers(),
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        items = data.get("message", {}).get("items", [])
        if not items:
            return None

        # 取标题最匹配的第一条
        best = items[0]
        return _parse_crossref_item(best)

    except Exception as e:
        logger.warning(f"CrossRef 检索失败: {e}")
        return None


def fetch_by_doi(doi: str) -> Optional[dict[str, Any]]:
    """按 DOI 获取论文元数据"""
    try:
        import httpx
    except ImportError:
        raise ImportError("需要安装 httpx: pip install httpx>=0.25.0")

    url = f"{CROSSREF_BASE}/{doi}"
    try:
        resp = httpx.get(url, headers=_build_headers(), timeout=15)
        resp.raise_for_status()
        data = resp.json()
        item = data.get("message", {})
        return _parse_crossref_item(item)

    except Exception as e:
        logger.warning(f"DOI 获取失败 ({doi}): {e}")
        return None


def _parse_crossref_item(item: dict) -> dict[str, Any]:
    """将 CrossRef API 返回的数据统一为内部格式"""
    title_list = item.get("title", [])
    title = title_list[0] if title_list else "未知标题"

    authors = []
    for author in item.get("author", []):
        given = author.get("given", "")
        family = author.get("family", "")
        name = f"{given} {family}".strip()
        if name:
            authors.append(name)

    doi = item.get("DOI", "")
    journal = ""
    if item.get("container-title"):
        journal = item["container-title"][0]

    year = 0
    if item.get("published-print", {}).get("date-parts"):
        year = item["published-print"]["date-parts"][0][0]
    elif item.get("published-online", {}).get("date-parts"):
        year = item["published-online"]["date-parts"][0][0]
    elif item.get("created", {}).get("date-parts"):
        year = item["created"]["date-parts"][0][0]

    abstract = item.get("abstract", "")

    return {
        "title": title,
        "authors": authors,
        "doi": doi,
        "journal": journal,
        "year": year,
        "abstract": abstract,
    }
