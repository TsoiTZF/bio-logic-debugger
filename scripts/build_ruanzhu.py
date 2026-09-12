"""生成软著交存：源程序 PDF、说明书 PDF、命令行/目录截图。"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "ruanzhu" / "deposit"
SHOT = ROOT / "docs" / "ruanzhu" / "screenshots"
HEADER = "育种目标生物逻辑验证系统 V1.0"
FONT_PATH = Path(r"C:\Windows\Fonts\simhei.ttf")
YAHEI = Path(r"C:\Windows\Fonts\msyh.ttc")

SOURCE_FILES = [
    "bio_logic_debugger/__init__.py",
    "bio_logic_debugger/paths.py",
    "bio_logic_debugger/core/domain.py",
    "bio_logic_debugger/core/expr.py",
    "bio_logic_debugger/core/anti_pattern.py",
    "bio_logic_debugger/core/engine.py",
    "bio_logic_debugger/knowledge/rice_knowledge.py",
    "bio_logic_debugger/knowledge/knowledge_store.py",
    "bio_logic_debugger/knowledge/weight_store.py",
    "bio_logic_debugger/knowledge/paper_analyzer.py",
    "bio_logic_debugger/knowledge/pdf_parser.py",
    "bio_logic_debugger/knowledge/doi_fetcher.py",
    "bio_logic_debugger/knowledge/paper_search.py",
    "bio_logic_debugger/llm/reasoner.py",
    "bio_logic_debugger/ui/runtime.py",
    "bio_logic_debugger/ui/pages/validate.py",
    "bio_logic_debugger/ui/pages/browser.py",
    "bio_logic_debugger/ui/pages/anti_patterns.py",
    "bio_logic_debugger/ui/pages/constraints.py",
    "bio_logic_debugger/ui/pages/literature.py",
    "bio_logic_debugger/cli.py",
    "bio_logic_debugger/app.py",
]

LINES_PER_PAGE = 50
FRONT_PAGES = 30
BACK_PAGES = 30


def register_fonts() -> str:
    pdfmetrics.registerFont(TTFont("SimHei", str(FONT_PATH)))
    return "SimHei"


def collect_source() -> list[str]:
    lines: list[str] = []
    for rel in SOURCE_FILES:
        path = ROOT / rel
        text = path.read_text(encoding="utf-8")
        body = [ln.rstrip() for ln in text.splitlines()]
        while body and not body[-1].strip():
            body.pop()
        lines.append(f"# ===== FILE: {rel} =====")
        lines.extend(body)
        lines.append("")
    return lines


def sanitize(line: str) -> str:
    out = []
    for ch in line.replace("\t", "    "):
        o = ord(ch)
        if o > 0xFFFF:
            out.append("?")
        else:
            out.append(ch)
    return "".join(out)


def paginate(lines: list[str], n: int) -> list[list[str]]:
    pages = []
    for i in range(0, len(lines), n):
        pages.append(lines[i:i + n])
    return pages


def draw_code_page(c: canvas.Canvas, page_lines: list[str], page_no: int, total: int, font: str) -> None:
    width, height = A4
    c.setFont(font, 9)
    c.drawString(18 * mm, height - 12 * mm, HEADER)
    c.setFont(font, 8)
    c.drawRightString(width - 18 * mm, height - 12 * mm, f"{page_no}/{total}")
    c.line(18 * mm, height - 14 * mm, width - 18 * mm, height - 14 * mm)
    y = height - 20 * mm
    c.setFont(font, 7)
    for i, line in enumerate(page_lines, 1):
        shown = sanitize(line)
        if len(shown) > 108:
            shown = shown[:108]
        c.drawString(18 * mm, y, f"{i:02d}  {shown}")
        y -= 4.6 * mm
    c.line(18 * mm, 12 * mm, width - 18 * mm, 12 * mm)
    c.setFont(font, 8)
    c.drawCentredString(width / 2, 8 * mm, str(page_no))


def build_source_pdf(font: str) -> Path:
    lines = collect_source()
    pages = paginate(lines, LINES_PER_PAGE)
    front = pages[:FRONT_PAGES]
    back = pages[-BACK_PAGES:] if len(pages) > BACK_PAGES else pages
    selected = front + back
    out = OUT / "源程序-前30页后30页.pdf"
    c = canvas.Canvas(str(out), pagesize=A4)
    total = len(selected)
    for i, pl in enumerate(selected, 1):
        draw_code_page(c, pl, i, total, font)
        c.showPage()
    c.save()
    count_path = OUT / "源程序量.txt"
    py_total = sum(
        len((ROOT / rel).read_text(encoding="utf-8").splitlines())
        for rel in SOURCE_FILES
        if (ROOT / rel).exists()
    )
    count_path.write_text(
        f"交存源程序文件 {len(SOURCE_FILES)} 个，合计 {py_total} 行。\n"
        f"全文 {len(lines)} 行（含文件分隔），共 {len(pages)} 页。\n"
        f"本 PDF 为前 {FRONT_PAGES} 页 + 后 {BACK_PAGES} 页，每页 {LINES_PER_PAGE} 行。\n",
        encoding="utf-8",
    )
    return out


def ui_font(size: int):
    try:
        return ImageFont.truetype(str(YAHEI), size, index=0)
    except OSError:
        return ImageFont.truetype(str(FONT_PATH), size)


def render_terminal(text: str, path: Path, title: str) -> None:
    font = ui_font(16)
    lines = text.replace("\r\n", "\n").split("\n")
    if len(lines) > 48:
        lines = lines[:48]
    pad = 24
    line_h = 22
    w = 1100
    h = pad * 2 + 36 + line_h * max(len(lines), 8)
    img = Image.new("RGB", (w, h), "#0f1419")
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, w, 40), fill="#1c2330")
    draw.text((16, 10), title, font=ui_font(15), fill="#d8dee9")
    y = 56
    for line in lines:
        draw.text((20, y), line[:120], font=font, fill="#e7ecf3")
        y += line_h
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)


def capture_cli_and_tree() -> None:
    SHOT.mkdir(parents=True, exist_ok=True)
    env = dict(**{k: v for k, v in __import__("os").environ.items()})
    env["PYTHONIOENCODING"] = "utf-8"
    listed = subprocess.check_output(
        [sys.executable, "-m", "bio_logic_debugger.cli", "--list-traits"],
        cwd=str(ROOT), env=env,
    ).decode("utf-8", errors="replace")
    render_terminal(listed, SHOT / "13-cli-list-traits.png", "bld --list-traits")
    validated = subprocess.check_output(
        [
            sys.executable, "-m", "bio_logic_debugger.cli",
            "--validate", "rice_plant_height", ">=", "130",
            "--env", "unused=0",
        ],
        cwd=str(ROOT), env=env,
    ).decode("utf-8", errors="replace")
    render_terminal(validated, SHOT / "13b-cli-validate.png", "bld --validate rice_plant_height >= 130")
    demo = subprocess.check_output(
        [sys.executable, "-c", (
            "from bio_logic_debugger.core.domain import BreedingGoal, TraitTarget;"
            "from bio_logic_debugger.core.engine import BioLogicEngine;"
            "from bio_logic_debugger.knowledge.knowledge_store import load_and_merge;"
            "e=BioLogicEngine(); t,c,k,a=load_and_merge();"
            "e.register_traits(t); e.register_correlations(c);"
            "e.register_constraints(k); e.register_anti_patterns(a);"
            "g=BreedingGoal(name='高秆高抗示例');"
            "g.add_target(TraitTarget('rice_plant_height',130,'>='));"
            "g.add_target(TraitTarget('rice_lodging_resistance',2,'<='));"
            "r=e.validate(g); print(r.verdict()); print(r.narrative())"
        )],
        cwd=str(ROOT), env=env,
    ).decode("utf-8", errors="replace")
    render_terminal(demo, SHOT / "05-result.png", "验证结论：高秆 + SES 高抗倒伏")
    tree_lines = []
    for rel in SOURCE_FILES:
        tree_lines.append(rel)
    render_terminal("\n".join(tree_lines), SHOT / "02-source-tree.png", "源程序文件顺序（交存用）")


def wrap_text(text: str, max_chars: int) -> list[str]:
    text = text.strip()
    if not text:
        return [""]
    out = []
    while text:
        out.append(text[:max_chars])
        text = text[max_chars:]
    return out


def build_manual_pdf(font: str) -> Path:
    md = (ROOT / "docs" / "ruanzhu" / "03-软件说明书.md").read_text(encoding="utf-8")
    out = OUT / "软件说明书.pdf"
    c = canvas.Canvas(str(out), pagesize=A4)
    width, height = A4
    page_no = 0

    def new_page():
        nonlocal page_no, y
        if page_no:
            c.showPage()
        page_no += 1
        c.setFont(font, 9)
        c.drawString(18 * mm, height - 12 * mm, HEADER + "  软件说明书")
        c.setFont(font, 8)
        c.drawRightString(width - 18 * mm, height - 12 * mm, str(page_no))
        c.line(18 * mm, height - 14 * mm, width - 18 * mm, height - 14 * mm)
        y = height - 22 * mm

    y = 0
    new_page()
    for raw in md.splitlines():
        line = raw.rstrip()
        if line.startswith("!["):
            continue
        if line.startswith("【截图"):
            name = line.strip("【】")
            # 尝试配图
            key = ""
            if "1" in line and "安装" in line or line.startswith("【截图 1"):
                key = ""
            candidates = {
                "【截图 2": "02-source-tree.png",
                "【截图 3": "03-sidebar.png",
                "【截图 4": "04-targets.png",
                "【截图 5": "05-result.png",
                "【截图 6": "06-violation.png",
                "【截图 7": "07-browser.png",
                "【截图 8": "08-anti-patterns.png",
                "【截图 9": "09-constraints.png",
                "【截图 10": "10-literature.png",
                "【截图 11": "11-extract.png",
                "【截图 12": "12-knowledge.png",
                "【截图 13": "13-cli-list-traits.png",
            }
            img_name = ""
            for prefix, fn in candidates.items():
                if line.startswith(prefix):
                    img_name = fn
                    break
            img_path = SHOT / img_name if img_name else None
            c.setFont(font, 10)
            if y < 70 * mm:
                new_page()
            c.drawString(20 * mm, y, line)
            y -= 7 * mm
            if img_path and img_path.exists():
                ih = 58 * mm
                if y - ih < 18 * mm:
                    new_page()
                c.drawImage(str(img_path), 20 * mm, y - ih, width=170 * mm, height=ih, preserveAspectRatio=True, mask="auto")
                y -= ih + 6 * mm
            continue
        if not line:
            y -= 3 * mm
            continue
        size = 12 if line.startswith("# ") else 11 if line.startswith("## ") else 10
        c.setFont(font, size)
        for part in wrap_text(line.lstrip("# ").strip(), 46 if size >= 11 else 52):
            if y < 18 * mm:
                new_page()
            c.setFont(font, size)
            c.drawString(20 * mm, y, part)
            y -= 5.2 * mm
    c.save()
    return out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    SHOT.mkdir(parents=True, exist_ok=True)
    font = register_fonts()
    capture_cli_and_tree()
    src = build_source_pdf(font)
    man = build_manual_pdf(font)
    print("源程序", src)
    print("说明书", man)
    print("截图目录", SHOT)


if __name__ == "__main__":
    main()
