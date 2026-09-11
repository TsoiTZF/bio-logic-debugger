from __future__ import annotations

import streamlit as st

from bio_logic_debugger.core.domain import ConstraintSeverity
from bio_logic_debugger.core.engine import BioLogicEngine


def render(engine: BioLogicEngine) -> None:
    st.title("📚 反模式库")
    st.markdown("历史上反复验证的育种死胡同。")
    severity_filter = st.selectbox("按等级筛选", ["全部", "严重", "警告", "提示"])

    tag_map = {
        ConstraintSeverity.FATAL: ("🔴", "致命"),
        ConstraintSeverity.SEVERE: ("🟠", "严重"),
        ConstraintSeverity.WARNING: ("🟡", "警告"),
        ConstraintSeverity.INFO: ("🔵", "提示"),
    }
    for ap in engine.iter_anti_patterns():
        if severity_filter == "严重" and ap.severity not in (
            ConstraintSeverity.SEVERE, ConstraintSeverity.FATAL
        ):
            continue
        if severity_filter == "警告" and ap.severity != ConstraintSeverity.WARNING:
            continue
        icon, tag = tag_map.get(ap.severity, ("⚪", ""))
        with st.expander(f"{icon} **[{tag}] {ap.name}**"):
            st.markdown(ap.description)
            names = "　".join(f"`{engine.trait_name(t)}`" for t in ap.trigger_traits)
            st.markdown("**触发性状：**　" + names)
            if ap.mechanism:
                st.markdown(f"**生理机制：** {ap.mechanism}")
            if ap.historical_examples:
                st.markdown("**历史案例：**")
                for ex in ap.historical_examples:
                    st.markdown(f"- {ex}")
            if ap.failed_approaches:
                st.markdown("**失败的尝试：**")
                for fa in ap.failed_approaches:
                    st.markdown(f"- {fa.description} —— _{fa.reason_failed}_")
            if ap.alternative_directions:
                st.success("**推荐的替代方向：**")
                for i, alt in enumerate(ap.alternative_directions, 1):
                    st.markdown(f"{i}. {alt}")
            st.caption(f"置信度：{ap.confidence:.0%}")
