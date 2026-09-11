#!/usr/bin/env python3
"""让邺城燃烧 — Streamlit 入口。页面在 ui.pages，引擎在 core。"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st

from bio_logic_debugger.ui.pages import anti_patterns, browser, constraints, literature, validate
from bio_logic_debugger.ui.runtime import boot, get_engine, render_sidebar

st.set_page_config(
    page_title="让邺城燃烧 — Bio-Logic Debugger",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded",
)

boot()
engine = get_engine()
page = render_sidebar(engine)

if page == "育种目标验证":
    validate.render(engine)
elif page == "性状浏览器":
    browser.render(engine)
elif page == "反模式库":
    anti_patterns.render(engine)
elif page == "约束规则":
    constraints.render(engine)
elif page == "📚 文献与知识库":
    literature.render(engine)
