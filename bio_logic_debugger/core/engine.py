"""
Bio-Logic Debugger — 约束验证引擎

引擎是整个系统的核心编排器。它接收一个育种目标，
依次经过多层验证管线，最终生成一份完整的验证报告。

验证管线（按执行顺序）：
  1. 基础检查层：性状是否存在、数值是否在合理范围内
  2. 关联检查层：逐对检查目标性状之间的关联，发现拮抗关系
  3. 约束规则层：检查是否符合已知的生物学约束
  4. 反模式匹配层：检查是否触发了历史反模式
  5. （可选）LLM 推理层：调用大模型做更深层的生物合理性分析
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Callable, Optional

from .domain import (
    AntiPattern,
    BiologicalConstraint,
    BreedingGoal,
    ConstraintSeverity,
    ConstraintScope,
    CorrelationType,
    EvidenceLevel,
    Trait,
    TraitCorrelation,
    TraitTarget,
    ValidationReport,
    Violation,
)
from .anti_pattern import AntiPatternMatcher

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# 验证管线接口
# ═══════════════════════════════════════════════════════════════

@dataclass
class ValidationContext:
    """
    验证上下文，在管线各层之间传递数据。

    每一层可以向 context 写入中间结果，
    供后续层或最终报告生成使用。
    """
    goal: BreedingGoal
    trait_map: dict[str, Trait] = field(default_factory=dict)
    violations: list[Violation] = field(default_factory=list)
    matched_anti_patterns: list[AntiPattern] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    llm_comment: str = ""

    @property
    def is_fatal(self) -> bool:
        return any(
            v.severity == ConstraintSeverity.FATAL
            for v in self.violations
        )


type ValidationLayer = Callable[[ValidationContext], ValidationContext]


# ═══════════════════════════════════════════════════════════════
# 引擎主体
# ═══════════════════════════════════════════════════════════════

class BioLogicEngine:
    """
    生物逻辑验证引擎的主类。

    用法：
        engine = BioLogicEngine()
        engine.register_trait(rice_trait)
        engine.register_correlation(rice_corr)
        report = engine.validate(goal)
        print(report.narrative())
    """

    def __init__(self):
        self._traits: dict[str, Trait] = {}
        self._correlations: list[TraitCorrelation] = []
        self._constraints: list[BiologicalConstraint] = []
        self._anti_patterns: AntiPatternMatcher = AntiPatternMatcher()
        self._layers: list[ValidationLayer] = []
        self._llm_callback: Optional[Callable] = None

        # 注册默认验证层
        self._register_default_layers()

    def _register_default_layers(self) -> None:
        self._layers = [
            self._layer_basic_check,
            self._layer_correlation_check,
            self._layer_constraint_check,
            self._layer_anti_pattern_match,
        ]

    # -------- 注册 API --------

    def register_trait(self, trait: Trait) -> None:
        self._traits[trait.id] = trait

    def register_traits(self, traits: list[Trait]) -> None:
        for t in traits:
            self.register_trait(t)

    def register_correlation(self, corr: TraitCorrelation) -> None:
        self._correlations.append(corr)

    def register_correlations(self, corrs: list[TraitCorrelation]) -> None:
        self._correlations.extend(corrs)

    def register_constraint(self, constraint: BiologicalConstraint) -> None:
        self._constraints.append(constraint)

    def register_constraints(self, constraints: list[BiologicalConstraint]) -> None:
        self._constraints.extend(constraints)

    def register_anti_pattern(self, pattern: AntiPattern) -> None:
        self._anti_patterns.register(pattern)

    def register_anti_patterns(self, patterns: list[AntiPattern]) -> None:
        self._anti_patterns.register_many(patterns)

    def register_layer(self, layer: ValidationLayer, index: int | None = None) -> None:
        """注册自定义验证层"""
        if index is None:
            self._layers.append(layer)
        else:
            self._layers.insert(index, layer)

    def set_llm_callback(self, callback: Callable) -> None:
        """设置 LLM 推理回调"""
        self._llm_callback = callback

    # -------- 验证管线 --------

    def validate(self, goal: BreedingGoal) -> ValidationReport:
        """
        执行完整的验证管线。

        流程：
          1. 构建验证上下文
          2. 依次执行各验证层
          3. （可选）调用 LLM 推理
          4. 生成最终报告
        """
        ctx = ValidationContext(
            goal=goal,
            trait_map={k: v for k, v in self._traits.items()},
        )

        # 执行各层
        for layer in self._layers:
            ctx = layer(ctx)
            if ctx.is_fatal:
                # 致命错误，提前终止
                logger.info(
                    f"发现致命违反，提前终止验证管线 (layer={layer.__name__})"
                )
                break

        # 可选的 LLM 分析
        if self._llm_callback and not ctx.is_fatal:
            try:
                ctx = self._llm_callback(ctx)
            except Exception as e:
                logger.warning(f"LLM 推理失败: {e}")
                ctx.llm_comment = f"[LLM 推理异常: {e}]"

        return ValidationReport(
            goal=goal,
            passed=len([
                v for v in ctx.violations
                if v.severity in (ConstraintSeverity.FATAL, ConstraintSeverity.SEVERE)
            ]) == 0,
            violations=ctx.violations,
            matched_anti_patterns=ctx.matched_anti_patterns,
            suggestions=ctx.suggestions,
            llm_comment=ctx.llm_comment,
        )

    # -------- 默认验证层实现 --------

    @staticmethod
    def _layer_basic_check(ctx: ValidationContext) -> ValidationContext:
        """
        基础检查层：
        - 目标性状是否在知识库中
        - 目标数值是否在合理范围内
        """
        for target in ctx.goal.targets:
            trait = ctx.trait_map.get(target.trait_id)
            if trait is None:
                ctx.suggestions.append(
                    f"性状 '{target.trait_id}' 不在当前知识库中，"
                    "将跳过与此性状相关的所有检查。建议先补充该性状的定义。"
                )
                continue

            # 检查数值范围
            lo, hi = trait.typical_range
            if target.desired_value is not None and lo is not None and hi is not None:
                if target.desired_value < lo or target.desired_value > hi:
                    ctx.violations.append(Violation(
                        constraint_id=f"range_check.{trait.id}",
                        severity=ConstraintSeverity.WARNING,
                        title=f"目标值超出 {trait.name} 的典型范围",
                        description=(
                            f"'{trait.name}' 的典型范围是 [{lo}, {hi}] {trait.unit}，"
                            f"而育种目标设置为 {target.desired_value}"
                        ),
                        mechanism="数值超出物种的生理极限范围",
                        narrative=(
                            f"关于「{trait.name}」：您设定的目标 ({target.desired_value}) "
                            f"超过典型范围（{lo:.2f} ~ {hi:.2f}）。\n"
                            f"这并不意味着绝对不可能，但如果该数值超出了物种已知的生理极限，"
                            f"可能需要引入远缘种质资源才能实现。"
                        ),
                        involved_traits=[trait.id],
                        suggestion=(
                            f"请确认：是否确实需要 {target.desired_value}？"
                            f"如果这是打破现有纪录的目标，建议分阶段实现。"
                        ),
                        source="rule",
                    ))

        return ctx

    def _layer_correlation_check(self, ctx: ValidationContext) -> ValidationContext:
        """
        关联检查层：
        逐对检查用户目标中的性状之间是否存在拮抗关系。
        """
        goal_traits = set(ctx.goal.trait_ids())

        for corr in self._correlations:
            # 只检查与育种目标相关的关联
            if corr.trait_a not in goal_traits and corr.trait_b not in goal_traits:
                continue

            # 找到用户对这两个性状的目标值
            target_a = self._find_target(ctx.goal, corr.trait_a)
            target_b = self._find_target(ctx.goal, corr.trait_b)

            is_relevant = (
                (corr.trait_a in goal_traits and corr.trait_b in goal_traits)
                or (corr.trait_a in goal_traits and corr.trait_b in ctx.trait_map)
            )

            if not is_relevant:
                continue

            # 构建叙事
            tname_a = self._trait_name(corr.trait_a)
            tname_b = self._trait_name(corr.trait_b)

            if corr.is_antagonistic():
                # 检查用户是否要求这两个性状同时达到高水平
                user_wants_both_high = self._wants_high(target_a) and self._wants_high(target_b)

                if not user_wants_both_high and corr.corr_type == CorrelationType.TRADE_OFF:
                    # 权衡关系且用户没有同时要求高值，只是提示
                    continue

                if user_wants_both_high:
                    severity = (
                        ConstraintSeverity.FATAL
                        if abs(corr.strength) >= 0.7
                        else ConstraintSeverity.SEVERE
                        if abs(corr.strength) >= 0.5
                        else ConstraintSeverity.WARNING
                    )

                    narrative_parts = [
                        f"在「{tname_a}」和「{tname_b}」之间存在一个已知的{self._corr_type_label(corr)}关系",
                        f"（相关系数 r = {corr.strength:.2f}）。",
                    ]
                    if corr.mechanism:
                        narrative_parts.append(f"\n\n背后的生理机制：{corr.mechanism}")

                    narrative_parts.append(
                        f"\n\n这意味着当您试图同时提高这两者时，"
                        f"其中一方的提升将会被另一方拖累。"
                    )

                    # 如果双方都设置了具体数值，给出冲击评估
                    if target_a and target_b:
                        impact = abs(corr.strength) * 100 * 0.5
                        narrative_parts.append(
                            f"\n粗略估算，同时追求两个目标可能导致实际达成率下降约 {impact:.0f}%。"
                        )

                    ctx.violations.append(Violation(
                        constraint_id=f"corr.{corr.trait_a}.{corr.trait_b}",
                        severity=severity,
                        title=f"拮抗关系：{tname_a} ↔ {tname_b}",
                        description=(
                            f"'{tname_a}' 与 '{tname_b}' 之间存在 {self._corr_type_label(corr)}，"
                            f"强度 {corr.strength:.2f}"
                        ),
                        mechanism=corr.mechanism or "未知机制",
                        narrative="".join(narrative_parts),
                        involved_traits=[corr.trait_a, corr.trait_b],
                        suggestion=(
                            f"建议：如果可能，尝试降低其中之一的目标值。"
                            f"或者寻找是否存在打破该连锁的特殊种质资源。"
                        ),
                        source="rule",
                    ))

            elif corr.corr_type == CorrelationType.CURVILINEAR:
                # 曲线关系：存在最优区间，过高或过低都不好
                ctx.violations.append(Violation(
                    constraint_id=f"corr_curve.{corr.trait_a}.{corr.trait_b}",
                    severity=ConstraintSeverity.INFO,
                    title=f"曲线关系提示：{tname_a} 与 {tname_b}",
                    description=f"两者之间存在曲线相关，存在最优配比区间",
                    mechanism=corr.mechanism or "未知机制",
                    narrative=(
                        f"「{tname_a}」和「{tname_b}」之间不是简单的线性关系，"
                        f"而是曲线相关。这意味着存在一个最优配比区间，"
                        f"过高或过低都会导致综合表现下降。\n\n"
                        f"建议不要同时追求两者最大化，而是要找到最佳平衡点。"
                    ),
                    involved_traits=[corr.trait_a, corr.trait_b],
                    suggestion="使用响应面法（RSM）寻找最优配比区间。",
                    source="rule",
                ))

        return ctx

    def _layer_constraint_check(self, ctx: ValidationContext) -> ValidationContext:
        """
        约束规则检查层：
        检查育种目标是否触发了已知的生物学约束。
        """
        for constraint in self._constraints:
            # 简单的范围检查：如果约束中涉及的性状都在目标中，触发检查
            # 这里是简化版，实际中 condition_expr 可以用表达式引擎解析
            involved = self._parse_trait_refs(constraint.condition_expr)
            if not involved:
                continue

            if not any(t in ctx.goal.trait_ids() for t in involved):
                continue

            # 构建叙事
            narrative_parts = [
                f"触发了约束规则「{constraint.name}」",
            ]
            if constraint.description:
                narrative_parts.append(f"\n\n{constraint.description}")
            if constraint.consequence:
                narrative_parts.append(f"\n\n生理后果：{constraint.consequence}")

            ctx.violations.append(Violation(
                constraint_id=constraint.id,
                severity=constraint.severity,
                title=constraint.name,
                description=constraint.description,
                mechanism=constraint.consequence,
                narrative="".join(narrative_parts),
                involved_traits=involved,
                suggestion="",
                source="rule",
            ))

        return ctx

    def _layer_anti_pattern_match(self, ctx: ValidationContext) -> ValidationContext:
        """反模式匹配层"""
        matches = self._anti_patterns.match(ctx.goal)

        for m in matches:
            pattern = m.anti_pattern

            # 精确匹配和高度部分匹配加入到反模式列表
            if m.match_type in ("exact", "partial") and m.score >= 0.5:
                ctx.matched_anti_patterns.append(pattern)

                # 构造历史教训叙事
                narrative_parts = [
                    f"⚠️ 您的育种目标与一个已知的育种反模式高度相似："
                    f"「{pattern.name}」\n\n",
                ]
                if pattern.description:
                    narrative_parts.append(f"{pattern.description}\n\n")

                if pattern.failed_approaches:
                    narrative_parts.append("历史上失败的案例：\n")
                    for fa in pattern.failed_approaches[:3]:
                        narrative_parts.append(f"  · {fa.description} —— {fa.reason_failed}\n")
                    narrative_parts.append("\n")

                if pattern.alternative_directions:
                    narrative_parts.append("推荐的替代方向：\n")
                    for i, alt in enumerate(pattern.alternative_directions, 1):
                        narrative_parts.append(f"  {i}. {alt}\n")

                narrative = "".join(narrative_parts)

                ctx.violations.append(Violation(
                    constraint_id=f"anti_pattern.{pattern.id}",
                    severity=pattern.severity,
                    title=f"反模式触发：{pattern.name}",
                    description=pattern.description,
                    mechanism=pattern.mechanism or "经验性规律",
                    narrative=narrative,
                    involved_traits=pattern.trigger_traits,
                    suggestion=(
                        pattern.alternative_directions[0]
                        if pattern.alternative_directions
                        else "建议重新评估育种方向"
                    ),
                    source="anti_pattern",
                ))

            # 弱匹配只增加建议
            elif m.match_type == "weak":
                ctx.suggestions.append(
                    f"部分匹配到反模式「{pattern.name}」，"
                    f"涉及的性状：{', '.join(m.matched_traits)}。"
                )

        return ctx

    # -------- 工具方法 --------

    def _find_target(self, goal: BreedingGoal, trait_id: str) -> Optional[TraitTarget]:
        for t in goal.targets:
            if t.trait_id == trait_id:
                return t
        return None

    def _trait_name(self, trait_id: str) -> str:
        trait = self._traits.get(trait_id)
        return trait.name if trait else trait_id

    @staticmethod
    def _wants_high(target: Optional[TraitTarget]) -> bool:
        if target is None:
            return False
        if target.direction in (">=", ">"):
            return True
        if target.direction == "range" and target.range_min and target.range_max:
            avg = (target.range_min + target.range_max) / 2
            return avg > 0  # 保守估计
        return False

    @staticmethod
    def _corr_type_label(corr: TraitCorrelation) -> str:
        labels = {
            CorrelationType.NEGATIVE: "负相关连锁",
            CorrelationType.TRADE_OFF: "权衡关系",
            CorrelationType.POSITIVE: "正相关",
            CorrelationType.CURVILINEAR: "曲线关系",
            CorrelationType.THRESHOLD: "阈值依赖关系",
            CorrelationType.EPISTATIC: "上位效应关系",
        }
        return labels.get(corr.corr_type, "未知关联")

    @staticmethod
    def _parse_trait_refs(expr: str) -> list[str]:
        """从条件表达式中提取性状引用（简化版）"""
        if not expr:
            return []
        # 简单策略：按空白分割，查找 ${...} 模式的引用
        # 完整版应使用表达式解析器
        refs = []
        for part in expr.replace("(", " ").replace(")", " ").split():
            if part.startswith("$"):
                refs.append(part[1:])
        return refs
