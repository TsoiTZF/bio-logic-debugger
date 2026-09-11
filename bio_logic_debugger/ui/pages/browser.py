from __future__ import annotations

import streamlit as st

from bio_logic_debugger.core.domain import CorrelationType
from bio_logic_debugger.core.engine import BioLogicEngine


def render(engine: BioLogicEngine) -> None:
    st.title("🔬 性状浏览器")
    st.markdown("浏览所有可用性状及其关联关系。")

    categories = sorted(set(t.category for t in engine.iter_traits()))
    selected_cat = st.selectbox("按分类筛选", ["全部"] + categories)
    traits_to_show = [
        t for t in engine.iter_traits()
        if selected_cat == "全部" or t.category == selected_cat
    ]
    by_cat: dict[str, list] = {}
    for t in traits_to_show:
        by_cat.setdefault(t.category, []).append(t)

    correlations = engine.iter_correlations()
    for cat, ts in sorted(by_cat.items()):
        st.subheader(f"📁 {cat}")
        cols = st.columns(3)
        for i, t in enumerate(sorted(ts, key=lambda x: x.id)):
            with cols[i % 3]:
                with st.container(border=True):
                    st.markdown(f"**{t.name}**")
                    st.caption(f"`{t.id}`")
                    if t.typical_range[0] is not None:
                        st.markdown(
                            f"范围：**{t.typical_range[0]} ~ {t.typical_range[1]}** {t.unit}"
                        )
                    else:
                        st.markdown(f"单位：{t.unit}")
                    st.caption(t.description)
                    related = [c for c in correlations if t.id in (c.trait_a, c.trait_b)]
                    if related:
                        with st.expander(f"关联 ({len(related)})"):
                            for c in related:
                                other = c.trait_b if c.trait_a == t.id else c.trait_a
                                other_name = engine.trait_name(other)
                                tag = (
                                    "🔴 拮抗" if c.is_antagonistic()
                                    else "🟡 权衡" if c.corr_type == CorrelationType.TRADE_OFF
                                    else "🟢 正相关" if c.corr_type == CorrelationType.POSITIVE
                                    else "🔵 相关"
                                )
                                st.markdown(f"{tag} **{other_name}**　(r={c.strength})")
                                mech = c.mechanism[:80] + "..." if len(c.mechanism) > 80 else c.mechanism
                                st.caption(mech)
