from __future__ import annotations

import streamlit as st

from bio_logic_debugger.core.domain import ConstraintSeverity
from bio_logic_debugger.core.engine import BioLogicEngine


def render(engine: BioLogicEngine) -> None:
    st.title("📜 生物学约束规则")
    st.markdown(
        "FATAL：生理极限。SEVERE：极难突破。WARNING：已知冲突，可能缓解。"
    )
    tag_map = {
        ConstraintSeverity.FATAL: ("🔴", "致命"),
        ConstraintSeverity.SEVERE: ("🟠", "严重"),
        ConstraintSeverity.WARNING: ("🟡", "警告"),
        ConstraintSeverity.INFO: ("🔵", "提示"),
    }
    for constraint in engine.iter_constraints():
        icon, tag = tag_map.get(constraint.severity, ("⚪", ""))
        with st.container(border=True):
            cols = st.columns([0.05, 1])
            with cols[0]:
                st.markdown(f"**{icon}**")
            with cols[1]:
                st.markdown(f"**[{tag}] {constraint.name}**")
                st.markdown(constraint.description)
                st.markdown(f"适用范围：`{constraint.scope.name}` / {constraint.species}")
                if constraint.consequence:
                    st.markdown(f"后果：_{constraint.consequence}_")
                if constraint.condition_expr:
                    st.code(constraint.condition_expr, language="text")
                st.caption(f"置信度：{constraint.confidence:.0%}")
