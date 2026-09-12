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


def test_community_does_not_override_builtin():
    builtin = {
        "traits": [{"id": "t1", "name": "内置", "description": "", "category": "x"}],
        "correlations": [],
        "constraints": [{"id": "c1", "name": "内置约束", "severity": "FATAL"}],
        "anti_patterns": [],
    }
    community = {
        "traits": [{"id": "t1", "name": "过时社区", "description": "", "category": "x"}],
        "correlations": [],
        "constraints": [{"id": "c1", "name": "过时约束", "severity": "INFO"}],
        "anti_patterns": [],
    }
    merged = merge_knowledge(builtin, community)
    assert merged["traits"][0]["name"] == "内置"
    assert merged["constraints"][0]["name"] == "内置约束"


def test_user_alias_id_rewrites_to_canonical():
    builtin = {
        "traits": [{
            "id": "rice_yield_per_mu",
            "name": "亩产",
            "aliases": ["rice_yield_per_ha"],
        }],
        "correlations": [{
            "trait_a": "rice_yield_per_mu",
            "trait_b": "rice_plant_height",
            "corr_type": "NEGATIVE",
            "strength": -0.4,
        }],
        "constraints": [],
        "anti_patterns": [],
    }
    merged = merge_knowledge(
        builtin,
        {"traits": [], "correlations": [], "constraints": [], "anti_patterns": []},
        user_traits=[{"id": "rice_yield_per_ha", "name": "用户亩产"}],
    )
    assert merged["traits"][0]["id"] == "rice_yield_per_mu"
    assert merged["traits"][0]["name"] == "用户亩产"
    assert "rice_yield_per_ha" in merged["traits"][0]["aliases"]
    assert merged["correlations"][0]["trait_a"] == "rice_yield_per_mu"


def test_community_adds_new_and_skips_alias():
    builtin = {
        "traits": [{
            "id": "rice_yield_per_mu",
            "name": "亩产",
            "aliases": ["rice_yield_per_ha"],
        }],
        "correlations": [],
        "constraints": [],
        "anti_patterns": [],
    }
    community = {
        "traits": [
            {"id": "rice_yield_per_ha", "name": "旧亩产"},
            {"id": "new_trait", "name": "社区新性状"},
        ],
        "correlations": [],
        "constraints": [],
        "anti_patterns": [],
    }
    merged = merge_knowledge(builtin, community)
    ids = [t["id"] for t in merged["traits"]]
    assert ids == ["rice_yield_per_mu", "new_trait"]
