from __future__ import annotations

import streamlit as st

from bio_logic_debugger.core.domain import (
    ENVIRONMENT_VARIABLES,
    BreedingGoal,
    ConstraintSeverity,
    TraitTarget,
)
from bio_logic_debugger.core.engine import BioLogicEngine
from bio_logic_debugger.ui.runtime import trait_label


def render(engine: BioLogicEngine) -> None:
    st.title("🎯 育种目标验证")
    st.markdown("设定育种目标，系统会检查拮抗关系、生理约束和已知反模式。")

    col_left, col_right = st.columns([3, 2])

    with col_left:
        st.subheader("目标设定")
        goal_name = st.text_input("育种目标名称", "未命名品种")
        available_traits = engine.trait_ids()
        categories = set(t.category for t in engine.iter_traits())

        if "goal_targets" not in st.session_state:
            st.session_state.goal_targets = []

        with st.container(border=True):
            cat_filter = st.selectbox(
                "分类筛选", ["全部"] + sorted(categories), key="cat_filter"
            )
            filtered = []
            for tid in available_traits:
                trait = engine.get_trait(tid)
                if trait is None:
                    continue
                if cat_filter == "全部" or trait.category == cat_filter:
                    filtered.append(tid)
            trait_id = st.selectbox(
                "性状", filtered,
                format_func=lambda tid: trait_label(engine, tid),
            )
            dir_col, val_col, pri_col = st.columns([1, 2, 1])
            with dir_col:
                direction = st.selectbox("方向", [">=", "<=", "=="], key="direction")
            with val_col:
                desired_value = st.number_input("目标值", value=0.0, step=0.1, format="%.2f")
            with pri_col:
                priority = st.number_input("优先级", min_value=1, max_value=10, value=5)

            if st.button("➕ 添加目标", use_container_width=True):
                st.session_state.goal_targets.append({
                    "trait_id": trait_id,
                    "direction": direction,
                    "value": desired_value,
                    "priority": priority,
                })
                st.rerun()

        if st.session_state.goal_targets:
            st.markdown("**已设定的目标：**")
            for i, tgt in enumerate(st.session_state.goal_targets):
                tname = engine.trait_name(tgt["trait_id"])
                trait = engine.get_trait(tgt["trait_id"])
                range_str = ""
                if trait and trait.typical_range[0] is not None:
                    range_str = f"  typical: {trait.typical_range[0]}~{trait.typical_range[1]}{trait.unit}"
                cols = st.columns([0.1, 0.7, 0.1])
                with cols[0]:
                    st.markdown(f"**{i+1}.**")
                with cols[1]:
                    st.markdown(
                        f"**{tname}**　{tgt['direction']} {tgt['value']}"
                        f"　（优先级 {tgt['priority']}）"
                        f"<span style='color:#888;font-size:0.8em;'>　{range_str}</span>",
                        unsafe_allow_html=True,
                    )
                with cols[2]:
                    if st.button("✕", key=f"del_{i}"):
                        st.session_state.goal_targets.pop(i)
                        st.rerun()

            if st.button("🗑 清空所有", type="secondary"):
                st.session_state.goal_targets = []
                st.rerun()

            st.divider()
            env_values: dict = {}
            with st.expander("🌤 环境条件（可选）"):
                st.caption("约束里的干旱程度 / 温度 / 施氮量在这里填，不填则相关约束跳过。")
                for var in ENVIRONMENT_VARIABLES:
                    if var.value_type == "enum":
                        options = ["（不设）"] + list(var.enum_values)
                        chosen = st.selectbox(var.name, options, key=f"env_{var.id}")
                        if chosen != "（不设）":
                            env_values[var.id] = chosen
                    else:
                        raw = st.text_input(
                            f"{var.name}（{var.unit}）" if var.unit else var.name,
                            value="",
                            key=f"env_{var.id}",
                        )
                        raw = raw.strip()
                        if raw:
                            try:
                                env_values[var.id] = float(raw)
                            except ValueError:
                                st.warning(f"{var.name} 需要数字")

            with st.expander("⚙️ LLM 深度分析（可选）"):
                llm_enabled = st.checkbox("启用 LLM 分析", value=False)
                api_key = st.text_input("API Key", type="password", placeholder="sk-... 或设置 BIO_LLM_API_KEY")
                base_url = st.text_input("Base URL", placeholder="https://api.deepseek.com/v1")
                model = st.text_input("模型名", placeholder="deepseek-chat")

            if st.button("🚀 运行验证", type="primary", use_container_width=True):
                goal = BreedingGoal(
                    name=goal_name,
                    species="水稻",
                    environment=env_values,
                )
                for tgt in st.session_state.goal_targets:
                    goal.add_target(TraitTarget(
                        trait_id=tgt["trait_id"],
                        desired_value=tgt["value"],
                        direction=tgt["direction"],
                        priority=tgt["priority"],
                    ))
                llm_layer = None
                if llm_enabled:
                    from bio_logic_debugger.llm.reasoner import LLMConfig, LLMReasoner
                    reasoner = LLMReasoner(config=LLMConfig.from_ui(
                        api_key=api_key,
                        base_url=base_url,
                        model=model,
                    ))
                    llm_layer = reasoner.as_validation_layer(engine)
                with st.spinner("验证中..."):
                    st.session_state.last_report = engine.validate(
                        goal, llm_layer=llm_layer,
                    )
                st.rerun()

    with col_right:
        st.subheader("验证结果")
        if "last_report" not in st.session_state:
            st.info("左侧设定目标后点击「运行验证」")
        else:
            report = st.session_state.last_report
            verdict = report.verdict()
            if verdict == "可以推进":
                st.success(f"✅ {verdict}")
            elif verdict == "谨慎推进":
                st.warning(f"⚠️ {verdict}")
            else:
                st.error(f"❌ {verdict}")
            summary = report.summary()
            mc1, mc2, mc3, mc4 = st.columns(4)
            mc1.metric("致命", summary["fatal"], border=True)
            mc2.metric("严重", summary["severe"], border=True)
            mc3.metric("警告", summary["warnings"], border=True)
            mc4.metric("提示", summary["infos"], border=True)
            if summary["anti_patterns_matched"]:
                st.markdown(f"⚠️ 匹配到 {summary['anti_patterns_matched']} 个反模式")

    if "last_report" in st.session_state:
        report = st.session_state.last_report
        if report.violations:
            st.subheader("📋 详细问题列表")
            severity_order = {
                ConstraintSeverity.FATAL: 0,
                ConstraintSeverity.SEVERE: 1,
                ConstraintSeverity.WARNING: 2,
                ConstraintSeverity.INFO: 3,
            }
            tag_map = {
                ConstraintSeverity.FATAL: ("🔴", "致命", "#ff4b4b"),
                ConstraintSeverity.SEVERE: ("🟠", "严重", "#ff922b"),
                ConstraintSeverity.WARNING: ("🟡", "警告", "#fcc419"),
                ConstraintSeverity.INFO: ("🔵", "提示", "#339af0"),
            }
            for v in sorted(report.violations, key=lambda x: severity_order.get(x.severity, 99)):
                icon, tag, _color = tag_map.get(v.severity, ("⚪", "未知", "#888"))
                expanded = v.severity in (ConstraintSeverity.FATAL, ConstraintSeverity.SEVERE)
                with st.expander(f"{icon} [{tag}] {v.title}", expanded=expanded):
                    st.markdown(v.description)
                    if v.involved_traits:
                        names = "　".join(f"`{engine.trait_name(tid)}`" for tid in v.involved_traits)
                        st.markdown("**涉及性状：**　" + names)
                    if v.mechanism:
                        st.markdown(f"**机制：** {v.mechanism}")
                    st.markdown("---")
                    st.markdown(v.narrative)
                    if v.suggestion:
                        st.info(f"💡 {v.suggestion}")
        if report.suggestions:
            st.subheader("💡 建议方向")
            for i, s in enumerate(report.suggestions, 1):
                st.markdown(f"{i}. {s}")
        if report.llm_comment:
            st.subheader("🤖 LLM 分析意见")
            st.markdown(report.llm_comment)
