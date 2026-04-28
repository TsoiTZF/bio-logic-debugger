"""
Bio-Logic Debugger — 核心领域模型

定义生物学逻辑约束系统的骨架数据结构。
所有模块以此为基础进行构建，保证可扩展性与类型安全。
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Optional


# ═══════════════════════════════════════════════════════════════
# 基础枚举
# ═══════════════════════════════════════════════════════════════

class CorrelationType(Enum):
    """两性状之间的关联类型"""
    POSITIVE = auto()            # 正相关：A↑ → B↑
    NEGATIVE = auto()            # 负相关：A↑ → B↓
    CURVILINEAR = auto()         # 曲线相关：存在最优区间
    THRESHOLD = auto()           # 阈值依赖：超过某值后关系翻转
    EPISTATIC = auto()           # 上位效应：依赖第三个性状的存在
    TRADE_OFF = auto()           # 权衡：不可兼得，必须取舍


class ConstraintSeverity(Enum):
    """约束违反的严重等级"""
    FATAL = auto()      # 生理上不可能，绝对死胡同
    SEVERE = auto()     # 极难突破，历史上极少成功
    WARNING = auto()    # 有冲突但可能通过特殊手段缓解
    INFO = auto()       # 需要注意，信息性提示


class EvidenceLevel(Enum):
    """证据等级：知识的确信度"""
    CONFIRMED = auto()        # 多篇独立文献+多年田间验证
    STRONG = auto()           # 有可靠文献支持
    SUGGESTED = auto()        # 单篇文献或初步观察
    ANECDOTAL = auto()        # 经验总结，未严格验证
    HYPOTHETICAL = auto()     # 理论推导，待验证


class ConstraintScope(Enum):
    """约束的适用范围"""
    UNIVERSAL = auto()        # 适用于所有作物
    GENUS = auto()            # 适用于某个属（如 Oryza）
    SPECIES = auto()          # 适用于某个种
    SUBSPECIES = auto()       # 适用于某个亚种/生态型
    CUSTOM = auto()           # 用户自定义


# ═══════════════════════════════════════════════════════════════
# 性状定义
# ═══════════════════════════════════════════════════════════════

@dataclass
class Trait:
    """
    一个可测量的生物学性状。

    这是系统中最基本的原子单位。一切约束、关联、反模式
    最终都落在性状上。

    Attributes:
        id: 唯一标识符，如 'rice.yield.per_plant'
        name: 人类可读名称，如 '单株产量'
        description: 详细描述，包括测量方法
        category: 分类，如 '产量', '品质', '抗病', '株型', '生理'
        unit: 测量单位
        typical_range: 该性状在目标物种中的典型取值范围 [min, max]
        tags: 标签，用于快速分类检索
    """
    id: str
    name: str
    description: str
    category: str
    unit: str = ""
    typical_range: tuple[float | None, float | None] = (None, None)
    tags: list[str] = field(default_factory=list)
    species: str = "通用"
    confidence: float = 1.0


# ═══════════════════════════════════════════════════════════════
# 性状关联
# ═══════════════════════════════════════════════════════════════

@dataclass
class CorrelationEvidence:
    """支撑一条关联规则的证据记录"""
    level: EvidenceLevel
    source: str                     # 文献引用或来源说明
    description: str                # 证据具体内容
    url: str = ""                   # 链接
    year: int = 0                   # 发表年份


@dataclass
class TraitCorrelation:
    """
    两个性状之间的关联关系。

    这是约束系统的核心：如果育种目标同时要求一对负相关性状
    都达到极值，引擎就会在这里触发警告。

    Attributes:
        trait_a, trait_b: 两个性状的 ID
        corr_type: 关联类型
        strength: 关联强度 [-1, 1]，负值表示负相关
        confidence: 置信度 [0, 1]
        mechanism: 生理机制解释——育种家关心的"为什么"
        conditions: 该关联成立的前提条件（如"C3植物"）
        evidence: 支撑证据列表
        antagonistic_threshold: 拮抗阈值，当双方需求超过此值时触发
    """
    trait_a: str
    trait_b: str
    corr_type: CorrelationType
    strength: float                 # -1.0 ~ 1.0
    confidence: float = 1.0         # 0.0 ~ 1.0
    mechanism: str = ""             # 生理机制解释
    conditions: list[str] = field(default_factory=list)
    evidence: list[CorrelationEvidence] = field(default_factory=list)
    antagonistic_threshold: float = 0.3  # 超过此强度视为"拮抗"

    def is_antagonistic(self) -> bool:
        """是否为拮抗关系（负相关且强度超过阈值）"""
        return self.corr_type in (
            CorrelationType.NEGATIVE,
            CorrelationType.TRADE_OFF,
        ) and abs(self.strength) >= self.antagonistic_threshold


# ═══════════════════════════════════════════════════════════════
# 约束规则
# ═══════════════════════════════════════════════════════════════

@dataclass
class BiologicalConstraint:
    """
    一条生物学约束规则。

    比 TraitCorrelation 更灵活：可以表达"如果A超过X且B低于Y则违反"
    这样的复合条件，而不只是两两关联。

    Attributes:
        id: 唯一标识
        name: 规则名称
        description: 规则描述
        severity: 违反后果的严重等级
        scope: 适用范围
        species: 适用的物种
        condition_expr: 条件表达式（结构化的判定逻辑）
        consequence: 违反的生理后果描述
        confidence: 置信度
        evidence: 证据列表
        tags: 标签
    """
    id: str
    name: str
    description: str
    severity: ConstraintSeverity
    scope: ConstraintScope = ConstraintScope.UNIVERSAL
    species: str = "通用"
    condition_expr: str = ""         # 条件表达式，详见 engine 文档
    consequence: str = ""
    confidence: float = 1.0
    evidence: list[CorrelationEvidence] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════
# 反模式
# ═══════════════════════════════════════════════════════════════

@dataclass
class FailedApproach:
    """历史上尝试过但失败的育种策略"""
    description: str
    reason_failed: str
    year_range: tuple[int, int] = (0, 0)
    reference: str = ""


@dataclass
class AntiPattern:
    """
    一个"反模式"——被历史反复验证的育种死胡同。

    它与 BiologicalConstraint 的区别在于：约束是普适的生理法则，
    而反模式是经验的、历史的、叙事性的。它告诉育种家
    "这条路以前有人走过，全都失败了，原因如下"。

    Attributes:
        id: 唯一标识
        name: 反模式名称，如"高产低质的陷阱"
        description: 详细描述
        trigger_traits: 触发此反模式的性状组合
        severity: 严重等级
        historical_examples: 历史案例
        failed_approaches: 已尝试的失败策略
        alternative_directions: 推荐的替代方向
        mechanism: 背后的生理机制
        confidence: 置信度
        evidence: 支撑证据
        tags: 标签
    """
    id: str
    name: str
    description: str
    trigger_traits: list[str]        # 相关的 trait id 列表
    severity: ConstraintSeverity = ConstraintSeverity.WARNING
    historical_examples: list[str] = field(default_factory=list)
    failed_approaches: list[FailedApproach] = field(default_factory=list)
    alternative_directions: list[str] = field(default_factory=list)
    mechanism: str = ""
    confidence: float = 1.0
    evidence: list[CorrelationEvidence] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    species: str = "通用"

    @property
    def signature(self) -> str:
        """生成反模式的特征签名，用于快速匹配"""
        sorted_traits = sorted(self.trigger_traits)
        raw = f"{self.species}:{','.join(sorted_traits)}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]


# ═══════════════════════════════════════════════════════════════
# 育种目标
# ═══════════════════════════════════════════════════════════════

@dataclass
class TraitTarget:
    """用户对某个性状的育种目标"""
    trait_id: str
    desired_value: float | None = None     # 目标数值
    direction: str = ">="                   # >=, <=, ==, range
    range_min: float | None = None
    range_max: float | None = None
    priority: int = 5                       # 1-10, 10最高
    note: str = ""


@dataclass
class BreedingGoal:
    """
    用户定义的育种目标。

    这是系统的输入：用户说"我想要A、B、C三个性状分别达到什么水平"，
    系统以此为基础做验证。
    """
    name: str
    species: str = "通用"
    targets: list[TraitTarget] = field(default_factory=list)
    context: str = ""                       # 额外的背景描述
    created_at: datetime = field(default_factory=datetime.now)

    def add_target(self, target: TraitTarget) -> None:
        self.targets.append(target)

    def trait_ids(self) -> list[str]:
        return [t.trait_id for t in self.targets]


# ═══════════════════════════════════════════════════════════════
# 验证结果
# ═══════════════════════════════════════════════════════════════

@dataclass
class Violation:
    """一次约束违反的记录"""
    constraint_id: str
    severity: ConstraintSeverity
    title: str
    description: str                    # 问题描述
    mechanism: str                      # 生理机制解释
    narrative: str                      # 可读的"顾问式"叙事
    involved_traits: list[str]
    suggestion: str = ""                # 建议
    source: str = "rule"                # rule / anti_pattern / llm

    def __post_init__(self):
        # 类型安全：确保 severity 不会意外被覆盖为 string
        if isinstance(self.severity, str):
            self.severity = ConstraintSeverity[self.severity.upper()]


@dataclass
class ValidationReport:
    """
    一份完整的育种目标验证报告。

    这是系统的输出——不仅告诉用户通不通过，
    还给出完整的叙事性解释。
    """
    goal: BreedingGoal
    passed: bool = True
    violations: list[Violation] = field(default_factory=list)
    matched_anti_patterns: list[AntiPattern] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    llm_comment: str = ""
    generated_at: datetime = field(default_factory=datetime.now)

    def add_violation(self, v: Violation) -> None:
        self.violations.append(v)
        if v.severity in (ConstraintSeverity.FATAL, ConstraintSeverity.SEVERE):
            self.passed = False

    def summary(self) -> dict:
        """返回报告的摘要字典，便于序列化"""
        return {
            "goal": self.goal.name,
            "passed": self.passed,
            "total_violations": len(self.violations),
            "fatal": sum(1 for v in self.violations if v.severity == ConstraintSeverity.FATAL),
            "severe": sum(1 for v in self.violations if v.severity == ConstraintSeverity.SEVERE),
            "warnings": sum(1 for v in self.violations if v.severity == ConstraintSeverity.WARNING),
            "infos": sum(1 for v in self.violations if v.severity == ConstraintSeverity.INFO),
            "anti_patterns_matched": len(self.matched_anti_patterns),
            "suggestions_count": len(self.suggestions),
        }

    def narrative(self) -> str:
        """生成完整的顾问式叙事报告"""
        lines = [f"# 育种目标验证报告：{self.goal.name}"]
        lines.append(f"物种：{self.goal.species}")
        lines.append(f"结论：{'✅ 可以推进' if self.passed else '❌ 建议重新评估'}")
        lines.append("")

        if self.violations:
            lines.append("## 发现的问题")
            for v in sorted(self.violations, key=lambda x: x.severity.value):
                tag = {
                    ConstraintSeverity.FATAL: "🔴 致命",
                    ConstraintSeverity.SEVERE: "🟠 严重",
                    ConstraintSeverity.WARNING: "🟡 警告",
                    ConstraintSeverity.INFO: "🔵 提示",
                }.get(v.severity, "⚪ 未知")
                lines.append(f"\n### [{tag}] {v.title}")
                lines.append(f"{v.narrative}")

        if self.suggestions:
            lines.append("\n## 建议方向")
            for i, s in enumerate(self.suggestions, 1):
                lines.append(f"{i}. {s}")

        if self.llm_comment:
            lines.append(f"\n## LLM 分析意见\n{self.llm_comment}")

        lines.append("")
        lines.append("---")
        lines.append(f"报告生成时间：{self.generated_at.isoformat()}")
        return "\n".join(lines)

    def to_json(self, indent: int = 2) -> str:
        """序列化为 JSON"""
        def _serialize(obj: Any) -> Any:
            if isinstance(obj, Enum):
                return obj.name
            if isinstance(obj, datetime):
                return obj.isoformat()
            if isinstance(obj, TraitTarget):
                return {
                    "trait_id": obj.trait_id,
                    "desired_value": obj.desired_value,
                    "direction": obj.direction,
                    "range_min": obj.range_min,
                    "range_max": obj.range_max,
                    "priority": obj.priority,
                    "note": obj.note,
                }
            if isinstance(obj, Violation):
                return {
                    "constraint_id": obj.constraint_id,
                    "severity": obj.severity.name,
                    "title": obj.title,
                    "description": obj.description,
                    "mechanism": obj.mechanism,
                    "narrative": obj.narrative,
                    "involved_traits": obj.involved_traits,
                    "suggestion": obj.suggestion,
                    "source": obj.source,
                }
            if isinstance(obj, AntiPattern):
                return {
                    "id": obj.id,
                    "name": obj.name,
                    "description": obj.description,
                    "severity": obj.severity.name,
                    "trigger_traits": obj.trigger_traits,
                    "alternative_directions": obj.alternative_directions,
                }
            if hasattr(obj, "__dataclass_fields__"):
                return {k: _serialize(v) for k, v in obj.__dict__.items()}
            return str(obj)

        return json.dumps(_serialize(self), ensure_ascii=False, indent=indent)
