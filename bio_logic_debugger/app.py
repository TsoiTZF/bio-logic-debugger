#!/usr/bin/env python3
"""
让邺城燃烧 — Bio-Logic Debugger Web UI (Streamlit)
"""
from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st

from bio_logic_debugger.core.domain import (
    AntiPattern,
    BreedingGoal,
    ConstraintSeverity,
    CorrelationType,
    TraitTarget,
)
from bio_logic_debugger.core.engine import BioLogicEngine
from bio_logic_debugger.knowledge.rice_knowledge import (
    ANTI_PATTERNS,
    CONSTRAINTS,
    CORRELATIONS,
    TRAITS,
)

st.set_page_config(
    page_title="让邺城燃烧 — Bio-Logic Debugger",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── 初始化引擎 ──────────────────────────────────────────────


@st.cache_resource
def get_engine() -> BioLogicEngine:
    engine = BioLogicEngine()
    engine.register_traits(TRAITS)
    engine.register_correlations(CORRELATIONS)
    engine.register_constraints(CONSTRAINTS)
    engine.register_anti_patterns(ANTI_PATTERNS)
    return engine


engine = get_engine()


def trait_label(trait_id: str) -> str:
    """生成性状选择器上显示的标签，附带典型范围"""
    t = engine._traits.get(trait_id)
    if not t:
        return trait_id
    label = t.name
    if t.typical_range[0] is not None:
        label += f"  ({t.typical_range[0]}~{t.typical_range[1]}{t.unit})"
    return label


# ── 侧边栏导航 ─────────────────────────────────────────────

st.sidebar.markdown(
    "<h1 style='font-size: 1.5rem;'>🌾 让邺城燃烧</h1>",
    unsafe_allow_html=True,
)
st.sidebar.markdown("**Bio-Logic Debugger**")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "导航",
    ["育种目标验证", "性状浏览器", "反模式库", "约束规则"],
    label_visibility="collapsed",
)

st.sidebar.markdown("---")
st.sidebar.caption(
    "用生物学逻辑在播种前筛掉注定失败的育种方向。"
)
st.sidebar.caption(
    "⚠️ 当前运行在本地网络，仅建议在受信任的内网使用。"
)

# ══════════════════════════════════════════════════════════
# 页面 1: 育种目标验证
# ══════════════════════════════════════════════════════════

