# -----------------------------------------------------------------------------#
# IMPORT LIBS
# -----------------------------------------------------------------------------#

import re
from datetime import date

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt

# -----------------------------------------------------------------------------#
# DEFINE GLOBAL VARS
# Here we define ppt themes
# -----------------------------------------------------------------------------#
THEME = {
    "bg_title": RGBColor(0x1E, 0x27, 0x61),  # deep navy
    "bg_content": RGBColor(0xFF, 0xFF, 0xFF),  # white
    "accent": RGBColor(0x4C, 0x72, 0xB0),  # blue accent
    "text_light": RGBColor(0xFF, 0xFF, 0xFF),
    "text_dark": RGBColor(0x1E, 0x1E, 0x1E),
    "text_muted": RGBColor(0x55, 0x65, 0x78),
    "bullet_dot": RGBColor(0x4C, 0x72, 0xB0),
}

SLIDE_W = Inches(10)
SLIDE_H = Inches(5.625)


# -----------------------------------------------------------------------------#
# DEF FUNCTIONS
# -----------------------------------------------------------------------------#


def parse_markdown(text: str) -> list[dict]:
    """
    Converts markdown text into a list of slide dicts:
      { "title": str,
        "body": [ {"type": "h2"|"bullet"|"text", "text": str, "level": int} ] }

    Rules:
      - H1 (#)  → new slide, used as the slide title
      - H2 (##) → sub-heading inside a slide body
      - Bullet (-, *, +) → bullet item; nested bullets via leading spaces
      - Numbered list (1.) → bullet item with number type flag
      - Plain paragraph → plain text block
    """
    slides = []
    current: dict | None = None

    for raw_line in text.splitlines():
        line = raw_line.rstrip()

        # H1 → new slide
        m = re.match(r"^#\s+(.*)", line)
        if m:
            current = {"title": m.group(1).strip(), "body": []}
            slides.append(current)
            continue

        if current is None:
            # Content before any H1 → create an untitled slide
            current = {"title": "", "body": []}
            slides.append(current)

        # H2
        m = re.match(r"^##\s+(.*)", line)
        if m:
            current["body"].append(
                {"type": "h2", "text": m.group(1).strip(), "level": 0}
            )
            continue

        # H3
        m = re.match(r"^###\s+(.*)", line)
        if m:
            current["body"].append(
                {"type": "h3", "text": m.group(1).strip(), "level": 0}
            )
            continue

        # Unordered bullet (supports up to 3 indent levels via leading spaces)
        m = re.match(r"^(\s*)[-*+]\s+(.*)", line)
        if m:
            indent = len(m.group(1))
            level = min(indent // 2, 2)
            current["body"].append(
                {"type": "bullet", "text": m.group(2).strip(), "level": level}
            )
            continue

        # Ordered list
        m = re.match(r"^(\s*)\d+\.\s+(.*)", line)
        if m:
            indent = len(m.group(1))
            level = min(indent // 2, 2)
            current["body"].append(
                {"type": "numbered", "text": m.group(2).strip(), "level": level}
            )
            continue

        # Blank line → skip
        if line.strip() == "":
            continue

        # Plain paragraph text
        current["body"].append({"type": "text", "text": line.strip(), "level": 0})

    return slides


# ─────────────────────────── SLIDE BUILDERS ───────────────────────────


def set_background(slide, color: RGBColor):
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = color


def add_title_slide(prs: Presentation, title: str, subtitle: str = ""):
    slide_layout = prs.slide_layouts[6]  # blank
    slide = prs.slides.add_slide(slide_layout)
    set_background(slide, THEME["bg_title"])

    # Title text box
    txBox = slide.shapes.add_textbox(Inches(0.7), Inches(1.8), Inches(8.6), Inches(1.4))
    tf = txBox.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.LEFT
    run = p.add_run()
    run.text = title
    run.font.size = Pt(40)
    run.font.bold = True
    run.font.color.rgb = THEME["text_light"]
    run.font.name = "Helvetica"

    if subtitle:
        p2 = tf.add_paragraph()
        p2.alignment = PP_ALIGN.LEFT
        r2 = p2.add_run()
        r2.text = subtitle
        r2.font.size = Pt(20)
        r2.font.color.rgb = RGBColor(0xCA, 0xDC, 0xFC)
        r2.font.name = "Helvetica"

    # Accent bar at bottom
    slide.shapes.add_shape(
        1,  # MSO_SHAPE_TYPE.RECTANGLE
        Inches(0),
        Inches(5.2),
        Inches(10),
        Inches(0.425),
    ).fill.solid()
    slide.shapes[-1].fill.fore_color.rgb = THEME["accent"]
    slide.shapes[-1].line.fill.background()

    return slide


def add_content_slide(prs: Presentation, slide_data: dict):
    slide_layout = prs.slide_layouts[6]  # blank
    slide = prs.slides.add_slide(slide_layout)
    set_background(slide, THEME["bg_content"])

    title_text = slide_data["title"]
    body_items = slide_data["body"]

    # ── Title bar (accent strip + title text) ──
    bar = slide.shapes.add_shape(1, Inches(0), Inches(0), Inches(10), Inches(0.85))
    bar.fill.solid()
    bar.fill.fore_color.rgb = THEME["bg_title"]
    bar.line.fill.background()

    txTitle = slide.shapes.add_textbox(
        Inches(0.35), Inches(0.05), Inches(9.3), Inches(0.75)
    )
    tf = txTitle.text_frame
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.LEFT
    run = p.add_run()
    run.text = title_text
    run.font.size = Pt(26)
    run.font.bold = True
    run.font.color.rgb = THEME["text_light"]
    run.font.name = "Calibri"

    # ── Body text box ──
    txBody = slide.shapes.add_textbox(
        Inches(0.5), Inches(1.05), Inches(9.0), Inches(4.3)
    )
    tf = txBody.text_frame
    tf.word_wrap = True

    first = True
    counter = [0]  # for numbered lists per level

    for item in body_items:
        itype = item["type"]
        raw = item[
            "text"
        ]  # raw markdown text — inline parsing done inside _style_paragraph
        level = item.get("level", 0)

        if first:
            p = tf.paragraphs[0]
            first = False
        else:
            p = tf.add_paragraph()

        p.level = level

        if itype == "h2":
            _style_paragraph(
                p,
                raw,
                size=20,
                bold=True,
                color=THEME["accent"],
                space_before=12,
                space_after=4,
            )
        elif itype == "h3":
            _style_paragraph(
                p,
                raw,
                size=16,
                bold=True,
                color=THEME["text_muted"],
                space_before=8,
                space_after=2,
            )
        elif itype == "bullet":
            _style_paragraph(
                p,
                raw,
                size=14,
                bold=False,
                color=THEME["text_dark"],
                bullet=True,
                space_before=3,
            )
        elif itype == "numbered":
            counter[0] += 1
            _style_paragraph(
                p,
                f"{counter[0]}. {raw}",
                size=14,
                bold=False,
                color=THEME["text_dark"],
                space_before=3,
            )
        else:  # plain text
            counter[0] = 0
            _style_paragraph(
                p, raw, size=14, bold=False, color=THEME["text_dark"], space_before=6
            )

    return slide


def _parse_inline(text: str) -> list[dict]:
    """
    Parse inline markdown into a list of run dicts:
      {"text": str, "bold": bool, "italic": bool, "code": bool}

    Handles (in priority order):
      ***bold+italic***  /  ___bold+italic___
      **bold**           /  __bold__
      *italic*           /  _italic_
      `code`
      [link text](url)   → renders as plain link text
    """
    runs = []
    # Combined pattern: order matters — longest markers first
    pattern = re.compile(
        r"(\*\*\*|___)(.*?)\1"  # bold+italic  (group 1 & 2)
        r"|(\*\*|__)(.*?)\3"  # bold         (group 3 & 4)
        r"|(\*|_)(.*?)\5"  # italic       (group 5 & 6)
        r"|`(.*?)`"  # code         (group 7)
        r"|\[([^\]]+)\]\([^)]+\)",  # link         (group 8)
        re.DOTALL,
    )
    last = 0
    for m in pattern.finditer(text):
        # Plain text before this match
        if m.start() > last:
            runs.append(
                {
                    "text": text[last : m.start()],
                    "bold": False,
                    "italic": False,
                    "code": False,
                }
            )
        if m.group(1):  # bold+italic
            runs.append(
                {"text": m.group(2), "bold": True, "italic": True, "code": False}
            )
        elif m.group(3):  # bold
            runs.append(
                {"text": m.group(4), "bold": True, "italic": False, "code": False}
            )
        elif m.group(5):  # italic
            runs.append(
                {"text": m.group(6), "bold": False, "italic": True, "code": False}
            )
        elif m.group(7) is not None:  # code
            runs.append(
                {"text": m.group(7), "bold": False, "italic": False, "code": True}
            )
        elif m.group(8):  # link text only
            runs.append(
                {"text": m.group(8), "bold": False, "italic": False, "code": False}
            )
        last = m.end()
    # Remaining plain text
    if last < len(text):
        runs.append(
            {"text": text[last:], "bold": False, "italic": False, "code": False}
        )
    return runs or [{"text": text, "bold": False, "italic": False, "code": False}]


def _style_paragraph(
    p,
    text,
    size=14,
    bold=False,
    color=None,
    bullet=False,
    space_before=0,
    space_after=0,
):
    from lxml import etree
    from pptx.oxml.ns import qn

    p.space_before = Pt(space_before)
    p.space_after = Pt(space_after)

    if bullet:
        pPr = p._p.get_or_add_pPr()
        # buFont has to come before buChar or PowerPoint flags the file
        buFont = etree.SubElement(pPr, qn("a:buFont"))
        buFont.set("typeface", "Arial")
        buChar = etree.SubElement(pPr, qn("a:buChar"))
        buChar.set("char", "•")

    for seg in _parse_inline(text):
        run = p.add_run()
        run.text = seg["text"]
        run.font.size = Pt(size)
        run.font.name = "Consolas" if seg["code"] else "Calibri"
        # Paragraph-level bold (e.g. h2) is merged with inline bold
        run.font.bold = bold or seg["bold"]
        run.font.italic = seg["italic"]
        if seg["code"]:
            run.font.color.rgb = RGBColor(0xC7, 0x25, 0x4E)  # red-ish for inline code
        elif color:
            run.font.color.rgb = color


def convert_md_to_ppt(md_path: str, out_path: str):
    print(f"Convert to ppt: {out_path}")
    with open(md_path, "r", encoding="utf-8") as f:
        md_text = f.read()

    slides_data = parse_markdown(md_text)

    prs = Presentation()
    prs.slide_width = SLIDE_W
    prs.slide_height = SLIDE_H

    # Hardcoded for now since I don't know how much flexibility
    # we will actually need here.
    subtitle = date.today().strftime("%B %d, %Y")
    add_title_slide(prs, "Core Meeting", subtitle)

    for slide_data in slides_data:
        add_content_slide(prs, slide_data)

    prs.save(out_path)
