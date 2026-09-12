from bio_logic_debugger.knowledge.paper_analyzer import (
    ExtractedItem,
    _chunk_text,
    _parse_llm_json,
    _rule_extract,
    items_to_constraints,
    items_to_traits,
    name_to_id,
)


def test_extracted_item_defaults_unselected():
    item = ExtractedItem(item_type="trait", data={"name": "x"})
    assert item.selected is False


def test_rule_extract_needs_trait_name_near_range():
    bare = _rule_extract("产量介于 10~20 g 之间")
    # 「产量」只有 2 字，PATTERN_TRAIT_NAME 要 含量/长度等后缀
    named = _rule_extract("株高性状为 90~120 cm")
    assert not any(i.item_type == "trait" and "未知性状" in i.data.get("name", "") for i in bare)
    assert any(i.item_type == "trait" and "株高" in i.data.get("name", "") for i in named)


def test_name_to_id_rejects_unknown_and_short_fuzzy():
    traits = [{"id": "rice_yield_per_plant", "name": "单株产量"}]
    assert name_to_id("未知性状（g）", traits) is None
    assert name_to_id("产量", traits) != "rice_yield_per_plant"
    assert name_to_id("单株产量", traits) == "rice_yield_per_plant"
    assert name_to_id("全新性状甲", traits).startswith("extracted_")


def test_items_to_traits_does_not_overwrite_known():
    known = [{"id": "rice_yield_per_mu", "name": "亩产", "aliases": ["rice_yield_per_ha"]}]
    items = [
        ExtractedItem(item_type="trait", data={"name": "亩产", "range": [1, 2], "unit": "kg"}),
        ExtractedItem(item_type="trait", data={"name": "新穗型指数", "range": [1, 2], "unit": ""}),
    ]
    out = items_to_traits(items, known)
    assert all(d["id"] != "rice_yield_per_mu" for d in out)
    assert any(d["name"] == "新穗型指数" for d in out)


def test_items_to_traits_skips_unknown():
    items = [
        ExtractedItem(item_type="trait", data={"name": "未知性状（g）", "range": [1, 2], "unit": "g"}),
        ExtractedItem(item_type="trait", data={"name": "穗粒数", "range": [80, 200], "unit": "粒"}),
    ]
    out = items_to_traits(items)
    assert all(not d["name"].startswith("未知") for d in out)
    assert any(d["name"] == "穗粒数" for d in out)


def test_items_to_constraints_skip_empty_and_cap_fatal():
    items = [
        ExtractedItem(item_type="constraint", data={"name": "空条件", "condition": "", "severity": "FATAL"}),
        ExtractedItem(
            item_type="constraint",
            data={"name": "有条件", "condition": "$a > 1", "severity": "FATAL"},
        ),
    ]
    out = items_to_constraints(items)
    assert len(out) == 1
    assert out[0]["condition_expr"] == "$a > 1"
    assert out[0]["severity"] == "WARNING"


def test_chunk_and_llm_json():
    chunks = _chunk_text("abcdefghij" * 800, size=100, overlap=20)
    assert len(chunks) > 1
    data = _parse_llm_json('```json\n{"traits": []}\n```')
    assert data == {"traits": []}
