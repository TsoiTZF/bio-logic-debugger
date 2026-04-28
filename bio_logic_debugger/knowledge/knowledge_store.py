"""
知识库存储与同步模块

管理知识库的加载、合并、持久化，以及社区知识库的自动同步。

知识库来源层级（优先级从高到低）：
  1. 社区知识库（从 GitHub raw 拉取的最新 JSON）
  2. 内置知识库（rice_knowledge.py）
  3. 本地用户扩充（通过 app 导入添加）
"""
from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any, Optional

from bio_logic_debugger.core.domain import (
    AntiPattern,
    BiologicalConstraint,
    ConstraintScope,
    ConstraintSeverity,
    CorrelationEvidence,
    CorrelationType,
    EvidenceLevel,
    FailedApproach,
    Trait,
    TraitCorrelation,
)
from bio_logic_debugger.knowledge.rice_knowledge import (
    ANTI_PATTERNS as BUILTIN_ANTI_PATTERNS,
    CONSTRAINTS as BUILTIN_CONSTRAINTS,
    CORRELATIONS as BUILTIN_CORRELATIONS,
    TRAITS as BUILTIN_TRAITS,
)

logger = logging.getLogger(__name__)

# 社区知识库的 raw URL（从 TsoiTZF/bio-logic-knowledge 主分支）
COMMUNITY_BASE = (
    "https://raw.githubusercontent.com/TsoiTZF/bio-logic-knowledge/main"
)

# 本地 data 目录（相对于本文件）
DATA_DIR = Path(__file__).parent / "data"


# ═══════════════════════════════════════════════════════════════
# 序列化辅助
# ═══════════════════════════════════════════════════════════════


def trait_to_dict(t: Trait) -> dict:
    return {
        "id": t.id,
        "name": t.name,
        "description": t.description,
        "category": t.category,
        "unit": t.unit,
        "typical_range": list(t.typical_range) if t.typical_range else [None, None],
        "tags": t.tags,
        "species": t.species,
        "confidence": t.confidence,
    }


def trait_from_dict(d: dict) -> Trait:
    r = d.get("typical_range", [None, None])
    return Trait(
        id=d["id"],
        name=d["name"],
        description=d.get("description", ""),
        category=d.get("category", ""),
        unit=d.get("unit", ""),
        typical_range=(r[0], r[1]) if isinstance(r, list) else (None, None),
        tags=d.get("tags", []),
        species=d.get("species", "通用"),
        confidence=d.get("confidence", 1.0),
    )


def correlation_to_dict(c: TraitCorrelation) -> dict:
    return {
        "trait_a": c.trait_a,
        "trait_b": c.trait_b,
        "corr_type": c.corr_type.name,
        "strength": c.strength,
        "confidence": c.confidence,
        "mechanism": c.mechanism,
        "conditions": c.conditions,
        "antagonistic_threshold": c.antagonistic_threshold,
    }


def correlation_from_dict(d: dict) -> TraitCorrelation:
    return TraitCorrelation(
        trait_a=d["trait_a"],
        trait_b=d["trait_b"],
        corr_type=CorrelationType[d["corr_type"]],
        strength=d["strength"],
        confidence=d.get("confidence", 1.0),
        mechanism=d.get("mechanism", ""),
        conditions=d.get("conditions", []),
        antagonistic_threshold=d.get("antagonistic_threshold", 0.3),
    )


def constraint_to_dict(c: BiologicalConstraint) -> dict:
    return {
        "id": c.id,
        "name": c.name,
        "description": c.description,
        "severity": c.severity.name,
        "scope": c.scope.name,
        "species": c.species,
        "condition_expr": c.condition_expr,
        "consequence": c.consequence,
        "confidence": c.confidence,
        "tags": c.tags,
    }


def _parse_constraint_scope(name: str) -> ConstraintScope:
    """安全地将字符串转换为 ConstraintScope 枚举"""
    try:
        return ConstraintScope[name.upper()]
    except KeyError:
        logger.warning(f"未知的 ConstraintScope: {name}，使用 SPECIES 兜底")
        return ConstraintScope.SPECIES


def constraint_from_dict(d: dict) -> BiologicalConstraint:
    return BiologicalConstraint(
        id=d["id"],
        name=d["name"],
        description=d.get("description", ""),
        severity=ConstraintSeverity[d["severity"]],
        scope=_parse_constraint_scope(d.get("scope", "SPECIES")),
        species=d.get("species", "通用"),
        condition_expr=d.get("condition_expr", ""),
        consequence=d.get("consequence", ""),
        confidence=d.get("confidence", 1.0),
        tags=d.get("tags", []),
    )


