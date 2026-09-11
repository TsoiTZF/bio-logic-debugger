from bio_logic_debugger.knowledge.knowledge_store import merge_knowledge


def test_user_overrides_community_and_builtin():
    builtin = {
        "traits": [{"id": "t1", "name": "内置", "description": "", "category": "x"}],
        "correlations": [],
        "constraints": [],
        "anti_patterns": [],
    }
    community = {
        "traits": [{"id": "t1", "name": "社区", "description": "", "category": "x"}],
        "correlations": [],
        "constraints": [],
        "anti_patterns": [],
    }
    merged = merge_knowledge(
        builtin,
        community,
        user_traits=[{"id": "t1", "name": "用户", "description": "", "category": "x"}],
    )
    assert len(merged["traits"]) == 1
    assert merged["traits"][0]["name"] == "用户"


def test_community_overrides_builtin_when_no_user():
    builtin = {
        "traits": [{"id": "t1", "name": "内置", "description": "", "category": "x"}],
        "correlations": [],
        "constraints": [],
        "anti_patterns": [],
    }
    community = {
        "traits": [{"id": "t1", "name": "社区", "description": "", "category": "x"}],
        "correlations": [],
        "constraints": [],
        "anti_patterns": [],
    }
    merged = merge_knowledge(builtin, community)
    assert merged["traits"][0]["name"] == "社区"
