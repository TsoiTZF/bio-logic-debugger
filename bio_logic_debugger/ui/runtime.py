"""引擎缓存、侧边栏、启动同步。"""
from __future__ import annotations

import streamlit as st

from bio_logic_debugger import __version__
from bio_logic_debugger.core.engine import BioLogicEngine
from bio_logic_debugger.knowledge import knowledge_store
from bio_logic_debugger.knowledge.knowledge_store import load_and_merge
from bio_logic_debugger.knowledge.weight_store import apply_weights_to_engine


@st.cache_resource
def get_engine() -> BioLogicEngine:
    engine = BioLogicEngine()
    try:
        traits, correlations, constraints, anti_patterns = load_and_merge()
        engine.register_traits(traits)
        engine.register_correlations(correlations)
        engine.register_constraints(constraints)
        engine.register_anti_patterns(anti_patterns)
    except Exception as e:
        from bio_logic_debugger.knowledge.rice_knowledge import (
            ANTI_PATTERNS as BUILTIN_AP,
            CONSTRAINTS as BUILTIN_CONS,
            CORRELATIONS as BUILTIN_CORRS,
            TRAITS as BUILTIN_TRAITS,
        )
        engine.register_traits(BUILTIN_TRAITS)
        engine.register_correlations(BUILTIN_CORRS)
        engine.register_constraints(BUILTIN_CONS)
        engine.register_anti_patterns(BUILTIN_AP)
        st.warning(f"知识库合并失败，使用内置兜底: {e}")
    try:
        apply_weights_to_engine(engine)
    except Exception:
        pass
    return engine


def trait_label(engine: BioLogicEngine, trait_id: str) -> str:
    t = engine.get_trait(trait_id)
    if not t:
        return trait_id
    label = t.name
    if t.typical_range[0] is not None:
        label += f"  ({t.typical_range[0]}~{t.typical_range[1]}{t.unit})"
    return label


def boot() -> None:
    if "_sync_done" not in st.session_state:
        try:
            st.session_state._sync_result = knowledge_store.sync_from_community()
            st.session_state._sync_done = True
        except Exception:
            st.session_state._sync_result = False
            st.session_state._sync_done = True

    if st.session_state.get("_sync_result") and st.session_state.get("_sync_done"):
        if "_notified" not in st.session_state:
            st.session_state._notified = True
            community_traits = len(knowledge_store.load_community().get("traits", []))
            if community_traits > 0:
                st.toast(f"🌾 社区知识库已同步（{community_traits} 个性状）", icon="📦")
            col_bar, col_btn = st.columns([3, 1])
            with col_bar:
                st.info("📦 社区知识库已更新 — 点击右侧按钮重新加载引擎", icon="ℹ️")
            with col_btn:
                if st.button("🔄 重新加载引擎", use_container_width=True, type="primary"):
                    st.cache_resource.clear()
                    st.session_state._sync_result = False
                    st.rerun()

    if "_version_notified" not in st.session_state:
        st.session_state._version_notified = True
        st.toast(f"当前版本 v{__version__}", icon="✨")


def render_sidebar(engine: BioLogicEngine) -> str:
    st.sidebar.markdown(
        "<h1 style='font-size: 1.5rem;'>🌾 让邺城燃烧</h1>",
        unsafe_allow_html=True,
    )
    st.sidebar.markdown("**Bio-Logic Debugger**")
    st.sidebar.caption(f"v{__version__}")
    st.sidebar.markdown("---")

    page = st.sidebar.radio(
        "导航",
        ["育种目标验证", "性状浏览器", "反模式库", "约束规则", "📚 文献与知识库"],
        label_visibility="collapsed",
    )

    st.sidebar.markdown("---")
    st.sidebar.caption("用生物学逻辑在播种前筛掉注定失败的育种方向。")
    st.sidebar.caption("⚠️ 当前运行在本地网络，仅建议在受信任的内网使用。")

    st.sidebar.markdown("---")
    st.sidebar.caption("📦 知识库状态")
    with st.sidebar:
        trait_count = len(list(engine.iter_traits()))
        corr_count = len(engine.iter_correlations())
        ap_count = len(engine.iter_anti_patterns())
        last_sync = knowledge_store.get_last_sync_time()
        has_community = knowledge_store.has_community_data()

        st.caption("✅ 已同步" if has_community else "⚪ 内置模式（未同步）")
        st.caption(f"同步于 {last_sync}" if last_sync else "从未同步")
        st.caption(f"性状 {trait_count} / 关联 {corr_count} / 反模式 {ap_count}")
        try:
            from bio_logic_debugger.knowledge.paper_search import load_seen_papers
            st.caption(f"已检索 {len(load_seen_papers())} 篇论文")
        except Exception:
            pass

        if st.button("🔄 检查更新", use_container_width=True, key="sidebar_sync"):
            with st.spinner("检查社区知识库..."):
                ok = knowledge_store.sync_from_community()
                if ok:
                    st.cache_resource.clear()
                    st.toast("✅ 社区知识库已更新，引擎已重新加载", icon="📦")
                    st.rerun()
                else:
                    st.toast("⚠️ 同步失败，请检查网络", icon="⚠️")
    return page
