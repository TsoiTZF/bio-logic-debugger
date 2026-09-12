from __future__ import annotations

import streamlit as st

from bio_logic_debugger.core.engine import BioLogicEngine
from bio_logic_debugger.knowledge import knowledge_store
from bio_logic_debugger.knowledge.weight_store import load_weights as load_user_weights
from bio_logic_debugger.knowledge.weight_store import merge_slider_overrides
from bio_logic_debugger.knowledge.weight_store import save_weights as save_user_weights


def render(engine: BioLogicEngine) -> None:
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
                image_bytes = chart_img.getvalue()
                st.image(image_bytes, caption="已上传的图表", use_container_width=True)
                st.session_state.chart_image_bytes = image_bytes
                vis_key = st.text_input(
                    "Vision API Key", type="password",
                    key="_vision_api_key",
                    placeholder="sk-... 或设置 BIO_LLM_API_KEY",
                )
                vis_url = st.text_input(
                    "Vision Base URL", key="_vision_base_url",
                    placeholder="https://api.openai.com/v1",
                )
                vis_model = st.text_input(
                    "Vision 模型", key="_vision_model", placeholder="gpt-4o",
                )
                if st.button("🔍 解读图表", use_container_width=True):
                    from bio_logic_debugger.llm.reasoner import LLMConfig, LLMReasoner
                    reasoner = LLMReasoner(config=LLMConfig.from_ui(
                        api_key=vis_key, base_url=vis_url, model=vis_model,
                    ))
                    reasoner.set_vision_model(vis_model or reasoner._vision_model)
                    with st.spinner("解读图表中..."):
                        st.session_state.chart_analysis = reasoner.analyze_vision(image_bytes)
                if st.session_state.get("chart_analysis"):
                    st.markdown(st.session_state.chart_analysis)

        # ── 自动检索论文 ──────────────────────────────
        with st.expander("🔄 自动检索论文（从知识库关键词搜索 CrossRef）"):
            # 从知识库提取关键词
            if "_search_keywords" not in st.session_state:
                from bio_logic_debugger.knowledge.paper_search import extract_keywords_from_knowledge
                kw = extract_keywords_from_knowledge(
                    list(engine.iter_traits()),
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
            llm_for_extract = st.checkbox(
                "启用 LLM 提取（需配置 API Key）", value=False,
                help="通过 LLM 提取更精确的结构化信息",
            )
            extract_api_key = ""
            extract_base_url = ""
            extract_model = ""
            if llm_for_extract:
                with st.expander("⚙️ LLM 配置", expanded=True):
                    extract_api_key = st.text_input(
                        "API Key", type="password",
                        key="_extract_api_key",
                        placeholder="sk-... 或设置 BIO_LLM_API_KEY",
                    )
                    extract_base_url = st.text_input(
                        "Base URL",
                        key="_extract_base_url",
                        placeholder="https://api.deepseek.com/v1",
                    )
                    extract_model = st.text_input(
                        "模型名", key="_extract_model", placeholder="deepseek-chat",
                    )
            raw_len = len(st.session_state.paper_raw_text)
            if raw_len > 6000:
                st.info(
                    f"正文约 {raw_len} 字。启用 LLM 时会按约 6000 字分块送入，"
                    "不再只取前 8000 字。"
                )
            analyze_btn = st.button("🚀 开始分析", type="primary", use_container_width=True)

            if analyze_btn:
                from bio_logic_debugger.knowledge.paper_analyzer import analyze_text

                llm_caller = None
                if llm_for_extract:
                    from bio_logic_debugger.llm.reasoner import LLMConfig, LLMReasoner
                    reasoner = LLMReasoner(config=LLMConfig.from_ui(
                        api_key=extract_api_key,
                        base_url=extract_base_url,
                        model=extract_model,
                    ))
                    llm_caller = reasoner.chat

                with st.spinner("分析论文中..."):
                    extracted = analyze_text(
                        st.session_state.paper_raw_text,
                        llm_caller=llm_caller,
                    )

                st.session_state.extracted_items = extracted
                st.success(f"分析完成，共提取 {len(extracted)} 条")

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
                        label = item.data.get("name") or item.data.get("trait_a", "未知")
                        checked = st.checkbox(
                            f"{label}  置信度 {item.confidence:.0%}",
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
                            detail_parts.append(f"原文：{item.source_sentence[:100]}")
                        if detail_parts:
                            st.markdown("\n\n".join(detail_parts))
                        st.markdown("---")

            # 导入按钮
            if st.button("📥 导入到知识库", type="primary", use_container_width=True):
                from bio_logic_debugger.knowledge.paper_analyzer import (
                    items_to_constraints,
                    items_to_correlations,
                    items_to_traits,
                )

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
                    known = list(engine.iter_traits())
                    new_traits = items_to_traits(selected_items, known)
                    new_corrs = items_to_correlations(selected_items, known)
                    new_constraints = items_to_constraints(selected_items, known)

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
                        stored = knowledge_store.load_user_knowledge()
                        st.session_state._user_traits = list(stored.get("traits", []))
                        st.session_state._user_corrs = list(stored.get("correlations", []))
                        st.session_state._user_constraints = list(stored.get("constraints", []))
                        st.session_state._user_anti_patterns = list(stored.get("anti_patterns", []))

                    st.session_state._user_traits.extend(new_traits)
                    st.session_state._user_corrs.extend(new_corrs)
                    st.session_state._user_constraints.extend(new_constraints)
                    knowledge_store.save_user_knowledge(
                        traits=st.session_state._user_traits,
                        correlations=st.session_state._user_corrs,
                        constraints=st.session_state._user_constraints,
                    )

                    st.success(f"✅ 已导入 {len(selected_items)} 条到知识库（已写入用户目录）！")
                    st.rerun()

    # ── Tab 2: 知识库管理 ──────────────────────────────

    with tab2:
        st.subheader("知识库管理")

        # 当前状态
        stored_user = knowledge_store.load_user_knowledge()
        if "_user_traits" not in st.session_state:
            st.session_state._user_traits = list(stored_user.get("traits", []))
            st.session_state._user_corrs = list(stored_user.get("correlations", []))
            st.session_state._user_constraints = list(stored_user.get("constraints", []))

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
        # tab 的内容每轮都会渲染，滑条一定进 session_state；保存时与磁盘合并。
        wtab1, wtab2, wtab3 = st.tabs([
            f"性状权重（{len(engine.trait_ids())}）",
            f"关联权重（{len(engine.iter_correlations())}）",
            f"约束权重（{len(engine.iter_constraints())}）",
        ])
        with wtab1:
            st.caption("低置信度的性状，其范围越界警告将降级为 INFO")
            for t in sorted(engine.iter_traits(), key=lambda x: x.id):
                tid = t.id
                default_conf = user_weights.get("traits", {}).get(tid, t.confidence)
                st.slider(
                    f"{t.name}（{t.category}）",
                    min_value=0.0, max_value=1.0, value=float(default_conf), step=0.1,
                    key=f"wt_trait_{tid}",
                )
        with wtab2:
            st.caption("低置信度的关联，验证时有效强度降低")
            for c in engine.iter_correlations():
                name_a = engine.trait_name(c.trait_a)
                name_b = engine.trait_name(c.trait_b)
                key = f"{c.trait_a}__{c.trait_b}" if c.trait_a < c.trait_b else f"{c.trait_b}__{c.trait_a}"
                default_conf = user_weights.get("correlations", {}).get(key, c.confidence)
                st.slider(
                    f"{name_a} ↔ {name_b}（r={c.strength}）",
                    min_value=0.0, max_value=1.0, value=float(default_conf), step=0.1,
                    key=f"wt_corr_{key}",
                )
        with wtab3:
            st.caption("低置信度的约束，违反时严重等级自动降级")
            for c in engine.iter_constraints():
                default_conf = user_weights.get("constraints", {}).get(c.id, c.confidence)
                st.slider(
                    f"{c.name}（{c.severity.name}）",
                    min_value=0.0, max_value=1.0, value=float(default_conf), step=0.1,
                    key=f"wt_cstr_{c.id}",
                )

        if st.button("💾 保存权重并重新加载引擎", type="primary", use_container_width=True):
            save_user_weights(merge_slider_overrides(load_user_weights(), dict(st.session_state)))
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
            "💡 **提示**：启动时不会自动覆盖知识库。需要更新时，在侧边栏或本页点「检查更新 / 手动同步」。"
        )
