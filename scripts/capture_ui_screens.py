"""启动 Streamlit，逐页截界面。"""
from __future__ import annotations

import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHOT = ROOT / "docs" / "ruanzhu" / "screenshots"
URL = "http://127.0.0.1:8511"


def wait_health() -> bool:
    for _ in range(60):
        try:
            urllib.request.urlopen(URL + "/_stcore/health", timeout=1)
            return True
        except Exception:
            time.sleep(0.5)
    return False


def snap(page, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        page.locator("html").screenshot(path=str(path), timeout=20000)
    except Exception:
        page.screenshot(path=str(path), timeout=20000, animations="disabled")


def main() -> int:
    SHOT.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["BIO_LOGIC_DEMO"] = "1"
    log = open(SHOT / "streamlit.log", "w", encoding="utf-8")
    proc = subprocess.Popen(
        [
            sys.executable, "-m", "streamlit", "run",
            str(ROOT / "bio_logic_debugger" / "app.py"),
            "--server.port", "8511",
            "--server.headless", "true",
            "--browser.gatherUsageStats", "false",
        ],
        cwd=str(ROOT),
        env=env,
        stdout=log,
        stderr=log,
    )
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("未安装 playwright")
        proc.terminate()
        return 1
    if not wait_health():
        print("Streamlit 未起来")
        proc.terminate()
        return 1

    jobs = [
        (None, "01-home.png"),
        (None, "03-sidebar.png"),
        (None, "04-targets.png"),
        (None, "05-ui-result.png"),
        (None, "06-violation.png"),
        ("性状浏览器", "07-browser.png"),
        ("反模式库", "08-anti-patterns.png"),
        ("约束规则", "09-constraints.png"),
        ("文献与知识库", "10-literature.png"),
        ("文献与知识库", "12-knowledge.png"),
    ]
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--disable-gpu", "--disable-dev-shm-usage", "--no-sandbox"],
            )
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.goto(URL, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(5000)
            last = None
            for label, name in jobs:
                if label and label != last:
                    page.get_by_text(label, exact=False).first.click(timeout=15000)
                    page.wait_for_timeout(3000)
                    last = label
                snap(page, SHOT / name)
                print("ok", name)
            # 文献页点到知识库 tab
            try:
                page.get_by_text("知识库", exact=False).first.click(timeout=8000)
                page.wait_for_timeout(2000)
                snap(page, SHOT / "12-knowledge.png")
                print("ok 12-knowledge.png")
            except Exception as exc:
                print("知识库 tab", exc)
            browser.close()
        return 0
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=8)
        except Exception:
            proc.kill()
        log.close()


if __name__ == "__main__":
    raise SystemExit(main())
