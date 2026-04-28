"""
论文分析编排器

协调 LLM 提取和规则提取，从论文文本中提取：
- 性状（Trait）
- 性状关联（TraitCorrelation）
- 约束规则（BiologicalConstraint）

支持 LLM + 规则双引擎，结果合并去重。
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# 提取结果数据模型
# ═══════════════════════════════════════════════════════════════


@dataclass
class ExtractedItem:
    """一条提取结果"""
    item_type: str                     # "trait" / "correlation" / "constraint"
    data: dict                         # 对应的数据字段
    confidence: float = 0.5            # 置信度 0-1
    source_sentence: str = ""          # 原文证据
    selected: bool = True              # 用户是否勾选

    def __hash__(self):
        return hash((self.item_type, json.dumps(self.data, sort_keys=True, ensure_ascii=False)))


# ═══════════════════════════════════════════════════════════════
# LLM 提取提示词
# ═══════════════════════════════════════════════════════════════

EXTRACT_SYSTEM_PROMPT = """你是一位作物育种知识提取专家。从以下论文片段中提取所有与育种相关的信息。

请严格按照 JSON 格式输出，只输出 JSON，不要其他内容。

提取三类信息：

1. traits（性状）：有数值范围、测量单位、分类归属的可测量生物学性状
   格式：{"name": "性状名称", "range": [最小值, 最大值], "unit": "单位", "category": "分类"}

2. correlations（关联）：两个性状之间的相关性描述
   格式：{"trait_a": "性状A", "trait_b": "性状B", "type": "positive/negative/trade_off/curvilinear", "strength": 相关系数, "mechanism": "生理机制描述"}

3. constraints（约束）：生理极限或不可兼得的规则
   格式：{"name": "约束名称", "description": "约束描述", "severity": "FATAL/SEVERE/WARNING/INFO", "condition": "条件表达式"}

注意：
- 只提取论文中明确提到的信息，不要臆造
- name 等中文名称使用论文中的原文术语
- 数值范围用论文中的原文数据
- 如果没有相关信息，对应字段返回空列表 []"""


def _build_extract_prompt(text: str) -> str:
    """构建知识提取提示词"""
    # 取文本前 8000 字符（LLM 上下文限制）
    truncated = text[:8000]
    return f"""论文片段：
{truncated}

