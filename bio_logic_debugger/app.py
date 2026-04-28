#!/usr/bin/env python3
"""
让邺城燃烧 — Bio-Logic Debugger Web UI (Streamlit)
"""
from __future__ import annotations

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st

from bio_logic_debugger import __version__
from bio_logic_debugger.core.domain import (
    AntiPattern,
    BreedingGoal,
    ConstraintSeverity,
    CorrelationType,
    TraitTarget,
)
from bio_logic_debugger.core.engine import BioLogicEngine
from bio_logic_debugger.knowledge import knowledge_store
from bio_logic_debugger.knowledge.knowledge_store import load_and_merge
from bio_logic_debugger.knowledge.weight_store import (
    load_weights as load_user_weights,
    save_weights as save_user_weights,
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
    try:
        traits, correlations, constraints, anti_patterns = load_and_merge()
        engine.register_traits(traits)
        engine.register_correlations(correlations)
        engine.register_constraints(constraints)
        engine.register_anti_patterns(anti_patterns)
    except Exception as e:
        # fallback to builtin if merge fails
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
    return engine


engine = get_engine()

# 加载用户权重并应用到引擎
try:
    from bio_logic_debugger.knowledge.weight_store import apply_weights_to_engine
    apply_weights_to_engine(engine)
except Exception:
    pass


# ── 启动时静默同步社区知识库（仅检查，不自动刷新） ──────────

if "_sync_done" not in st.session_state:
    try:
        st.session_state._sync_result = knowledge_store.sync_from_community()
        st.session_state._sync_done = True
    except Exception as e:
        st.session_state._sync_result = False
        st.session_state._sync_done = True

# 同步完成后弹通知，仅首次显示
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
                st.session_state._sync_result = False  # 隐藏提示
                st.rerun()

# ── 版本更新提示（首次启动显示） ──────────────────────────

if "_version_notified" not in st.session_state:
    st.session_state._version_notified = True
    if __version__ == "0.2.0":
        st.toast("🎉 已更新至 v0.2.0 — 新增自动论文检索与数据权重调整", icon="✨")


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
st.sidebar.caption(f"v{__version__}")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "导航",
    ["育种目标验证", "性状浏览器", "反模式库", "约束规则", "📚 文献与知识库"],
    label_visibility="collapsed",
)

st.sidebar.markdown("---")
st.sidebar.caption(
    "用生物学逻辑在播种前筛掉注定失败的育种方向。"
)
st.sidebar.caption(
    "⚠️ 当前运行在本地网络，仅建议在受信任的内网使用。"
)

# ── 侧边栏知识库状态 ────────────────────────────────────

st.sidebar.markdown("---")
st.sidebar.caption("📦 知识库状态")
with st.sidebar:
    trait_count = len(engine._traits)
    corr_count = len(engine._correlations)
    ap_count = len(engine._anti_patterns._patterns)
    last_sync = knowledge_store.get_last_sync_time()
    has_community = knowledge_store.has_community_data()

    if has_community:
        sync_status = "✅ 已同步"
    else:
        sync_status = "⚪ 内置模式（未同步）"
    st.caption(f"{sync_status}")
    if last_sync:
        st.caption(f"同步于 {last_sync}")
    else:
        st.caption("从未同步")
    st.caption(f"性状 {trait_count} / 关联 {corr_count} / 反模式 {ap_count}")
    # 已检索论文数
    try:
        from bio_logic_debugger.knowledge.paper_search import load_seen_papers
        seen_count = len(load_seen_papers())
        st.caption(f"已检索 {seen_count} 篇论文")
    except Exception:
        pass

    # 同步按钮
    if st.button("🔄 检查更新", use_container_width=True, key="sidebar_sync"):
        with st.spinner("检查社区知识库..."):
            ok = knowledge_store.sync_from_community()
            if ok:
                st.cache_resource.clear()
                st.toast("✅ 社区知识库已更新，引擎已重新加载", icon="📦")
                st.rerun()
            else:
                st.toast("⚠️ 同步失败，请检查网络", icon="⚠️")

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

