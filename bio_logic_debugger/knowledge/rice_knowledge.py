"""
兼容入口。内置水稻知识已迁到 knowledge/builtin/*.json，
这里只做加载，避免再维护一份 Python 常量。
"""
from bio_logic_debugger.knowledge.knowledge_store import load_builtin_objects

TRAITS, CORRELATIONS, CONSTRAINTS, ANTI_PATTERNS = load_builtin_objects()
