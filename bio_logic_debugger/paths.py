"""用户数据目录。社区缓存、用户知识、权重都放这里，不写进安装包。"""
from __future__ import annotations

import os
from pathlib import Path


def user_data_dir() -> Path:
    raw = os.environ.get("BIO_LOGIC_HOME", "").strip()
    if raw:
        path = Path(raw).expanduser()
    else:
        path = Path.home() / ".bio-logic-debugger"
    path.mkdir(parents=True, exist_ok=True)
    return path


def community_dir() -> Path:
    path = user_data_dir() / "community"
    path.mkdir(parents=True, exist_ok=True)
    return path
