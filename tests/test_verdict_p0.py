from bio_logic_debugger.core.domain import (
    BreedingGoal,
    ConstraintSeverity,
    CorrelationType,
    Trait,
    TraitCorrelation,
    TraitTarget,
)
from bio_logic_debugger.core.engine import BioLogicEngine
from bio_logic_debugger.knowledge.rice_knowledge import ANTI_PATTERNS, CONSTRAINTS, CORRELATIONS, TRAITS


def _rice() -> BioLogicEngine:
    engine = BioLogicEngine()
    engine.register_traits(TRAITS)
    engine.register_correlations(CORRELATIONS)
    engine.register_constraints(CONSTRAINTS)
    engine.register_anti_patterns(ANTI_PATTERNS)
    return engine


def test_yield_components_all_high_is_warning():
    engine = _rice()
    goal = BreedingGoal(name="三要素全高")
    goal.add_target(TraitTarget("rice_panicle_number", 22, ">="))
    goal.add_target(TraitTarget("rice_grain_per_panicle", 300, ">="))
    goal.add_target(TraitTarget("rice_1000_grain_weight", 33, ">="))
    report = engine.validate(goal)
    assert any(v.constraint_id == "rice_yield_components_ceiling" for v in report.violations)
    assert any(p.id == "rice_yield_component_all_max" for p in report.matched_anti_patterns)
    assert report.passed
    assert report.verdict() == "谨慎推进"


def test_drought_warning_does_not_fail_report():
    engine = _rice()
    goal = BreedingGoal(name="高抗遇大旱", environment={"drought_severity": "severe"})
    goal.add_target(TraitTarget("rice_drought_tolerance", 2, "<="))
    report = engine.validate(goal)
    hits = [v for v in report.violations if v.constraint_id == "rice_drought_severe_yield_loss"]
    assert hits and hits[0].severity == ConstraintSeverity.WARNING
    assert report.passed
    assert report.verdict() == "可以推进"


def test_builtin_tall_high_resist_is_fatal_weak_is_not():
    engine = _rice()
    resist = BreedingGoal(name="高秆高抗")
    resist.add_target(TraitTarget("rice_plant_height", 130, ">="))
    resist.add_target(TraitTarget("rice_lodging_resistance", 2, "<="))
    report = engine.validate(resist)
    assert any(v.constraint_id == "rice_not_both_tall_and_lodging_free" for v in report.violations)

    weak = BreedingGoal(name="高秆易倒")
    weak.add_target(TraitTarget("rice_plant_height", 130, ">="))
    weak.add_target(TraitTarget("rice_lodging_resistance", 8, ">="))
    report = engine.validate(weak)
    assert not any(v.constraint_id == "rice_not_both_tall_and_lodging_free" for v in report.violations)


def test_indica_quality_is_not_low_quality_trap():
    engine = _rice()
    goal = BreedingGoal(name="优质籼稻")
    goal.add_target(TraitTarget("rice_yield_per_mu", 650, ">="))
    goal.add_target(TraitTarget("rice_grain_length", 7.5, ">="))
    goal.add_target(TraitTarget("rice_amylose_content", 26, ">="))
    report = engine.validate(goal)
    assert not any(p.id == "rice_high_yield_low_quality" for p in report.matched_anti_patterns)


def test_high_yield_high_chalk_low_milling_hits_trap():
    engine = _rice()
    goal = BreedingGoal(name="高产高垩白低整精米")
    goal.add_target(TraitTarget("rice_yield_per_mu", 800, ">="))
    goal.add_target(TraitTarget("rice_chalkiness", 25, ">="))
    goal.add_target(TraitTarget("rice_head_rice_recovery", 42, "<="))
    report = engine.validate(goal)
    assert any(p.id == "rice_high_yield_low_quality" for p in report.matched_anti_patterns)


def test_late_heading_high_yield_is_not_precocious_trap():
    engine = _rice()
    goal = BreedingGoal(name="晚熟高产")
    goal.add_target(TraitTarget("rice_heading_days", 150, ">="))
    goal.add_target(TraitTarget("rice_yield_per_plant", 50, ">="))
    goal.add_target(TraitTarget("rice_biomass", 16, ">="))
    report = engine.validate(goal)
    assert not any(p.id == "rice_precocious_sacrifice" for p in report.matched_anti_patterns)


def test_early_heading_high_yield_hits_precocious_trap():
    engine = _rice()
    goal = BreedingGoal(name="极早熟高产")
    goal.add_target(TraitTarget("rice_heading_days", 70, "<="))
    goal.add_target(TraitTarget("rice_yield_per_plant", 50, ">="))
    goal.add_target(TraitTarget("rice_biomass", 16, ">="))
    report = engine.validate(goal)
    assert any(p.id == "rice_precocious_sacrifice" for p in report.matched_anti_patterns)


def test_positive_correlation_tailwind_and_coupling():
    engine = BioLogicEngine()
    engine.register_traits([
        Trait("a", "A", "", "产量", "g", (0.0, 100.0)),
        Trait("b", "B", "", "品质", "%", (0.0, 100.0)),
    ])
    engine.register_correlation(TraitCorrelation(
        trait_a="a", trait_b="b",
        corr_type=CorrelationType.POSITIVE,
        strength=0.6, confidence=1.0,
        mechanism="测试正相关",
    ))
    both = BreedingGoal(name="同向")
    both.add_target(TraitTarget("a", 80, ">="))
    both.add_target(TraitTarget("b", 80, ">="))
    report = engine.validate(both)
    hits = [v for v in report.violations if v.constraint_id.startswith("corr_pos.")]
    assert hits and hits[0].severity == ConstraintSeverity.INFO
    assert "联动" in hits[0].title

    mixed = BreedingGoal(name="一优一劣")
    mixed.add_target(TraitTarget("a", 80, ">="))
    mixed.add_target(TraitTarget("b", 20, "<="))
    report = engine.validate(mixed)
    hits = [v for v in report.violations if v.constraint_id.startswith("corr_pos.")]
    assert hits and "顺风" in hits[0].title


def test_correlation_respects_confidence_weight():
    engine = BioLogicEngine()
    engine.register_traits([
        Trait("a", "A", "", "产量", "g", (0.0, 100.0)),
        Trait("b", "B", "", "品质", "%", (0.0, 100.0)),
    ])
    engine.register_correlation(TraitCorrelation(
        trait_a="a", trait_b="b",
        corr_type=CorrelationType.NEGATIVE,
        strength=-0.8, confidence=0.1,
        mechanism="低置信",
    ))
    goal = BreedingGoal(name="双高低权")
    goal.add_target(TraitTarget("a", 80, ">="))
    goal.add_target(TraitTarget("b", 80, ">="))
    report = engine.validate(goal)
    assert not any(v.constraint_id.startswith("corr.") for v in report.violations)

    engine.register_correlation(TraitCorrelation(
        trait_a="a", trait_b="b",
        corr_type=CorrelationType.NEGATIVE,
        strength=-0.8, confidence=1.0,
        mechanism="高置信",
    ))
    report = engine.validate(goal)
    assert any(v.constraint_id.startswith("corr.") for v in report.violations)
    assert all(v.severity == ConstraintSeverity.WARNING for v in report.violations if v.constraint_id.startswith("corr."))
