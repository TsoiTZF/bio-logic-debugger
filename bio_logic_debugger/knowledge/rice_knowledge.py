"""
兼容入口。内置水稻知识已迁到 knowledge/builtin/*.json。
模块级常量改为惰性加载，避免 JSON 损坏时 import 即炸。
"""
from bio_logic_debugger.knowledge.knowledge_store import load_builtin_objects

_BUNDLE = None


def _bundle():
    global _BUNDLE
    if _BUNDLE is None:
        _BUNDLE = load_builtin_objects()
    return _BUNDLE


def __getattr__(name: str):
    names = ("TRAITS", "CORRELATIONS", "CONSTRAINTS", "ANTI_PATTERNS")
    if name in names:
        return _bundle()[names.index(name)]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