def anti_pattern_to_dict(ap: AntiPattern) -> dict:
    return {
        "id": ap.id,
        "name": ap.name,
        "description": ap.description,
        "trigger_traits": ap.trigger_traits,
        "severity": ap.severity.name,
        "historical_examples": ap.historical_examples,
        "failed_approaches": [
            {"description": fa.description, "reason_failed": fa.reason_failed}
            for fa in ap.failed_approaches
        ],
        "alternative_directions": ap.alternative_directions,
        "mechanism": ap.mechanism,
        "confidence": ap.confidence,
        "tags": ap.tags,
        "species": ap.species,
    }


def anti_pattern_from_dict(d: dict) -> AntiPattern:
    return AntiPattern(
        id=d["id"],
        name=d["name"],
        description=d.get("description", ""),
        trigger_traits=d.get("trigger_traits", []),
        severity=ConstraintSeverity[d.get("severity", "WARNING")],
        historical_examples=d.get("historical_examples", []),
        failed_approaches=[
            FailedApproach(fa["description"], fa["reason_failed"])
            for fa in d.get("failed_approaches", [])
        ],
        alternative_directions=d.get("alternative_directions", []),
        mechanism=d.get("mechanism", ""),
        confidence=d.get("confidence", 1.0),
        tags=d.get("tags", []),
        species=d.get("species", "通用"),
    )


# ═══════════════════════════════════════════════════════════════
# 核心 API
# ═══════════════════════════════════════════════════════════════


