from bio_logic_debugger.core.domain import ENVIRONMENT_VAR_IDS
from bio_logic_debugger.core.expr import parse, referenced_ids
from bio_logic_debugger.knowledge.knowledge_store import load_builtin


def test_builtin_constraint_vars_are_declared():
    data = load_builtin()
    trait_ids = {t["id"] for t in data["traits"]}
    allowed = trait_ids | set(ENVIRONMENT_VAR_IDS)
    unknown = []
    for c in data["constraints"]:
        expr = (c.get("condition_expr") or "").strip()
        if not expr:
            continue
        for name in referenced_ids(parse(expr)):
            if name not in allowed:
                unknown.append((c["id"], name))
    assert unknown == []