if page == "育种目标验证":
    st.title("🎯 育种目标验证")
    st.markdown(
        "设定育种目标，系统会检查拮抗关系、生理约束和已知反模式。"
    )

    col_left, col_right = st.columns([3, 2])

    with col_left:
        st.subheader("目标设定")

        goal_name = st.text_input("育种目标名称", "未命名品种")

        available_traits = sorted(engine._traits.keys())
        categories = set(t.category for t in engine._traits.values())

        if "goal_targets" not in st.session_state:
            st.session_state.goal_targets = []

        # 添加新目标
        with st.container(border=True):
            cat_filter = st.selectbox(
                "分类筛选", ["全部"] + sorted(categories), key="cat_filter"
            )

            filtered = [
                t for t in available_traits
                if cat_filter == "全部" or engine._traits[t].category == cat_filter
            ]
            trait_id = st.selectbox(
                "性状", filtered,
                format_func=trait_label,
            )

            dir_col, val_col, pri_col = st.columns([1, 2, 1])
            with dir_col:
                direction = st.selectbox("方向", [">=", "<=", "=="], key="direction")
            with val_col:
                desired_value = st.number_input(
                    "目标值",
                    value=0.0,
                    step=0.1,
                    format="%.2f",
                )
            with pri_col:
                priority = st.number_input(
                    "优先级", min_value=1, max_value=10, value=5,
                )

            if st.button("➕ 添加目标", use_container_width=True):
                st.session_state.goal_targets.append({
                    "trait_id": trait_id,
                    "direction": direction,
                    "value": desired_value,
                    "priority": priority,
                })
                st.rerun()

        # 已添加的目标列表（紧凑卡片式）
        if st.session_state.goal_targets:
            st.markdown("**已设定的目标：**")
            for i, tgt in enumerate(st.session_state.goal_targets):
                tname = engine._trait_name(tgt["trait_id"])
                trait = engine._traits.get(tgt["trait_id"])
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

            # 可选的 LLM 配置
            with st.expander("⚙️ LLM 深度分析（可选）"):
                llm_enabled = st.checkbox("启用 LLM 分析", value=False)
                api_key = st.text_input(
                    "API Key", type="password",
                    placeholder="sk-... 或设置 BIO_LLM_API_KEY",
                )
                base_url = st.text_input(
                    "Base URL", placeholder="https://api.deepseek.com/v1",
                )
                model = st.text_input("模型名", placeholder="deepseek-chat")

            if st.button("🚀 运行验证", type="primary", use_container_width=True):
                goal = BreedingGoal(name=goal_name, species="水稻")
                for tgt in st.session_state.goal_targets:
                    goal.add_target(TraitTarget(
                        trait_id=tgt["trait_id"],
                        desired_value=tgt["value"],
                        direction=tgt["direction"],
                        priority=tgt["priority"],
                    ))

                if llm_enabled:
                    from bio_logic_debugger.llm.reasoner import LLMConfig, LLMReasoner
                    config = LLMConfig(
                        api_key=api_key or None,
                        base_url=base_url or None,
                        model=model or None,
                    )
                    reasoner = LLMReasoner(config=config)
                    engine.set_llm_callback(reasoner.analyze)

                with st.spinner("验证中..."):
                    report = engine.validate(goal)

                st.session_state.last_report = report
                st.rerun()

    # ── 结果展示 ──
    with col_right:
        st.subheader("验证结果")

        if "last_report" not in st.session_state:
            st.info("左侧设定目标后点击「运行验证」")
        else:
            report = st.session_state.last_report

            if report.passed:
                st.success("✅ 可以推进")
            else:
                st.error("❌ 建议重新评估")

            summary = report.summary()
            mc1, mc2, mc3, mc4 = st.columns(4)
            mc1.metric("致命", summary["fatal"], border=True)
            mc2.metric("严重", summary["severe"], border=True)
            mc3.metric("警告", summary["warnings"], border=True)
            mc4.metric("提示", summary["infos"], border=True)

            if summary["anti_patterns_matched"]:
                st.markdown(
                    f"⚠️ 匹配到 {summary['anti_patterns_matched']} 个反模式"
                )

    # ── 完整报告（下方） ──
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
            sorted_v = sorted(
                report.violations, key=lambda v: severity_order.get(v.severity, 99)
            )

            for v in sorted_v:
                tag_map = {
                    ConstraintSeverity.FATAL: ("🔴", "致命", "#ff4b4b"),
                    ConstraintSeverity.SEVERE: ("🟠", "严重", "#ff922b"),
                    ConstraintSeverity.WARNING: ("🟡", "警告", "#fcc419"),
                    ConstraintSeverity.INFO: ("🔵", "提示", "#339af0"),
                }
                icon, tag, color = tag_map.get(v.severity, ("⚪", "未知", "#888"))
                badge = f"<span style='background:{color};color:white;padding:1px 8px;border-radius:10px;font-size:0.75em;'>{tag}</span>"

                expanded = v.severity in (
                    ConstraintSeverity.FATAL, ConstraintSeverity.SEVERE
                )

                with st.expander(
                    f"{icon} {badge} {v.title}", expanded=expanded,
                ):
                    st.markdown(v.description, unsafe_allow_html=True)

                    if v.involved_traits:
                        trait_names = []
                        for tid in v.involved_traits:
                            tn = engine._trait_name(tid)
                            trait_names.append(tn)
                        st.markdown(
                            "**涉及性状：**　" + "　".join(
                                [f"`{n}`" for n in trait_names]
                            )
                        )

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

# ══════════════════════════════════════════════════════════
# 页面 2: 性状浏览器
# ══════════════════════════════════════════════════════════

