"""
自动论文检索编排模块

从知识库提取关键词 → 批量搜索 CrossRef → 去重 → 供用户审核。
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Optional

from bio_logic_debugger.paths import user_data_dir

logger = logging.getLogger(__name__)


def _seen_papers_path() -> Path:
    return user_data_dir() / "seen_papers.json"


# ═══════════════════════════════════════════════════════════════
# 关键词提取
# ═══════════════════════════════════════════════════════════════


# CrossRef 是英文索引，不要把中文性状名直接丢进去。
TRAIT_SEARCH_EN = {
    "rice_yield_per_plant": "rice yield per plant",
    "rice_yield_per_mu": "rice grain yield",
    "rice_chalkiness": "rice chalkiness",
    "rice_heading_days": "rice heading date",
    "rice_amylose_content": "rice amylose content",
    "rice_gel_consistency": "rice gel consistency",
    "rice_head_rice_recovery": "head rice recovery",
    "rice_plant_height": "rice plant height",
    "rice_lodging_resistance": "rice lodging resistance",
    "rice_harvest_index": "rice harvest index",
    "rice_grain_length": "rice grain length",
    "rice_drought_tolerance": "rice drought tolerance",
    "rice_blast_resistance": "rice blast resistance",
}


def extract_keywords_from_knowledge(
    traits: list,
    correlations: Optional[list] = None,
    constraints: Optional[list] = None,
    max_keywords: int = 10,
) -> list[str]:
    """从性状 id 映射英文检索词；没有映射的跳过中文短名。"""
    keywords: list[str] = []
    seen: set[str] = set()

    def add(term: str) -> None:
        term = (term or "").strip()
        if not term or term in seen:
            return
        if any("\u4e00" <= ch <= "\u9fff" for ch in term):
            return
        seen.add(term)
        keywords.append(term)

    for t in traits:
        tid = getattr(t, "id", None) or (isinstance(t, dict) and t.get("id")) or ""
        add(TRAIT_SEARCH_EN.get(str(tid), ""))

    add("rice breeding")
    add("Oryza sativa")
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
    path = _seen_papers_path()
    if not path.exists():
        return set()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return set(data.get("dois", []))
    except Exception as e:
        logger.warning(f"加载 seen_papers 失败: {e}")
        return set()


def save_seen_papers(dois: set[str]) -> None:
    """持久化已处理过的论文 DOI"""
    path = _seen_papers_path()
    try:
        path.write_text(
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
