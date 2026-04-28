"""
自动论文检索编排模块

从知识库提取关键词 → 批量搜索 CrossRef → 去重 → 供用户审核。
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent / "data"
SEEN_PAPERS_PATH = DATA_DIR / "seen_papers.json"


# ═══════════════════════════════════════════════════════════════
# 关键词提取
# ═══════════════════════════════════════════════════════════════


def extract_keywords_from_knowledge(
    traits: list,
    correlations: Optional[list] = None,
    constraints: Optional[list] = None,
    max_keywords: int = 10,
) -> list[str]:
    """
    从知识库中提取高频关键词用于论文检索。

    从 trait 的 name、category 和 tags 中提取关键词，
    按类别分组后每类取前几个，保证检索覆盖面。
    """
    keywords: list[str] = []
    seen: set[str] = set()

    # 1. 从性状名称提取（核心词）
    for t in traits:
        name = getattr(t, "name", None) or (isinstance(t, dict) and t.get("name", ""))
        if name and name not in seen:
            seen.add(name)
            # 简短名称直接作为关键词
            if len(name) <= 8:
                keywords.append(name)

    # 2. 按分类分组提取代表性关键词（避免同类重复）
    categories: dict[str, list[str]] = {}
    for t in traits:
        cat = getattr(t, "category", None) or (isinstance(t, dict) and t.get("category", ""))
        name = getattr(t, "name", None) or (isinstance(t, dict) and t.get("name", ""))
        if cat and name:
            categories.setdefault(cat, []).append(name)

    for cat, names in categories.items():
        if cat not in seen:
            seen.add(cat)
            keywords.append(cat)
        # 每类最多补 2 个关键词
        added = 0
        for name in names:
            if added >= 2:
                break
            if name not in seen and len(name) <= 10:
                seen.add(name)
                keywords.append(name)
                added += 1

    # 3. 从 tags 补充
    for t in traits:
        tags = getattr(t, "tags", None) or (isinstance(t, dict) and t.get("tags", []))
        if tags:
            for tag in tags:
                if tag not in seen and len(tag) <= 8:
                    seen.add(tag)
                    keywords.append(tag)

    # 4. 限制数量，优先保留核心性状名称
    if len(keywords) > max_keywords:
        keywords = keywords[:max_keywords]

    logger.info(f"从知识库提取了 {len(keywords)} 个关键词: {keywords}")
    return keywords


# ═══════════════════════════════════════════════════════════════
# 批量搜索
# ═══════════════════════════════════════════════════════════════


def search_all_keywords(
    keywords: list[str],
    rows_per_query: int = 8,
    seen_dois: Optional[set[str]] = None,
) -> list[dict[str, Any]]:
    """
    遍历关键词批量搜索 CrossRef，去重后返回新论文列表。

    参数：
        keywords: 搜索关键词列表
        rows_per_query: 每个关键词返回的最大结果数
        seen_dois: 已见过的 DOI 集合（跳过这些）

    返回：
        去重后的论文元数据列表（按年份降序排列）
    """
    if not keywords:
        logger.warning("关键词列表为空，跳过检索")
        return []

    from bio_logic_debugger.knowledge.doi_fetcher import search_by_keywords as _search

    seen = set(seen_dois or [])
    all_papers: list[dict[str, Any]] = []
    seen_titles: set[str] = set()

    for keyword in keywords:
        try:
            papers = _search([keyword], rows=rows_per_query)
        except Exception as e:
            logger.warning(f"关键词 '{keyword}' 检索失败: {e}")
            continue

        for paper in papers:
            doi = paper.get("doi", "")
            title = paper.get("title", "")

            # 跳过无 DOI 或无标题的论文
            if not doi and not title:
                continue

            # 去重：按 DOI 去重，无 DOI 的按标题去重
            dedup_key = doi if doi else title
            if dedup_key in seen:
                continue

            seen.add(dedup_key)
            seen_titles.add(title)
            all_papers.append(paper)

    if not all_papers:
        logger.info("未找到新论文")
        return []

    # 按年份降序排列
    all_papers.sort(key=lambda p: p.get("year", 0), reverse=True)

    logger.info(f"批量检索到 {len(all_papers)} 篇新论文")
    return all_papers


# ═══════════════════════════════════════════════════════════════
# 已见论文持久化
# ═══════════════════════════════════════════════════════════════


def load_seen_papers() -> set[str]:
    """加载已处理过的论文 DOI 集合"""
    if not SEEN_PAPERS_PATH.exists():
        return set()
    try:
        data = json.loads(SEEN_PAPERS_PATH.read_text(encoding="utf-8"))
        return set(data.get("dois", []))
    except Exception as e:
        logger.warning(f"加载 seen_papers 失败: {e}")
        return set()


def save_seen_papers(dois: set[str]) -> None:
    """持久化已处理过的论文 DOI"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    try:
        SEEN_PAPERS_PATH.write_text(
            json.dumps({"dois": sorted(dois)}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception as e:
        logger.warning(f"保存 seen_papers 失败: {e}")


def mark_papers_seen(papers: list[dict]) -> None:
    """将一批论文的 DOI 标记为已见"""
    existing = load_seen_papers()
    for p in papers:
        doi = p.get("doi", "")
        if doi:
            existing.add(doi)
    save_seen_papers(existing)