elif page == "性状浏览器":
    st.title("🔬 性状浏览器")
    st.markdown("浏览所有可用性状及其关联关系。")

    categories = sorted(set(t.category for t in engine._traits.values()))
    selected_cat = st.selectbox("按分类筛选", ["全部"] + categories)

    traits_to_show = [
        t for t in engine._traits.values()
        if selected_cat == "全部" or t.category == selected_cat
    ]

    by_cat: dict[str, list] = {}
    for t in traits_to_show:
        by_cat.setdefault(t.category, []).append(t)

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

                    related = [
                        c for c in engine._correlations
                        if t.id in (c.trait_a, c.trait_b)
                    ]
                    if related:
                        with st.expander(f"关联 ({len(related)})"):
                            for c in related:
                                other = (
                                    c.trait_b if c.trait_a == t.id else c.trait_a
                                )
                                other_name = engine._trait_name(other)
                                tag = (
                                    "🔴 拮抗"
                                    if c.is_antagonistic()
                                    else "🟡 权衡"
                                    if c.corr_type == CorrelationType.TRADE_OFF
                                    else "🟢 正相关"
                                    if c.corr_type == CorrelationType.POSITIVE
                                    else "🔵 相关"
                                )
                                st.markdown(
                                    f"{tag} **{other_name}**　(r={c.strength})"
                                )
                                st.caption(
                                    c.mechanism[:80] + "..."
                                    if len(c.mechanism) > 80
                                    else c.mechanism
                                )

# ══════════════════════════════════════════════════════════
# 页面 3: 反模式库
# ══════════════════════════════════════════════════════════

elif page == "反模式库":
    st.title("📚 反模式库")
    st.markdown(
        "历史上反复验证的育种死胡同。"
    )

    severity_filter = st.selectbox(
        "按等级筛选",
        ["全部", "严重", "警告", "提示"],
    )

    for ap in engine._anti_patterns._patterns.values():
        if severity_filter == "严重" and ap.severity not in (
            ConstraintSeverity.SEVERE, ConstraintSeverity.FATAL
        ):
            continue
        if severity_filter == "警告" and ap.severity != ConstraintSeverity.WARNING:
            continue

        tag_map = {
            ConstraintSeverity.FATAL: ("🔴", "致命"),
            ConstraintSeverity.SEVERE: ("🟠", "严重"),
            ConstraintSeverity.WARNING: ("🟡", "警告"),
            ConstraintSeverity.INFO: ("🔵", "提示"),
        }
        icon, tag = tag_map.get(ap.severity, ("⚪", ""))

        with st.expander(f"{icon} **[{tag}] {ap.name}**"):
            st.markdown(ap.description)

            # 触发性状：用 trait 中文名显示
            trigger_names = [
                engine._trait_name(t) for t in ap.trigger_traits
            ]
            st.markdown(
                "**触发性状：**　"
                + "　".join([f"`{n}`" for n in trigger_names])
            )

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

# ══════════════════════════════════════════════════════════
# 页面 4: 约束规则
# ══════════════════════════════════════════════════════════

elif page == "约束规则":
    st.title("📜 生物学约束规则")
    st.markdown("生理学法则——违反这些约束意味着生理上不可能。")

    for constraint in engine._constraints:
        tag_map = {
            ConstraintSeverity.FATAL: ("🔴", "致命"),
            ConstraintSeverity.SEVERE: ("🟠", "严重"),
            ConstraintSeverity.WARNING: ("🟡", "警告"),
            ConstraintSeverity.INFO: ("🔵", "提示"),
        }
        icon, tag = tag_map.get(constraint.severity, ("⚪", ""))

        with st.container(border=True):
            cols = st.columns([0.05, 1])
            with cols[0]:
                st.markdown(f"**{icon}**")
            with cols[1]:
                st.markdown(f"**[{tag}] {constraint.name}**")
                st.markdown(constraint.description)
                st.markdown(
                    f"适用范围：`{constraint.scope.name}` / {constraint.species}"
                )
                if constraint.consequence:
                    st.markdown(f"后果：_{constraint.consequence}_")
                if constraint.condition_expr:
                    st.code(constraint.condition_expr, language="text")
                st.caption(f"置信度：{constraint.confidence:.0%}")
