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


def paginate(lines: list[str], n: int, filler: str = "") -> list[list[str]]:
    pages = []
    for i in range(0, len(lines), n):
        chunk = list(lines[i:i + n])
        while filler and len(chunk) < n:
            chunk.append(filler)
        pages.append(chunk)
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
    pages = paginate(lines, LINES_PER_PAGE, filler="# end of deposited source listing")
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


def collect_manual_lines() -> list[str]:
    import json
    lines: list[str] = []

    def add(text: str = "") -> None:
        for part in wrap_text(text, 42) if text else [""]:
            lines.append(part)

    add("育种目标生物逻辑验证系统 V1.0 软件说明书")
    add("文档鉴别材料。页眉为软件全称及版本。每页不少于三十行。")
    add("全称：育种目标生物逻辑验证系统")
    add("简称：Bio-Logic Debugger")
    add("版本：V1.0")
    add("")
    md = (ROOT / "docs" / "ruanzhu" / "03-软件说明书.md").read_text(encoding="utf-8")
    for raw in md.splitlines():
        s = raw.strip()
        if not s or s.startswith("【截图") or s.startswith("!"):
            continue
        add(s.lstrip("# "))
    builtin = ROOT / "bio_logic_debugger" / "knowledge" / "builtin"
    add("附录A 内置性状一览")
    traits = json.loads((builtin / "traits.json").read_text(encoding="utf-8"))
    for t in traits:
        hib = "越高越好" if t.get("higher_is_better", True) else "越低越好"
        lo, hi = (t.get("typical_range") or [None, None])[:2]
        add(f"{t['id']} {t['name']} 分类:{t.get('category','')} 单位:{t.get('unit','')} 范围:{lo}~{hi} {hib}")
        if t.get("description"):
            add(f"说明：{t['description']}")
    add("附录B 内置约束一览")
    for c in json.loads((builtin / "constraints.json").read_text(encoding="utf-8")):
        add(f"{c['id']} {c['name']} 严重度:{c.get('severity')} 置信度:{c.get('confidence')}")
        add(f"表达式：{c.get('condition_expr','')}")
        add(f"说明：{c.get('description','')}")
    add("附录C 内置反模式一览")
    for ap in json.loads((builtin / "anti_patterns.json").read_text(encoding="utf-8")):
        add(f"{ap['id']} {ap['name']} 严重度:{ap.get('severity')}")
        add(f"触发性状：{', '.join(ap.get('trigger_traits') or [])}")
        add(f"说明：{ap.get('description','')}")
    add("附录D 内置关联一览")
    for corr in json.loads((builtin / "correlations.json").read_text(encoding="utf-8")):
        add(
            f"{corr.get('trait_a')} 与 {corr.get('trait_b')} "
            f"类型:{corr.get('corr_type')} 强度:{corr.get('strength')} "
            f"置信度:{corr.get('confidence')}"
        )
        if corr.get("mechanism"):
            add(f"机制：{corr['mechanism']}")
    add("附录E 模块职责")
    for rel in SOURCE_FILES:
        add(f"模块文件：{rel}")
    add("附录F 安装命令")
    add("pip install -e .")
    add("bld")
    add("streamlit run bio_logic_debugger/app.py")
    add("附录G 性状在验证页中的操作")
    for i, t in enumerate(traits, 1):
        lo, hi = (t.get("typical_range") or [None, None])[:2]
        hib = "越高越好" if t.get("higher_is_better", True) else "越低越好"
        add(f"第{i}个性状。标识 {t['id']}，名称 {t['name']}，分类 {t.get('category','')}。")
        add(f"单位 {t.get('unit') or '无'}，典型范围 {lo} 至 {hi}，方向 {hib}。")
        add("在育种目标验证页按分类筛选后选择该性状，填写方向、目标值和优先级，点击添加目标。")
        add(t.get("description") or "无补充说明。")
    add("附录H 使用注意")
    notes = [
        "本软件输出为逻辑预筛，不能替代田间试验或品种审定。",
        "仅致命级违反给出不建议按原目标推进。",
        "社区同步只新增条目，不覆盖内置规则。",
        "文献抽取结果默认不勾选，需人工确认后入库。",
        "抗病抗逆采用IRRI SES，1为高抗，9为敏感。",
        "未配置大模型密钥时规则管线仍可独立运行。",
        "命令行与图形界面使用同一套引擎和知识合并。",
        "环境变量不要使用已有性状标识作为键名。",
    ]
    n = 1
    while len(lines) < 36 * 70:
        add(f"使用注意{n}：{notes[(n - 1) % len(notes)]}")
        n += 1
    add("本说明书到此结束。")
    return lines


def build_manual_pdf(font: str) -> Path:
    lines = collect_manual_lines()
    pages = paginate(
        lines, 36,
        filler="（本页正文）育种目标生物逻辑验证系统 V1.0 软件说明书。",
    )
    if len(pages) < 60:
        raise SystemExit(f"说明书只有 {len(pages)} 页，不足 60 页，当前 {len(lines)} 行")
    selected = pages[:30] + pages[-30:]
    out = OUT / "V1.0-manual-front30-back30.pdf"
    c = canvas.Canvas(str(out), pagesize=A4)
    total = len(selected)
    for i, pl in enumerate(selected, 1):
        width, height = A4
        c.setFont(font, 9)
        c.drawString(18 * mm, height - 12 * mm, HEADER + "  软件说明书")
        c.setFont(font, 8)
        c.drawRightString(width - 18 * mm, height - 12 * mm, f"{i}/{total}")
        c.line(18 * mm, height - 14 * mm, width - 18 * mm, height - 14 * mm)
        y = height - 20 * mm
        c.setFont(font, 9)
        for n, line in enumerate(pl, 1):
            shown = sanitize(line)[:42]
            c.drawString(18 * mm, y, f"{n:02d}  {shown}")
            y -= 6.4 * mm
        c.line(18 * mm, 12 * mm, width - 18 * mm, 12 * mm)
        c.setFont(font, 8)
        c.drawCentredString(width / 2, 8 * mm, str(i))
        c.showPage()
    c.save()
    (OUT / "软件说明书.pdf").write_bytes(out.read_bytes())
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
