"""
数据权重持久化模块

用户可以通过 UI 调整每条知识（性状/关联/约束）的置信度权重，
这些调整被持久化到本地 JSON 文件，引擎加载时自动应用。

权重优先级：用户手动调整 > 默认值 (1.0)
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Optional

from bio_logic_debugger.core.engine import BioLogicEngine

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent / "data"
WEIGHTS_PATH = DATA_DIR / "user_weights.json"

DEFAULT_WEIGHTS = {
    "traits": {},
    "correlations": {},
    "constraints": {},
}


def _ensure_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_weights() -> dict[str, dict[str, float]]:
    """加载用户调整过的权重配置"""
    if not WEIGHTS_PATH.exists():
        return dict(DEFAULT_WEIGHTS)

    try:
        data = json.loads(WEIGHTS_PATH.read_text(encoding="utf-8"))
        # 保证所有 key 存在
        result = dict(DEFAULT_WEIGHTS)
        result.update(data)
        return result
    except Exception as e:
        logger.warning(f"加载权重文件失败: {e}")
        return dict(DEFAULT_WEIGHTS)


def save_weights(weights: dict[str, dict[str, float]]) -> None:
    """批量保存权重配置"""
    _ensure_dir()
    try:
        WEIGHTS_PATH.write_text(
            json.dumps(weights, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info(f"已保存 {sum(len(v) for v in weights.values())} 条权重配置")
    except Exception as e:
        logger.warning(f"保存权重文件失败: {e}")


def save_weight(entity_type: str, entity_id: str, confidence: float) -> None:
    """单条保存权重"""
    weights = load_weights()
    if entity_type not in weights:
        weights[entity_type] = {}
    weights[entity_type][entity_id] = confidence
    save_weights(weights)


def apply_weights_to_engine(engine: BioLogicEngine) -> int:
    """
    将用户权重应用到引擎。

    遍历 engine 中已注册的 traits/correlations/constraints，
    如果有对应的用户权重则覆盖其 confidence 字段。

    返回：已更新的条目数
    """
    weights = load_weights()
    updated = 0

    # 应用性状权重
    trait_weights = weights.get("traits", {})
    for tid, trait in engine._traits.items():
        if tid in trait_weights:
            trait.confidence = trait_weights[tid]
            updated += 1

    # 应用关联权重
    corr_weights = weights.get("correlations", {})
    for corr in engine._correlations:
        key = _corr_key(corr.trait_a, corr.trait_b)
        if key in corr_weights:
            corr.confidence = corr_weights[key]
            updated += 1

    # 应用约束权重
    cstr_weights = weights.get("constraints", {})
    for cstr in engine._constraints:
        if cstr.id in cstr_weights:
            cstr.confidence = cstr_weights[cstr.id]
            updated += 1

    if updated:
        logger.info(f"已应用 {updated} 条用户权重到引擎")
    return updated


def _corr_key(trait_a: str, trait_b: str) -> str:
    """生成关联的唯一 key（排序无关）"""
    return f"{trait_a}__{trait_b}" if trait_a < trait_b else f"{trait_b}__{trait_a}"
