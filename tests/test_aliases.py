from bio_logic_debugger.core.domain import BreedingGoal, CorrelationType, TraitCorrelation, TraitTarget
from bio_logic_debugger.core.engine import BioLogicEngine
from bio_logic_debugger.knowledge.rice_knowledge import TRAITS, CORRELATIONS, CONSTRAINTS


def test_legacy_yield_id_resolves():
    engine = BioLogicEngine()
    engine.register_traits(TRAITS)
    engine.register_correlations(CORRELATIONS)
    engine.register_constraints(CONSTRAINTS)
    t = engine.get_trait("rice_yield_per_ha")
    assert t is not None
    assert t.id == "rice_yield_per_mu"
    assert "rice_yield_per_ha" in t.aliases
    assert engine.trait_ids().count("rice_yield_per_mu") == 1
    assert "rice_yield_per_ha" not in engine.trait_ids()

    goal = BreedingGoal(name="旧id")
    goal.add_target(TraitTarget("rice_yield_per_ha", desired_value=400, direction=">="))
    engine.validate(goal)
    assert goal.targets[0].trait_id == "rice_yield_per_ha"


def test_batch_register_canonicalizes_alias():
    engine = BioLogicEngine()
    engine.register_traits(TRAITS)
    engine.register_correlations([
        TraitCorrelation(
            trait_a="rice_yield_per_ha",
            trait_b="rice_chalkiness",
            corr_type=CorrelationType.POSITIVE,
            strength=0.3,
            confidence=1.0,
        )
    ])
    pairs = {(c.trait_a, c.trait_b) for c in engine.iter_correlations()}
    assert ("rice_yield_per_mu", "rice_chalkiness") in pairs
    assert all("rice_yield_per_ha" not in pair for pair in pairs)


def test_some_evidence_has_real_urls():
    engine = BioLogicEngine()
    engine.register_correlations(CORRELATIONS)
    urls = [
        e.url
        for c in engine.iter_correlations()
        for e in c.evidence
        if e.url
    ]
    assert any("doi.org/10.1016/j.fcr.2008.04.001" in u for u in urls)
    assert any("doi.org/10.1038/ng.2923" in u or "doi.org/10.1038/ng.143" in u for u in urls)
