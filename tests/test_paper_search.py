from types import SimpleNamespace

from bio_logic_debugger.knowledge.paper_search import extract_keywords_from_knowledge


def test_keywords_are_english():
    traits = [
        SimpleNamespace(id="rice_yield_per_mu", name="亩产", category="产量", tags=["产量"]),
        SimpleNamespace(id="rice_chalkiness", name="垩白度", category="品质", tags=["品质"]),
        SimpleNamespace(id="rice_heading_days", name="抽穗天数", category="生育期", tags=[]),
    ]
    keys = extract_keywords_from_knowledge(traits, max_keywords=10)
    assert keys
    assert all(not any("\u4e00" <= ch <= "\u9fff" for ch in k) for k in keys)
    assert "rice grain yield" in keys
    assert "rice chalkiness" in keys
    assert "rice heading date" in keys
