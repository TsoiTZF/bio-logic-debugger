"""
反模式匹配引擎

反模式（AntiPattern）不等同于约束规则。约束规则是普适的生理法则，
而反模式是经验的、历史的、叙事性的——它告诉育种家"这条路以前有人走过，
全都失败了，原因如下"。

匹配策略：
  1. 精确匹配：育种目标中的性状组合直接触发某个反模式
  2. 部分匹配：性状组合与反模式部分重叠，给出提示
  3. 语义匹配：通过 LLM 判断育种方向是否与已知反模式在语义上相似
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .domain import AntiPattern, BreedingGoal, ConstraintSeverity, EvidenceLevel


@dataclass
class AntiPatternMatch:
    """
    一次反模式匹配的结果。

    Attributes:
        anti_pattern: 匹配到的反模式
        match_type: 匹配类型（精确/部分/语义）
        matched_traits: 实际匹配到的性状
        missing_traits: 反模式中有但育种目标未提及的性状
        score: 匹配度 [0, 1]
    """
    anti_pattern: AntiPattern
    match_type: str  # exact / partial / semantic
    matched_traits: list[str] = field(default_factory=list)
    missing_traits: list[str] = field(default_factory=list)
    score: float = 0.0


class AntiPatternMatcher:
    """
    反模式匹配器。

    使用多策略匹配：先做精确匹配（高性能），
    再做部分匹配（召回），
    语义匹配交给外部 LLM。
    """

    def __init__(self, anti_patterns: list[AntiPattern] | None = None):
        self._patterns: dict[str, AntiPattern] = {}  # id -> pattern
        self._trait_index: dict[str, list[str]] = {}  # trait_id -> [pattern_id, ...]
        self._confidence_threshold: float = 0.3

        if anti_patterns:
            for p in anti_patterns:
                self.register(p)

    def register(self, pattern: AntiPattern) -> None:
        """注册一个反模式到索引"""
        self._patterns[pattern.id] = pattern
        for tid in pattern.trigger_traits:
            if tid not in self._trait_index:
                self._trait_index[tid] = []
            self._trait_index[tid].append(pattern.id)

    def register_many(self, patterns: list[AntiPattern]) -> None:
        for p in patterns:
            self.register(p)

    def unregister(self, pattern_id: str) -> None:
        """移除一个反模式"""
        pattern = self._patterns.pop(pattern_id, None)
        if pattern:
            for tid in pattern.trigger_traits:
                if tid in self._trait_index:
                    self._trait_index[tid] = [
                        pid for pid in self._trait_index[tid] if pid != pattern_id
                    ]

    def match(self, goal: BreedingGoal) -> list[AntiPatternMatch]:
        """
        对育种目标执行反模式匹配。

        返回按匹配度排序的匹配结果列表。
        """
        goal_traits = set(goal.trait_ids())
        results: list[AntiPatternMatch] = []

        # 策略1: 直接遍历所有反模式（小型知识库适用）
        for pattern in self._patterns.values():
            pattern_traits = set(pattern.trigger_traits)
            matched = goal_traits & pattern_traits
            missing = pattern_traits - goal_traits

            if not matched:
                continue

            # 计算匹配度：Jaccard 相似度 × 置信度
            jaccard = len(matched) / len(pattern_traits | goal_traits)
            score = jaccard * pattern.confidence

            if score < self._confidence_threshold:
                continue

            if matched == pattern_traits:
                match_type = "exact"
            elif len(matched) >= len(pattern_traits) * 0.5:
                match_type = "partial"
            else:
                match_type = "weak"

            results.append(AntiPatternMatch(
                anti_pattern=pattern,
                match_type=match_type,
                matched_traits=sorted(matched),
                missing_traits=sorted(missing),
                score=round(score, 3),
            ))

        # 按匹配度从高到低排序
        results.sort(key=lambda r: (-r.score, r.match_type))
        return results

    def quick_check(self, goal: BreedingGoal) -> list[AntiPatternMatch]:
        """
        快速检查：仅返回高置信度的精确/高度部分匹配。
        用于初始筛选阶段，避免信息过载。
        """
        all_matches = self.match(goal)
        return [
            m for m in all_matches
            if m.match_type == "exact"
            or (m.match_type == "partial" and m.score >= 0.5)
        ]

    @property
    def count(self) -> int:
        return len(self._patterns)

    def trait_coverage(self) -> dict[str, int]:
        """返回覆盖每个性状的反模式数量"""
        return {t: len(ids) for t, ids in self._trait_index.items()}
