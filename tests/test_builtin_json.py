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
    assert len(data["constraints"]) == 10
    assert len(data["anti_patterns"]) == 8


def test_shim_matches_json():
    assert len(TRAITS) == 40
    assert len(CORRELATIONS) == 30
    assert len(CONSTRAINTS) == 10
    assert CONSTRAINTS[0].condition_expr.startswith("$rice_plant_height")


def test_evidence_roundtrip():
    original = CORRELATIONS[0]
    assert original.evidence
    restored = correlation_from_dict(correlation_to_dict(original))
    assert restored.evidence[0].source == original.evidence[0].source
    assert restored.evidence[0].level == original.evidence[0].level
    assert restored.mechanism == original.mechanism


def test_every_trait_declares_higher_is_better():
    data = load_builtin()
    missing = [t["id"] for t in data["traits"] if "higher_is_better" not in t]
    assert missing == []
    by_id = {t["id"]: t["higher_is_better"] for t in data["traits"]}
    assert by_id["rice_chalkiness"] is False
    assert by_id["rice_protein_content"] is False
    assert by_id["rice_leaf_angle"] is False
    assert by_id["rice_lodging_resistance"] is False
    assert by_id["rice_yield_per_mu"] is True


def test_confirmed_evidence_has_url():
    data = load_builtin()
    missing = []
    for key in ("correlations", "constraints", "anti_patterns"):
        for item in data[key]:
            for e in item.get("evidence") or []:
                if str(e.get("level", "")).upper() == "CONFIRMED" and not (e.get("url") or "").strip():
                    missing.append((key, item.get("id") or (item.get("trait_a"), item.get("trait_b")), e.get("source")))
    assert missing == []


def test_gene_papers_not_used_as_correlation_r():
    data = load_builtin()
    for item in data["correlations"]:
        pair = {item.get("trait_a"), item.get("trait_b")}
        for e in item.get("evidence") or []:
            url = e.get("url") or ""
            if pair == {"rice_yield_per_mu", "rice_chalkiness"}:
                assert "ng.2923" not in url
            if pair == {"rice_yield_per_plant", "rice_grain_length"}:
                assert "s00122-006-0218-1" not in url


def test_load_and_merge_from_json():
    traits, correlations, constraints, anti_patterns = load_and_merge()
    assert len(traits) >= 40
    assert len(correlations) >= 1
    ids = {t.id for t in traits}
    assert "rice_yield_per_plant" in ids