def sync_from_community() -> bool:
    """从社区知识库仓库拉取最新的 JSON 文件到本地 data/ 目录"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    files = ["traits.json", "correlations.json", "constraints.json", "anti_patterns.json"]
    success = True

    for fname in files:
        url = f"{COMMUNITY_BASE}/{fname}"
        try:
            import httpx
            resp = httpx.get(url, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            dest = DATA_DIR / fname
            with open(dest, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"已同步 {fname} ({len(data)} 条)")
        except Exception as e:
            logger.warning(f"同步 {fname} 失败: {e}")
            success = False

    # 写入同步时间戳
    if success:
        ts_path = DATA_DIR / ".sync_timestamp"
        ts_path.write_text(str(int(time.time())), encoding="utf-8")

    return success


def get_last_sync_time() -> Optional[str]:
    """获取最后一次同步的时间"""
    ts_path = DATA_DIR / ".sync_timestamp"
    if ts_path.exists():
        ts = ts_path.read_text(encoding="utf-8").strip()
        try:
            t = int(ts)
            from datetime import datetime
            return datetime.fromtimestamp(t).strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            pass
    return None


def has_community_data() -> bool:
    """检查本地是否有社区知识库数据"""
    return all((DATA_DIR / f).exists() for f in ["traits.json", "correlations.json"])


def load_community() -> dict:
    """从本地 data/ 目录加载社区知识库数据（JSON 格式的原始 dict）"""
    result = {"traits": [], "correlations": [], "constraints": [], "anti_patterns": []}
    for key, fname in [
        ("traits", "traits.json"),
        ("correlations", "correlations.json"),
        ("constraints", "constraints.json"),
        ("anti_patterns", "anti_patterns.json"),
    ]:
        path = DATA_DIR / fname
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    result[key] = json.load(f)
            except Exception as e:
                logger.warning(f"加载 {fname} 失败: {e}")
    return result


def load_builtin() -> dict:
    """加载内置知识库（rice_knowledge.py），返回序列化后的 dict 列表"""
    return {
        "traits": [trait_to_dict(t) for t in BUILTIN_TRAITS],
        "correlations": [correlation_to_dict(c) for c in BUILTIN_CORRELATIONS],
        "constraints": [constraint_to_dict(c) for c in BUILTIN_CONSTRAINTS],
        "anti_patterns": [anti_pattern_to_dict(ap) for ap in BUILTIN_ANTI_PATTERNS],
    }


def merge_knowledge(
    builtin: dict,
    community: dict,
    user_traits: Optional[list[dict]] = None,
    user_correlations: Optional[list[dict]] = None,
    user_constraints: Optional[list[dict]] = None,
    user_anti_patterns: Optional[list[dict]] = None,
) -> dict:
    """
    合并三源知识库，优先级：user > community > builtin。
    以 trait id 和 correlation (trait_a, trait_b) 为去重 key。
    """
    seen_traits: set[str] = set()
    seen_corrs: set[tuple[str, str]] = set()
    seen_constraints: set[str] = set()
    seen_patterns: set[str] = set()

    result = {"traits": [], "correlations": [], "constraints": [], "anti_patterns": []}

    # 1. builtin（最低优先级）
    for item in builtin.get("traits", []):
        tid = item.get("id", "")
        if tid not in seen_traits:
            result["traits"].append(item)
            seen_traits.add(tid)
    for item in builtin.get("correlations", []):
        key = (item.get("trait_a", ""), item.get("trait_b", ""))
        if key not in seen_corrs:
            result["correlations"].append(item)
            seen_corrs.add(key)
    for item in builtin.get("constraints", []):
        cid = item.get("id", "")
        if cid not in seen_constraints:
            result["constraints"].append(item)
            seen_constraints.add(cid)
    for item in builtin.get("anti_patterns", []):
        pid = item.get("id", "")
        if pid not in seen_patterns:
            result["anti_patterns"].append(item)
            seen_patterns.add(pid)

    # 2. community（覆盖 builtin）
    for item in community.get("traits", []):
        tid = item.get("id", "")
        if tid in seen_traits:
            _replace_in_list(result["traits"], "id", tid, item)
        else:
            result["traits"].append(item)
            seen_traits.add(tid)
    for item in community.get("correlations", []):
        key = (item.get("trait_a", ""), item.get("trait_b", ""))
        if key in seen_corrs:
            _replace_in_list(result["correlations"], lambda x: (x.get("trait_a", ""), x.get("trait_b", "")) == key, True, item)
        else:
            result["correlations"].append(item)
            seen_corrs.add(key)
    for item in community.get("constraints", []):
        cid = item.get("id", "")
        if cid in seen_constraints:
            _replace_in_list(result["constraints"], "id", cid, item)
        else:
            result["constraints"].append(item)
            seen_constraints.add(cid)
    for item in community.get("anti_patterns", []):
        pid = item.get("id", "")
        if pid in seen_patterns:
            _replace_in_list(result["anti_patterns"], "id", pid, item)
        else:
            result["anti_patterns"].append(item)
            seen_patterns.add(pid)

    # 3. user（最高优先级）
    for item in (user_traits or []):
        tid = item.get("id", "")
        if tid in seen_traits:
            _replace_in_list(result["traits"], "id", tid, item)
        else:
            result["traits"].append(item)
    for item in (user_correlations or []):
        key = (item.get("trait_a", ""), item.get("trait_b", ""))
        if key in seen_corrs:
            _replace_in_list(result["correlations"], lambda x: (x.get("trait_a", ""), x.get("trait_b", "")) == key, True, item)
        else:
            result["correlations"].append(item)
    for item in (user_constraints or []):
        cid = item.get("id", "")
        if cid in seen_constraints:
            _replace_in_list(result["constraints"], "id", cid, item)
        else:
            result["constraints"].append(item)
    for item in (user_anti_patterns or []):
        pid = item.get("id", "")
        if pid in seen_patterns:
            _replace_in_list(result["anti_patterns"], "id", pid, item)
        else:
            result["anti_patterns"].append(item)

    return result


def _replace_in_list(lst: list, key: str | callable, value: Any, new_item: dict) -> None:
    """替换列表中的元素（用于覆盖）"""
    if callable(key):
        pred = key
    else:
        pred = lambda x: x.get(key) == value
    for i, item in enumerate(lst):
        if pred(item):
            lst[i] = new_item
            return


def deserialize_all(merged: dict) -> tuple:
    """将合并后的 dict 数据反序列化为领域对象"""
    traits = [trait_from_dict(d) for d in merged.get("traits", [])]
    correlations = [correlation_from_dict(d) for d in merged.get("correlations", [])]
    constraints = [constraint_from_dict(d) for d in merged.get("constraints", [])]
    anti_patterns = [anti_pattern_from_dict(d) for d in merged.get("anti_patterns", [])]
    return traits, correlations, constraints, anti_patterns


def export_user_knowledge(
    traits: list[dict],
    correlations: list[dict],
    constraints: list[dict],
    anti_patterns: list[dict],
) -> str:
    """将用户扩充的知识导出为 JSON 字符串，用于提 PR"""
    export = {
        "traits": traits,
        "correlations": correlations,
        "constraints": constraints,
        "anti_patterns": anti_patterns,
    }
    return json.dumps(export, ensure_ascii=False, indent=2)


def load_and_merge(
    user_traits=None, user_correlations=None,
    user_constraints=None, user_anti_patterns=None,
) -> tuple:
    """
    一站式加载+合并+反序列化。
    优先使用社区数据，其次内置兜底。
    """
    builtin = load_builtin()
    if has_community_data():
        community = load_community()
    else:
        community = {"traits": [], "correlations": [], "constraints": [], "anti_patterns": []}

    merged = merge_knowledge(
        builtin, community,
        user_traits=user_traits,
        user_correlations=user_correlations,
        user_constraints=user_constraints,
        user_anti_patterns=user_anti_patterns,
    )
    result = deserialize_all(merged)

    # 应用用户调整的权重
    try:
        from bio_logic_debugger.knowledge.weight_store import apply_weights_to_engine
        # 注意：此时 engine 还未创建，无法直接调用。
        # 权重的应用延迟到 engine 注册所有知识之后，在 app.py 中处理。
    except ImportError:
        pass

    return result