请提取其中的育种相关知识，以 JSON 格式输出：
{{
  "traits": [{{"name": "...", "range": [min, max], "unit": "...", "category": "..."}}],
  "correlations": [{{"trait_a": "...", "trait_b": "...", "type": "positive/negative/trade_off", "strength": 0.0, "mechanism": "..."}}],
  "constraints": [{{"name": "...", "description": "...", "severity": "FATAL/SEVERE/WARNING", "condition": "..."}}]
}}"""


# ═══════════════════════════════════════════════════════════════
# 规则提取（正则匹配）
# ═══════════════════════════════════════════════════════════════

# 匹配 XX~XX 单位 的数值范围模式
PATTERN_RANGE = re.compile(
    r'(\d+\.?\d*)\s*[~\-–—到至]\s*(\d+\.?\d*)\s*(g|kg|cm|mm|m|%|天|d|级|粒|穗|个|株|ml|L|mg|μg)'
)

# 匹配相关性描述：A与B呈正/负相关
PATTERN_CORR_POS = re.compile(
    r'([^，。\s]{2,8})(?:与|和)([^，。\s]{2,8})(?:呈|存在|表现为|有)(?:极显著|显著|明显)?正相关'
)
PATTERN_CORR_NEG = re.compile(
    r'([^，。\s]{2,8})(?:与|和)([^，。\s]{2,8})(?:呈|存在|表现为|有)(?:极显著|显著|明显)?负相关'
)
PATTERN_CORR_TRADE = re.compile(
    r'([^，。\s]{2,8})(?:与|和)([^，。\s]{2,8})(?:存在|呈|有)(?:权衡|不可兼得|此消彼长)'
)

# 匹配约束关键词
PATTERN_CONSTRAINT = re.compile(
    r'(不能[^，。]*|无法[^，。]*|不可能[^，。]*|不得超过[^，。]*|不得低于[^，。]*|极限[^，。]{0,20}|上限[^，。]{0,20}|下限[^，。]{0,20})'
)

# 匹配可能的性状名称（上下文中有"性状"、"含量"、"长度"、"宽度"等关键词）
PATTERN_TRAIT_NAME = re.compile(
    r'([^，。\s]{2,10}(?:性状|含量|长度|宽度|高度|数|量|率|性|期|重|积|比|指数|值|度))'
)


def _rule_extract(text: str) -> list[ExtractedItem]:
    """基于正则表达式的规则提取"""
    items: list[ExtractedItem] = []
    seen_sentences: set[str] = set()

    def _add(item: ExtractedItem):
        s = item.source_sentence.strip()[:80]
        if s and s not in seen_sentences:
            seen_sentences.add(s)
            items.append(item)

    # 1. 提取数值范围 → 推测性状
    for match in PATTERN_RANGE.finditer(text):
        lo, hi, unit = match.groups()
        _add(ExtractedItem(
            item_type="trait",
            data={
                "name": f"未知性状（{unit}）",
                "range": [float(lo), float(hi)],
                "unit": unit,
                "category": "未知",
            },
            confidence=0.3,
            source_sentence=match.group(0),
        ))

    # 2. 提取正相关
    for match in PATTERN_CORR_POS.finditer(text):
        _add(ExtractedItem(
            item_type="correlation",
            data={
                "trait_a": match.group(1),
                "trait_b": match.group(2),
                "type": "positive",
                "strength": 0.5,
                "mechanism": "",
            },
            confidence=0.4,
            source_sentence=match.group(0),
        ))

    # 3. 提取负相关
    for match in PATTERN_CORR_NEG.finditer(text):
        _add(ExtractedItem(
            item_type="correlation",
            data={
                "trait_a": match.group(1),
                "trait_b": match.group(2),
                "type": "negative",
                "strength": -0.4,
                "mechanism": "",
            },
            confidence=0.4,
            source_sentence=match.group(0),
        ))

    # 4. 提取权衡关系
    for match in PATTERN_CORR_TRADE.finditer(text):
        _add(ExtractedItem(
            item_type="correlation",
            data={
                "trait_a": match.group(1),
                "trait_b": match.group(2),
                "type": "trade_off",
                "strength": -0.3,
                "mechanism": "",
            },
            confidence=0.35,
            source_sentence=match.group(0),
        ))

    # 5. 提取约束描述
    for match in PATTERN_CONSTRAINT.finditer(text):
        _add(ExtractedItem(
            item_type="constraint",
            data={
                "name": match.group(0)[:30],
                "description": match.group(0),
                "severity": "WARNING",
                "condition": "",
            },
            confidence=0.25,
            source_sentence=match.group(0),
        ))

    return items


def _llm_extract(text: str, llm_caller: Callable) -> list[ExtractedItem]:
    """调用 LLM 提取知识"""
    if not llm_caller:
        return []

    try:
        result_text = llm_caller(text, _build_extract_prompt(text))
    except Exception as e:
        logger.warning(f"LLM 提取失败: {e}")
        return []

    # 解析 JSON 结果
    try:
        # 清理可能存在的 markdown 代码块标记
        cleaned = result_text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()

        data = json.loads(cleaned)
    except (json.JSONDecodeError, Exception) as e:
        logger.warning(f"LLM 返回无法解析的 JSON: {e}")
        return []

    items: list[ExtractedItem] = []

    for t in data.get("traits", []):
        r = t.get("range", [None, None])
        items.append(ExtractedItem(
            item_type="trait",
            data={
                "name": t.get("name", "未知"),
                "range": r,
                "unit": t.get("unit", ""),
                "category": t.get("category", "未知"),
            },
            confidence=0.7,
            source_sentence=json.dumps(t, ensure_ascii=False),
        ))

    for c in data.get("correlations", []):
        items.append(ExtractedItem(
            item_type="correlation",
            data={
                "trait_a": c.get("trait_a", ""),
                "trait_b": c.get("trait_b", ""),
                "type": c.get("type", "positive"),
                "strength": c.get("strength", 0.0),
                "mechanism": c.get("mechanism", ""),
            },
            confidence=0.7,
            source_sentence=json.dumps(c, ensure_ascii=False),
        ))

    for c in data.get("constraints", []):
        items.append(ExtractedItem(
            item_type="constraint",
            data={
                "name": c.get("name", "未知约束"),
                "description": c.get("description", ""),
                "severity": c.get("severity", "WARNING"),
                "condition": c.get("condition", ""),
            },
            confidence=0.65,
            source_sentence=json.dumps(c, ensure_ascii=False),
        ))

    return items


def _merge_results(
    rule_items: list[ExtractedItem],
    llm_items: list[ExtractedItem],
) -> list[ExtractedItem]:
    """合并规则提取和 LLM 提取的结果，去重"""
    seen: set[ExtractedItem] = set()
    merged: list[ExtractedItem] = []

    # LLM 结果优先（高置信度）
    for item in llm_items:
        if item not in seen:
            seen.add(item)
            merged.append(item)

    # 补充规则结果（不在 LLM 结果中的）
    for item in rule_items:
        if item not in seen:
            seen.add(item)
            merged.append(item)

    return merged


# ═══════════════════════════════════════════════════════════════
# 公开 API
# ═══════════════════════════════════════════════════════════════


def analyze_text(
    text: str,
    llm_caller: Optional[Callable] = None,
) -> list[ExtractedItem]:
    """
    分析论文文本，提取育种相关知识。

    参数：
        text: 论文文本
        llm_caller: 可选，LLM 调用函数，签名 fn(system_prompt, user_prompt) -> str

    返回：
        提取结果列表（已去重合并）
    """
    rule_results = _rule_extract(text)
    logger.info(f"规则提取到 {len(rule_results)} 条")

    if llm_caller:
        llm_results = _llm_extract(text, llm_caller)
        logger.info(f"LLM 提取到 {len(llm_results)} 条")
    else:
        llm_results = []

    merged = _merge_results(rule_results, llm_results)
    logger.info(f"合并后共 {len(merged)} 条")

    return merged


def items_to_traits(items: list[ExtractedItem]) -> list[dict]:
    """将提取项中的性状转换为 knowledge_store 可用的 dict"""
    results = []
    seen_names: set[str] = set()
    for item in items:
        if item.item_type != "trait":
            continue
        name = item.data.get("name", "")
        if not name or name in seen_names:
            continue
        seen_names.add(name)
        tid = name_to_id(name)
        r = item.data.get("range", [None, None])
        results.append({
            "id": tid,
            "name": name,
            "description": f"从论文提取：{item.source_sentence[:100]}",
            "category": item.data.get("category", "文献提取"),
            "unit": item.data.get("unit", ""),
            "typical_range": r if isinstance(r, list) else [None, None],
            "tags": ["文献提取"],
            "species": "通用",
        })
    return results


def items_to_correlations(items: list[ExtractedItem]) -> list[dict]:
    """将提取项中的关联转换为 knowledge_store 可用的 dict"""
    results = []
    seen: set[tuple[str, str]] = set()
    for item in items:
        if item.item_type != "correlation":
            continue
        ta = item.data.get("trait_a", "")
        tb = item.data.get("trait_b", "")
        if not ta or not tb:
            continue
        key = (ta, tb)
        if key in seen:
            continue
        seen.add(key)
        corr_type_map = {
            "positive": "POSITIVE",
            "negative": "NEGATIVE",
            "trade_off": "TRADE_OFF",
            "curvilinear": "CURVILINEAR",
        }
        results.append({
            "trait_a": name_to_id(ta),
            "trait_b": name_to_id(tb),
            "corr_type": corr_type_map.get(item.data.get("type", ""), "POSITIVE"),
            "strength": item.data.get("strength", 0.0),
            "confidence": item.confidence,
            "mechanism": item.data.get("mechanism", ""),
            "conditions": [],
            "antagonistic_threshold": 0.3,
        })
    return results


def items_to_constraints(items: list[ExtractedItem]) -> list[dict]:
    """将提取项中的约束转换为 knowledge_store 可用的 dict"""
    results = []
    seen: set[str] = set()
    for item in items:
        if item.item_type != "constraint":
            continue
        name = item.data.get("name", "")
        if not name or name in seen:
            continue
        seen.add(name)
        results.append({
            "id": name_to_id(name),
            "name": name,
            "description": item.data.get("description", ""),
            "severity": item.data.get("severity", "WARNING"),
            "scope": "SPECIES",
            "species": "通用",
            "condition_expr": item.data.get("condition", ""),
            "consequence": "",
            "confidence": item.confidence,
            "tags": ["文献提取"],
        })
    return results


def name_to_id(name: str) -> str:
    """将中文名称转换为 trait id"""
    import hashlib
    suffix = hashlib.md5(name.encode()).hexdigest()[:8]
    return f"extracted_{suffix}"
