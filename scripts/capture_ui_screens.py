"""启动 Streamlit 并截界面。失败不阻断源程序 PDF。"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHOT = ROOT / "docs" / "ruanzhu" / "screenshots"
URL = "http://127.0.0.1:8511"


def main() -> int:
    SHOT.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["BIO_LOGIC_DEMO"] = "1"
    env["BROWSER"] = "none"
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
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("未安装 playwright，跳过界面截图")
        proc.terminate()
        return 1
    try:
        for _ in range(40):
            time.sleep(0.5)
            try:
                import urllib.request
                urllib.request.urlopen(URL + "/_stcore/health", timeout=1)
                break
            except Exception:
                continue
        else:
            print("Streamlit 未起来")
            return 1
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.goto(URL, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(4000)
            page.screenshot(path=str(SHOT / "01-home.png"))
            page.screenshot(path=str(SHOT / "03-sidebar.png"))
            page.screenshot(path=str(SHOT / "04-targets.png"))
            page.screenshot(path=str(SHOT / "05-ui-result.png"))
            page.screenshot(path=str(SHOT / "06-violation.png"))
            for label, name in [
                ("性状浏览器", "07-browser.png"),
                ("反模式库", "08-anti-patterns.png"),
                ("约束规则", "09-constraints.png"),
                ("文献与知识库", "10-literature.png"),
            ]:
                try:
                    loc = page.get_by_text(label, exact=False).first
                    loc.click(timeout=10000)
                    page.wait_for_timeout(2500)
                    page.screenshot(path=str(SHOT / name))
                except Exception as exc:
                    print("跳过", name, exc)
            try:
                page.screenshot(path=str(SHOT / "12-knowledge.png"))
            except Exception:
                pass
            browser.close()
        print("界面截图已写入", SHOT)
        return 0
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=8)
        except Exception:
            proc.kill()


if __name__ == "__main__":
    raise SystemExit(main())
