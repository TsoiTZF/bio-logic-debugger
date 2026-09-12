from bio_logic_debugger.knowledge.weight_store import merge_slider_overrides


def test_merge_keeps_disk_when_slider_missing():
    stored = {"traits": {"a": 0.4}, "correlations": {"x": 0.3}, "constraints": {"c": 0.2}}
    merged = merge_slider_overrides(stored, {"other": 1})
    assert merged["traits"]["a"] == 0.4
    assert merged["correlations"]["x"] == 0.3
    assert merged["constraints"]["c"] == 0.2


def test_merge_overlays_rendered_sliders():
    stored = {"traits": {"a": 0.4, "b": 0.5}, "correlations": {}, "constraints": {}}
    session = {"wt_trait_a": 0.8, "wt_trait_b": 1.0, "wt_cstr_z": 0.1}
    merged = merge_slider_overrides(stored, session)
    assert merged["traits"]["a"] == 0.8
    assert "b" not in merged["traits"]
    assert merged["constraints"]["z"] == 0.1
