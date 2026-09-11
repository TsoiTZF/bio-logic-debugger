from bio_logic_debugger.knowledge.knowledge_store import (
    correlation_from_dict,
    correlation_to_dict,
    load_and_merge,
    load_builtin,
)
from bio_logic_debugger.knowledge.rice_knowledge import CONSTRAINTS, CORRELATIONS, TRAITS


def test_builtin_json_counts():
    data = load_builtin()
    assert len(data["traits"]) == 40
    assert len(data["correlations"]) == 30
    assert len(data["constraints"]) == 9
    assert len(data["anti_patterns"]) == 7


def test_shim_matches_json():
    assert len(TRAITS) == 40
    assert len(CORRELATIONS) == 30
    assert len(CONSTRAINTS) == 9
    assert CONSTRAINTS[0].condition_expr.startswith("$rice_plant_height")


def test_evidence_roundtrip():
    original = CORRELATIONS[0]
    assert original.evidence
    restored = correlation_from_dict(correlation_to_dict(original))
    assert restored.evidence[0].source == original.evidence[0].source
    assert restored.evidence[0].level == original.evidence[0].level
    assert restored.mechanism == original.mechanism


def test_load_and_merge_from_json():
    traits, correlations, constraints, anti_patterns = load_and_merge()
    assert len(traits) >= 40
    assert len(correlations) >= 1
    ids = {t.id for t in traits}
    assert "rice_yield_per_plant" in ids
