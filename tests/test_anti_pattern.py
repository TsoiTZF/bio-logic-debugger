from bio_logic_debugger.core.anti_pattern import AntiPatternMatcher
from bio_logic_debugger.core.domain import AntiPattern, BreedingGoal, TraitTarget


def _matcher() -> AntiPatternMatcher:
    return AntiPatternMatcher([
        AntiPattern(
            id="ap_yield_quality",
            name="高产低质",
            description="",
            trigger_traits=["rice_yield_per_plant", "rice_amylose_content"],
            confidence=1.0,
        )
    ])


def test_exact_match_with_extra_traits_still_hits():
    m = _matcher()
    goal = BreedingGoal(name="多性状")
    goal.add_target(TraitTarget("rice_yield_per_plant", 50, ">="))
    goal.add_target(TraitTarget("rice_amylose_content", 10, "<="))
    goal.add_target(TraitTarget("rice_plant_height", 90, "<="))
    hits = m.match(goal)
    exact = [h for h in hits if h.anti_pattern.id == "ap_yield_quality"]
    assert exact
    assert exact[0].match_type == "exact"
    assert exact[0].score == 1.0
