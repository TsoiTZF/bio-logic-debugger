from bio_logic_debugger.core.domain import (
    AntiPattern,
    BiologicalConstraint,
    BreedingGoal,
    ConstraintSeverity,
    CorrelationType,
    Trait,
    TraitCorrelation,
    TraitTarget,
)
from bio_logic_debugger.core.engine import BioLogicEngine


def _engine() -> BioLogicEngine:
    engine = BioLogicEngine()
    engine.register_traits([
        Trait("rice_yield_per_plant", "单株产量", "", "产量", "g", (10.0, 80.0)),
        Trait("rice_amylose_content", "直链淀粉含量", "", "品质", "%", (0.0, 33.0)),
        Trait("rice_plant_height", "株高", "", "株型", "cm", (60.0, 150.0)),
        Trait("rice_lodging_resistance", "抗倒伏性", "", "抗逆", "级", (1.0, 9.0), higher_is_better=False),
        Trait("rice_heading_days", "抽穗天数", "", "生育期", "天", (60.0, 180.0)),
        Trait("rice_gel_consistency", "胶稠度", "", "品质", "mm", (26.0, 100.0)),
    ])
    engine.register_correlation(TraitCorrelation(
        trait_a="rice_yield_per_plant",
        trait_b="rice_amylose_content",
        corr_type=CorrelationType.NEGATIVE,
        strength=-0.8,
        confidence=1.0,
        mechanism="测试用强负相关",
    ))
    engine.register_constraint(BiologicalConstraint(
        id="rice_not_both_tall_and_lodging_free",
        name="株高与抗倒伏的不可兼得",
        description="高度超过 120cm 且高抗倒伏",
        severity=ConstraintSeverity.FATAL,
        condition_expr="$rice_plant_height > 120 AND $rice_lodging_resistance <= 3",
        confidence=0.9,
    ))
    engine.register_constraint(BiologicalConstraint(
        id="rice_extreme_precocity",
        name="极端早熟的生育期下限",
        description="抽穗天数过短",
        severity=ConstraintSeverity.FATAL,
        condition_expr="$rice_heading_days < 65",
        confidence=0.9,
    ))
    engine.register_anti_pattern(AntiPattern(
        id="ap_yield_quality",
        name="高产低质陷阱",
        description="测试反模式",
        trigger_traits=["rice_yield_per_plant", "rice_amylose_content"],
        severity=ConstraintSeverity.SEVERE,
        confidence=1.0,
    ))
    return engine


def test_range_violation():
    engine = _engine()
    goal = BreedingGoal(name="超范围", species="水稻")
    goal.add_target(TraitTarget("rice_yield_per_plant", desired_value=200, direction=">="))
    report = engine.validate(goal)
    ids = [v.constraint_id for v in report.violations]
    assert "range_check.rice_yield_per_plant" in ids


def test_unknown_trait_is_suggestion_not_crash():
    engine = _engine()
    goal = BreedingGoal(name="未知", species="水稻")
    goal.add_target(TraitTarget("not_a_real_trait", desired_value=1, direction=">="))
    report = engine.validate(goal)
    assert report.passed
    assert any("不在当前知识库" in s for s in report.suggestions)


def test_antagonistic_both_high_is_warning_not_fatal():
    engine = _engine()
    goal = BreedingGoal(name="双高", species="水稻")
    goal.add_target(TraitTarget("rice_yield_per_plant", desired_value=50, direction=">="))
    goal.add_target(TraitTarget("rice_amylose_content", desired_value=28, direction=">="))
    report = engine.validate(goal)
    corrs = [v for v in report.violations if v.constraint_id.startswith("corr.")]
    assert corrs
    assert all(v.severity == ConstraintSeverity.WARNING for v in corrs)
    assert all("达成率" not in v.narrative for v in corrs)
    # 反模式仍可能是 SEVERE，相关层自己不得再标 FATAL


def test_midrange_plus_is_not_chasing_high():
    engine = _engine()
    goal = BreedingGoal(name="中低产", species="水稻")
    goal.add_target(TraitTarget("rice_yield_per_plant", desired_value=20, direction=">="))
    goal.add_target(TraitTarget("rice_amylose_content", desired_value=28, direction=">="))
    report = engine.validate(goal)
    assert not any(v.constraint_id.startswith("corr.") for v in report.violations)


def test_range_direction_is_not_automatically_high():
    engine = _engine()
    goal = BreedingGoal(name="区间", species="水稻")
    goal.add_target(TraitTarget(
        "rice_yield_per_plant", direction="range", range_min=1, range_max=2,
    ))
    goal.add_target(TraitTarget(
        "rice_amylose_content", direction="range", range_min=1, range_max=2,
    ))
    report = engine.validate(goal)
    assert not any(v.constraint_id.startswith("corr.") for v in report.violations)


