from bio_logic_debugger.core.domain import BreedingGoal, Trait, TraitTarget
from bio_logic_debugger.core.engine import BioLogicEngine
from bio_logic_debugger.knowledge.weight_store import apply_weights_to_engine


def test_validate_llm_layer_does_not_use_shared_callback():
    engine = BioLogicEngine()
    engine.register_traits([Trait("a", "A", "", "x", "", (0.0, 1.0))])

    def sticky(ctx):
        ctx.llm_comment = "shared"
        return ctx

    engine.set_llm_callback(sticky)
    goal = BreedingGoal(name="t")
    goal.add_target(TraitTarget("a", 0.5, ">="))
    report = engine.validate(goal, llm_layer=None)
    assert report.llm_comment == ""
    report = engine.validate(goal)
    assert report.llm_comment == "shared"


def test_set_confidence_public_api(tmp_path, monkeypatch):
    from bio_logic_debugger.knowledge import weight_store

    monkeypatch.setattr(weight_store, "_weights_path", lambda: tmp_path / "w.json")
    engine = BioLogicEngine()
    engine.register_traits([Trait("t1", "T", "", "x", "", (0.0, 1.0), confidence=1.0)])
    assert engine.set_confidence("traits", "t1", 0.4)
    assert engine.get_trait("t1").confidence == 0.4
    tmp_path.joinpath("w.json").write_text(
        '{"traits": {"t1": 0.2}, "correlations": {}, "constraints": {}}',
        encoding="utf-8",
    )
    apply_weights_to_engine(engine)
    assert engine.get_trait("t1").confidence == 0.2