# ══════════════════════════════════════════════════════════
# 页面 5: 文献与知识库
# ══════════════════════════════════════════════════════════

elif page == "📚 文献与知识库":
    st.title("📚 文献与知识库")
    st.markdown("上传论文、分析图表、管理知识库。")

    tab1, tab2, tab3 = st.tabs(["📄 导入文献分析", "📦 知识库管理", "🤝 贡献指南"])

    # ── Tab 1: 导入文献分析 ──────────────────────────────

    with tab1:
        st.subheader("导入文献分析")
        st.markdown("从论文中提取性状、关联和约束，审核后导入知识库。")

        # 来源选择
        source_method = st.radio(
            "论文来源",
            ["上传 PDF", "DOI / 标题搜索"],
            horizontal=True,
        )

        pdf_bytes = None
        paper_meta = {}

        if source_method == "上传 PDF":
            uploaded = st.file_uploader(
                "上传 PDF 文件", type=["pdf"],
                help="支持标准的学术论文 PDF",
            )
            if uploaded:
                pdf_bytes = uploaded.read()
                st.success(f"已上传：{uploaded.name} ({len(pdf_bytes) // 1024} KB)")
                # 提取文本
                from bio_logic_debugger.knowledge.pdf_parser import extract_text
                with st.spinner("提取文本中..."):
                    raw_text = extract_text(pdf_bytes)
                st.info(f"提取到 {len(raw_text)} 字符")
                st.session_state.paper_raw_text = raw_text

        else:
            col1, col2 = st.columns([3, 1])
            with col1:
                search_input = st.text_input(
                    "DOI 或论文标题",
                    placeholder="10.1007/s00122-021-03867-w 或输入标题...",
                )
            with col2:
                search_btn = st.button("🔍 检索", use_container_width=True)

            if search_btn and search_input:
                from bio_logic_debugger.knowledge.doi_fetcher import (
                    fetch_by_doi, search_by_title,
                )
                with st.spinner("检索中..."):
                    # 检测是否为 DOI
                    if search_input.startswith("10."):
                        paper_meta = fetch_by_doi(search_input) or {}
                    else:
                        paper_meta = search_by_title(search_input) or {}

                if paper_meta:
                    st.success(f"找到：{paper_meta.get('title', '未知')}")
                    st.session_state.paper_meta = paper_meta
                    st.session_state.paper_raw_text = paper_meta.get("abstract", "")
                else:
                    st.warning("未找到相关论文")

            # 显示已检索的元数据
            if "paper_meta" in st.session_state and st.session_state.paper_meta:
                pm = st.session_state.paper_meta
                with st.container(border=True):
                    st.markdown(f"**{pm.get('title')}**")
                    cols = st.columns(4)
                    cols[0].caption(f"作者：{'、'.join(pm.get('authors', []))}")
                    cols[1].caption(f"期刊：{pm.get('journal', 'N/A')}")
                    cols[2].caption(f"年份：{pm.get('year', 'N/A')}")
                    if pm.get("doi"):
                        cols[3].caption(f"DOI：{pm['doi']}")

        # 图表分析（可选）
        with st.expander("📊 图表分析（可选）"):
            chart_img = st.file_uploader(
                "上传图表图片（如相关性热图、箱线图等）",
                type=["png", "jpg", "jpeg", "gif", "webp"],
            )
            if chart_img:
                st.image(chart_img, caption="已上传的图表", use_container_width=True)
                st.session_state.chart_image_bytes = chart_img.read()

        # ── 自动检索论文 ──────────────────────────────
        with st.expander("🔄 自动检索论文（从知识库关键词搜索 CrossRef）"):
            # 从知识库提取关键词
            if "_search_keywords" not in st.session_state:
                from bio_logic_debugger.knowledge.paper_search import extract_keywords_from_knowledge
                kw = extract_keywords_from_knowledge(
                    list(engine._traits.values()),
                    max_keywords=10,
                )
                st.session_state._search_keywords = kw

            st.markdown("**检索关键词**（可编辑）：")
            edited_keywords = st.text_input(
                "关键词（逗号分隔）",
                value=", ".join(st.session_state._search_keywords),
                key="search_kw_input",
                label_visibility="collapsed",
            )
            kw_list = [k.strip() for k in edited_keywords.split(",") if k.strip()]

            col_s1, col_s2 = st.columns([1, 3])
            with col_s1:
                rows_per = st.number_input("每批数量", min_value=3, max_value=20, value=8, step=1)
            with col_s2:
                search_btn = st.button("🔍 开始检索", type="primary", use_container_width=True)

            if search_btn:
                from bio_logic_debugger.knowledge.paper_search import (
                    load_seen_papers,
                    mark_papers_seen,
                    search_all_keywords,
                )
                seen = load_seen_papers()
                with st.spinner(f"正在用 {len(kw_list)} 个关键词检索 CrossRef..."):
                    papers = search_all_keywords(kw_list, rows_per_query=rows_per, seen_dois=seen)

                if not papers:
                    st.info("没有找到新的论文（所有结果已检索过）")
                else:
                    st.success(f"找到 {len(papers)} 篇新论文")
                    st.session_state._auto_search_results = papers

            # 显示检索结果
            if "_auto_search_results" in st.session_state:
                papers = st.session_state._auto_search_results
                if papers:
                    st.markdown("**检索结果（勾选要分析的论文）：**")
                    selected_papers = []
                    for i, p in enumerate(papers):
                        c1, c2 = st.columns([0.05, 1])
                        with c1:
                            checked = st.checkbox("", key=f"paper_{i}")
                        with c2:
                            meta = f"**{p.get('title', '未知')}**"
                            authors = "、".join(p.get("authors", []))[:60]
                            if authors:
                                meta += f"　_{authors}_"
                            meta += f"　({p.get('year', '?')})"
                            if p.get("journal"):
                                meta += f"　`{p['journal']}`"
                            if p.get("doi"):
                                meta += f"　DOI: {p['doi']}"
                            st.markdown(meta)
                            if p.get("abstract"):
                                abstract_preview = p["abstract"][:200].replace("<", "&lt;").replace(">", "&gt;")
                                st.caption(f"摘要：{abstract_preview}…" if len(p["abstract"]) > 200 else f"摘要：{abstract_preview}")
                        if checked:
                            selected_papers.append(p)

                    if selected_papers:
                        if st.button("📥 分析选中论文", use_container_width=True):
                            from bio_logic_debugger.knowledge.paper_search import mark_papers_seen
                            from bio_logic_debugger.knowledge.paper_analyzer import analyze_text
                            # 合并选中论文的摘要
                            combined = "\n\n".join(
                                p.get("abstract", "") for p in selected_papers
                            )
                            if combined.strip():
                                with st.spinner("分析中..."):
                                    extracted = analyze_text(combined, llm_caller=None)
                                st.session_state.extracted_items = extracted
                                st.session_state._auto_search_results = []  # 清空结果
                                # 标记已见
                                mark_papers_seen(selected_papers)
                                st.success(f"分析完成，共提取 {len(extracted)} 条，请在上方「分析结果」区域审核导入")
                                st.rerun()
                            else:
                                st.warning("选中论文无可用摘要")

        # ── 开始分析 ──
        has_text = "paper_raw_text" in st.session_state and st.session_state.paper_raw_text.strip()

        if has_text:
            col_a, col_b = st.columns([1, 3])
            with col_a:
                llm_for_extract = st.checkbox(
                    "启用 LLM 提取（需配置 API Key）", value=False,
                    help="通过 LLM 提取更精确的结构化信息",
                )
            with col_b:
                analyze_btn = st.button("🚀 开始分析", type="primary", use_container_width=True)

            if analyze_btn:
                from bio_logic_debugger.knowledge.paper_analyzer import analyze_text

                llm_caller = None
                if llm_for_extract:
                    api_key = st.session_state.get("_extract_api_key", "")
                    base_url = st.session_state.get("_extract_base_url", "")
                    model = st.session_state.get("_extract_model", "")
                    if api_key:
                        from bio_logic_debugger.llm.reasoner import LLMConfig, LLMReasoner
                        config = LLMConfig(
                            api_key=api_key,
                            base_url=base_url or None,
                            model=model or None,
                        )
                        reasoner = LLMReasoner(config=config)
                        llm_caller = reasoner.extract_knowledge

                with st.spinner("分析论文中..."):
                    extracted = analyze_text(
                        st.session_state.paper_raw_text,
                        llm_caller=llm_caller,
                    )

                st.session_state.extracted_items = extracted
                st.success(f"分析完成，共提取 {len(extracted)} 条")

        # LLM API 配置（分析用）
        if has_text and llm_for_extract:
            with st.expander("⚙️ LLM 配置"):
                st.text_input(
                    "API Key", type="password",
                    key="_extract_api_key",
                    placeholder="sk-... 或设置 BIO_LLM_API_KEY",
                )
                st.text_input(
                    "Base URL",
                    key="_extract_base_url",
                    placeholder="https://api.deepseek.com/v1",
                )
                st.text_input("模型名", key="_extract_model", placeholder="deepseek-chat")

        # 展示分析结果
        if "extracted_items" in st.session_state and st.session_state.extracted_items:
            items = st.session_state.extracted_items
            st.divider()
            st.subheader("分析结果")

            # 分类展示
            categories = {"trait": "🧬 性状", "correlation": "🔗 关联", "constraint": "📜 约束"}
            selected_ids = set()

            for cat_key, cat_label in categories.items():
                cat_items = [it for it in items if it.item_type == cat_key]
                if not cat_items:
                    continue

                with st.expander(f"{cat_label}（{len(cat_items)} 条）", expanded=True):
                    for idx, item in enumerate(cat_items):
                        item_key = f"{cat_key}_{idx}"
                        checked = st.checkbox(
                            f"**{item.data.get('name') or item.data.get('trait_a', '未知')}**　"
                            f"<span style='color:#888;font-size:0.8em;'>置信度 {item.confidence:.0%}</span>",
                            value=item.selected,
                            key=f"select_{item_key}",
                        )
                        if checked:
                            selected_ids.add(item_key)

                        # 显示详情
                        detail_parts = []
                        if item.data.get("trait_b"):
                            detail_parts.append(
                                f"{item.data['trait_a']} ↔ {item.data['trait_b']}　"
                                f"类型：{item.data.get('type', '')}　"
                                f"强度：{item.data.get('strength', 0)}"
                            )
                        if item.data.get("description"):
                            detail_parts.append(f"描述：{item.data['description'][:120]}")
                        if item.data.get("range"):
                            detail_parts.append(
                                f"范围：{item.data['range']} {item.data.get('unit', '')}"
                            )
                        if item.source_sentence:
                            detail_parts.append(
                                f"<span style='color:#999;font-style:italic;'>"
                                f"原文：{item.source_sentence[:100]}</span>"
                            )
                        if detail_parts:
                            st.markdown("<br>".join(detail_parts), unsafe_allow_html=True)
                        st.markdown("---")

            # 导入按钮
            if st.button("📥 导入到知识库", type="primary", use_container_width=True):
                from bio_logic_debugger.knowledge.paper_analyzer import (
                    items_to_constraints,
                    items_to_correlations,
                    items_to_traits,
                )

                # 收集勾选项
                selected_items = []
                for cat_key in categories:
                    cat_items = [it for it in items if it.item_type == cat_key]
                    for idx, item in enumerate(cat_items):
                        if f"{cat_key}_{idx}" in selected_ids:
                            item.selected = True
                            selected_items.append(item)

                if not selected_items:
                    st.warning("请先勾选要导入的项")
                else:
                    # 转换为知识库格式
                    new_traits = items_to_traits(selected_items)
                    new_corrs = items_to_correlations(selected_items)
                    new_constraints = items_to_constraints(selected_items)

                    # 注册到引擎
                    from bio_logic_debugger.knowledge.knowledge_store import (
                        constraint_from_dict,
                        correlation_from_dict,
                        trait_from_dict,
                    )
                    for d in new_traits:
                        engine.register_trait(trait_from_dict(d))
                    for d in new_corrs:
                        engine.register_correlation(correlation_from_dict(d))
                    for d in new_constraints:
                        engine.register_constraint(constraint_from_dict(d))

                    # 保存到 session_state 用户扩充列表
                    if "_user_traits" not in st.session_state:
                        st.session_state._user_traits = []
                        st.session_state._user_corrs = []
                        st.session_state._user_constraints = []

                    st.session_state._user_traits.extend(new_traits)
                    st.session_state._user_corrs.extend(new_corrs)
                    st.session_state._user_constraints.extend(new_constraints)

                    st.success(f"✅ 已导入 {len(selected_items)} 条到知识库！")
                    st.rerun()

    # ── Tab 2: 知识库管理 ──────────────────────────────

    with tab2:
        st.subheader("知识库管理")

        # 当前状态
        col1, col2, col3 = st.columns(3)
        col1.metric("内置性状", len(knowledge_store.load_builtin().get("traits", [])), border=True)
        col2.metric("社区性状", len(knowledge_store.load_community().get("traits", [])), border=True)
        col3.metric("用户扩充", len(st.session_state.get("_user_traits", [])), border=True)

        sync_time = knowledge_store.get_last_sync_time() or "从未同步"
        st.caption(f"📅 最后同步：{sync_time}")

        # 同步按钮
        if st.button("🔄 手动同步社区知识库", use_container_width=True):
            with st.spinner("同步中..."):
                if knowledge_store.sync_from_community():
                    st.success("同步完成！正在重新加载引擎...")
                    # 清理缓存，重新加载
                    st.cache_resource.clear()
                    st.rerun()
                else:
                    st.warning("部分同步失败，请检查网络连接")

        st.divider()

        # 用户扩充列表
        user_traits = st.session_state.get("_user_traits", [])
        user_corrs = st.session_state.get("_user_corrs", [])
        user_constraints = st.session_state.get("_user_constraints", [])

        if user_traits or user_corrs or user_constraints:
            st.markdown("**用户扩充的知识：**")

            if user_traits:
                with st.expander(f"🧬 用户性状（{len(user_traits)} 条）"):
                    for t in user_traits:
                        st.markdown(f"- **{t.get('name')}**　`{t.get('id')}`　范围：{t.get('typical_range')} {t.get('unit', '')}")

            if user_corrs:
                with st.expander(f"🔗 用户关联（{len(user_corrs)} 条）"):
                    for c in user_corrs:
                        st.markdown(f"- {c.get('trait_a')} ↔ {c.get('trait_b')}　类型：{c.get('corr_type')}　r={c.get('strength')}")

            if user_constraints:
                with st.expander(f"📜 用户约束（{len(user_constraints)} 条）"):
                    for c in user_constraints:
                        st.markdown(f"- **{c.get('name')}**　等级：{c.get('severity')}")

            # 导出
            st.divider()
            if st.button("📤 导出为 JSON", use_container_width=True):
                exported = knowledge_store.export_user_knowledge(
                    traits=user_traits,
                    correlations=user_corrs,
                    constraints=user_constraints,
                    anti_patterns=[],
                )
                st.download_button(
                    "⬇️ 下载 JSON 文件",
                    data=exported,
                    file_name="user_knowledge_export.json",
                    mime="application/json",
                )
                st.info("将此 JSON 提 PR 到 TsoiTZF/bio-logic-knowledge 仓库即可贡献到社区！")

        else:
            st.info("暂无用户扩充的知识。在「导入文献分析」Tab 中分析论文后导入即可。")

        st.divider()

        # ── 权重调整 ──────────────────────────────────
        st.subheader("⚖️ 数据权重调整")
        st.caption("调整每条知识对验证结果的影响程度。降低不可靠知识的权重可减少误报。")

        user_weights = load_user_weights()

        # 性状权重
        with st.expander(f"🧬 性状权重（{len(engine._traits)} 条）"):
            st.caption("低置信度的性状，其范围越界警告将降级为 INFO")
            trait_weights = {}
            for tid, t in sorted(engine._traits.items()):
                default_conf = user_weights.get("traits", {}).get(tid, t.confidence)
                w = st.slider(
                    f"{t.name}（{t.category}）",
                    min_value=0.0, max_value=1.0, value=default_conf, step=0.1,
                    key=f"wt_trait_{tid}",
                )
                if w != 1.0:
                    trait_weights[tid] = w

        # 关联权重
        with st.expander(f"🔗 关联权重（{len(engine._correlations)} 条）"):
            st.caption("低置信度的关联，验证时有效强度降低，警告等级相应降级")
            corr_weights = {}
            for c in engine._correlations:
                name_a = engine._trait_name(c.trait_a)
                name_b = engine._trait_name(c.trait_b)
                key = f"{c.trait_a}__{c.trait_b}" if c.trait_a < c.trait_b else f"{c.trait_b}__{c.trait_a}"
                default_conf = user_weights.get("correlations", {}).get(key, c.confidence)
                w = st.slider(
                    f"{name_a} ↔ {name_b}（r={c.strength}）",
                    min_value=0.0, max_value=1.0, value=default_conf, step=0.1,
                    key=f"wt_corr_{key}",
                )
                if w != 1.0:
                    corr_weights[key] = w

        # 约束权重
        with st.expander(f"📜 约束权重（{len(engine._constraints)} 条）"):
            st.caption("低置信度的约束，违反时严重等级自动降级")
            cstr_weights = {}
            for c in engine._constraints:
                default_conf = user_weights.get("constraints", {}).get(c.id, c.confidence)
                w = st.slider(
                    f"{c.name}（{c.severity.name}）",
                    min_value=0.0, max_value=1.0, value=default_conf, step=0.1,
                    key=f"wt_cstr_{c.id}",
                )
                if w != 1.0:
                    cstr_weights[c.id] = w

        # 保存按钮
        if st.button("💾 保存权重并重新加载引擎", type="primary", use_container_width=True):
            new_weights = {
                "traits": trait_weights,
                "correlations": corr_weights,
                "constraints": cstr_weights,
            }
            save_user_weights(new_weights)
            st.cache_resource.clear()
            st.success("✅ 权重已保存，引擎已重新加载！")
            st.rerun()

    # ── Tab 3: 贡献指南 ──────────────────────────────

    with tab3:
        st.subheader("🤝 贡献知识到社区")
        st.markdown("""
        本应用的知识库支持社区共享——你可以将本地提取的知识贡献到社区知识库，
        让所有用户都能获得最新的育种知识。
        """)

        with st.container(border=True):
            st.markdown("### 如何贡献")
            st.markdown("""
            1. **提取知识**：在「导入文献分析」Tab 中上传论文，提取性状/关联/约束
            2. **审核勾选**：检查提取结果，只勾选准确、有用的条目
            3. **导入到本地**：点击「导入到知识库」确认导入
            4. **导出 JSON**：切换到「知识库管理」Tab，点击「导出为 JSON」
            5. **提交 PR**：将导出的 JSON 文件提 Pull Request 到社区仓库：

            ```
            https://github.com/TsoiTZF/bio-logic-knowledge
            ```
            """)

        with st.container(border=True):
            st.markdown("### 社区仓库结构")
            st.code("""
            bio-logic-knowledge/
            ├── traits.json          # 性状定义
            ├── correlations.json    # 关联关系
            ├── constraints.json     # 约束规则
            ├── anti_patterns.json   # 反模式
            └── CHANGELOG.md         # 更新日志
            """)

        st.markdown("---")
        st.markdown(
            "💡 **提示**：每次启动 app 时会自动从社区仓库同步最新知识库。"
            "你也可以在「知识库管理」Tab 中手动触发同步。"
        )
