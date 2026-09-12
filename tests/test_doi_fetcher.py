from bio_logic_debugger.knowledge.doi_fetcher import _parse_crossref_item


def test_parse_crossref_item_fields():
    parsed = _parse_crossref_item({
        "title": ["A rice paper"],
        "author": [{"given": "Wei", "family": "Xue"}],
        "DOI": "10.1038/ng.143",
        "container-title": ["Nature Genetics"],
        "published-print": {"date-parts": [[2008, 5, 4]]},
        "abstract": "Ghd7",
    })
    assert parsed["title"] == "A rice paper"
    assert parsed["authors"] == ["Wei Xue"]
    assert parsed["doi"] == "10.1038/ng.143"
    assert parsed["journal"] == "Nature Genetics"
    assert parsed["year"] == 2008
    assert parsed["abstract"] == "Ghd7"


def test_parse_crossref_item_missing_title():
    parsed = _parse_crossref_item({})
    assert parsed["title"] == "未知标题"
    assert parsed["year"] == 0
    assert parsed["authors"] == []