def test_constraint_fires_only_when_condition_holds():
    engine = _engine()
    # SES：1 抗 9 感。高秆+真高抗（≤3）才是 FATAL；高秆+易倒（≥7）不触发。
    tall_resist = BreedingGoal(name="高秆高抗", species="水稻")
    tall_resist.add_target(TraitTarget("rice_plant_height", desired_value=130, direction=">="))
    tall_resist.add_target(TraitTarget("rice_lodging_resistance", desired_value=2, direction="<="))
    report = engine.validate(tall_resist)
    assert any(v.constraint_id == "rice_not_both_tall_and_lodging_free" for v in report.violations)

    tall_weak = BreedingGoal(name="高秆易倒", species="水稻")
    tall_weak.add_target(TraitTarget("rice_plant_height", desired_value=130, direction=">="))
    tall_weak.add_target(TraitTarget("rice_lodging_resistance", desired_value=8, direction=">="))
    report = engine.validate(tall_weak)
    assert not any(v.constraint_id == "rice_not_both_tall_and_lodging_free" for v in report.violations)

    only_tall = BreedingGoal(name="只高", species="水稻")
    only_tall.add_target(TraitTarget("rice_plant_height", desired_value=130, direction=">="))
    report = engine.validate(only_tall)
    assert not any(v.constraint_id == "rice_not_both_tall_and_lodging_free" for v in report.violations)


def test_constraint_numeric_threshold():
    engine = _engine()
    early = BreedingGoal(name="过早", species="水稻")
    early.add_target(TraitTarget("rice_heading_days", desired_value=50, direction="<="))
    report = engine.validate(early)
    assert any(v.constraint_id == "rice_extreme_precocity" for v in report.violations)

    normal = BreedingGoal(name="正常抽穗", species="水稻")
    normal.add_target(TraitTarget("rice_heading_days", desired_value=90, direction=">="))
    report = engine.validate(normal)
    assert not any(v.constraint_id == "rice_extreme_precocity" for v in report.violations)


def test_builtin_heading_constraint_uses_real_expr():
    from bio_logic_debugger.knowledge.rice_knowledge import CONSTRAINTS, TRAITS

    engine = BioLogicEngine()
    engine.register_traits(TRAITS)
    engine.register_constraints(CONSTRAINTS)
    too_early = BreedingGoal(name="过早", species="水稻")
    too_early.add_target(TraitTarget("rice_heading_days", desired_value=50, direction="<="))
    report = engine.validate(too_early)
    assert any(v.constraint_id == "rice_extreme_precocity" for v in report.violations)

    # 旧实现只要目标里出现抽穗天数就会误报；90 天不应触发 < 65
    ok = BreedingGoal(name="正常", species="水稻")
    ok.add_target(TraitTarget("rice_heading_days", desired_value=90, direction=">="))
    report = engine.validate(ok)
    assert not any(v.constraint_id == "rice_extreme_precocity" for v in report.violations)


def test_constraint_interval_does_not_fire_when_goal_only_may_cross():
    engine = _engine()
    goal = BreedingGoal(name="抽穗下界50", species="水稻")
    goal.add_target(TraitTarget("rice_heading_days", desired_value=50, direction=">="))
    report = engine.validate(goal)
    assert not any(v.constraint_id == "rice_extreme_precocity" for v in report.violations)


def test_environment_binds_constraint():
    engine = _engine()
    engine.register_constraint(BiologicalConstraint(
        id="env_demo",
        name="干旱环境",
        description="",
        severity=ConstraintSeverity.WARNING,
        condition_expr="$drought_severity = 'severe'",
        confidence=1.0,
    ))
    goal = BreedingGoal(name="旱", species="水稻", environment={"drought_severity": "severe"})
    goal.add_target(TraitTarget("rice_yield_per_plant", desired_value=50, direction=">="))
    report = engine.validate(goal)
    assert any(v.constraint_id == "env_demo" for v in report.violations)


def test_anti_pattern_exact_match():
    engine = _engine()
    goal = BreedingGoal(name="高产低质", species="水稻")
    goal.add_target(TraitTarget("rice_yield_per_plant", desired_value=50, direction=">="))
    goal.add_target(TraitTarget("rice_amylose_content", desired_value=10, direction="<="))
    report = engine.validate(goal)
    assert any(p.id == "ap_yield_quality" for p in report.matched_anti_patterns)
