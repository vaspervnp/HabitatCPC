"""Τα εγχειρίδια σε PDF: docs/manual-en.md -> docs/manual-en.pdf, και το ελληνικό.

python3 tools/mkpdf.py [docs/manual-en.md ...]

Θέλει το reportlab (pip install reportlab) και τις γραμματοσειρές Noto Sans και
Noto Sans Mono. Διαβάζει μόνο ό,τι γράφουν τα εγχειρίδια: επικεφαλίδες #/##/###,
παραγράφους, λίστες με - και 1. (και μέσα τους, με δύο κενά), πίνακες με |,
μπλοκ κώδικα με ```, εικόνες σε δική τους γραμμή, και μέσα στο κείμενο
**έντονα**, *πλάγια*, `κώδικα` και [συνδέσμους](#άγκυρα). Οι σύνδεσμοι προς τις
ενότητες γίνονται σύνδεσμοι μέσα στο PDF, και προς το άλλο εγχειρίδιο προς το
δικό του PDF.
"""
import os, re, sys
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, CondPageBreak, Frame, HRFlowable, Image, KeepTogether, PageTemplate,
                                Paragraph, Spacer, Table, TableStyle, XPreformatted)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS = "/usr/share/fonts/truetype/noto"
for name, f in (("Sans", "NotoSans-Regular"), ("Sans-B", "NotoSans-Bold"), ("Sans-I", "NotoSans-Italic"),
                ("Sans-BI", "NotoSans-BoldItalic"), ("Mono", "NotoSansMono-Regular"),
                ("Mono-B", "NotoSansMono-Bold")):
    pdfmetrics.registerFont(TTFont(name, os.path.join(FONTS, f + ".ttf")))
pdfmetrics.registerFontFamily("Sans", normal="Sans", bold="Sans-B", italic="Sans-I", boldItalic="Sans-BI")
pdfmetrics.registerFontFamily("Mono", normal="Mono", bold="Mono-B", italic="Mono", boldItalic="Mono-B")

INK, SOFT, RULE, TINT, LINK = (colors.HexColor(c) for c in ("#1b1b1a", "#5a5955", "#c9c7c0", "#f1f0ec",
                                                            "#1d5fa8"))
BODY = ParagraphStyle("body", fontName="Sans", fontSize=10, leading=14, textColor=INK, spaceAfter=6)
TITLE = ParagraphStyle("title", BODY, fontName="Sans-B", fontSize=24, leading=30, spaceAfter=6)
SUB = ParagraphStyle("sub", BODY, fontName="Sans-I", fontSize=12, leading=16, textColor=SOFT, spaceAfter=10)
H1 = ParagraphStyle("h1", BODY, fontName="Sans-B", fontSize=16, leading=20, spaceBefore=14, spaceAfter=8,
                    keepWithNext=1)
H2 = ParagraphStyle("h2", BODY, fontName="Sans-B", fontSize=12.5, leading=16, spaceBefore=10, spaceAfter=6,
                    keepWithNext=1)
LEAD = ParagraphStyle("lead", BODY, keepWithNext=1)       # «…:» μένει με ό,τι ακολουθεί
CELL = ParagraphStyle("cell", BODY, fontSize=9, leading=12, spaceAfter=0)
HEAD = ParagraphStyle("head", CELL, fontName="Sans-B")
CODE = ParagraphStyle("code", BODY, fontName="Mono", fontSize=8.2, leading=11, spaceAfter=0)
CAPTION = ParagraphStyle("caption", BODY, fontName="Sans-I", fontSize=9, leading=12, textColor=SOFT,
                         alignment=TA_CENTER, spaceAfter=10)


def slug(text):
    """Η άγκυρα μιας επικεφαλίδας όπως τη φτιάχνει το GitHub."""
    t = re.sub(r"[`*]", "", text).strip().lower()
    t = re.sub(r"[^\w\- ]", "", t)
    return t.replace(" ", "-")


def inline(text, other):
    """Η γραμμή του markdown στη γλώσσα των Paragraph του reportlab."""
    spans = []

    def keep(s):
        spans.append(s)
        return f"\x00{len(spans) - 1}\x00"

    def esc(s):
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    text = re.sub(r"`([^`]+)`", lambda m: keep(f'<font name="Mono" size="9">{esc(m.group(1))}</font>'), text)

    def link(m):
        label, href = m.group(1), m.group(2)
        if href.startswith("#"):
            return keep(f'<a href="{href}" color="#1d5fa8">') + label + keep("</a>")
        if href == other + ".md":
            return keep(f'<a href="{other}.pdf" color="#1d5fa8">') + label + keep("</a>")
        return label                        # το README και ό,τι άλλο: μόνο το κείμενο
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", link, text)
    text = esc(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<i>\1</i>", text)
    text = text.replace("→", '<font name="Mono">→</font>')   # το Noto Sans δεν έχει βέλος
    return re.sub("\x00(\\d+)\x00", lambda m: spans[int(m.group(1))], text)


def table(rows, other, width):
    cells = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows]
    head, body = cells[0], [r for r in cells[2:]]
    n = len(head)
    plain = lambda s: len(re.sub(r"[`*]|\]\([^)]*\)|\[", "", s))
    want = [max(plain(r[i]) for r in [head] + body) for i in range(n)]
    want = [min(max(w, 4), 60) for w in want]
    total = sum(want)
    widths = [width * w / total for w in want]
    # ΚΑΜΙΑ ΛΕΞΗ ΔΕΝ ΣΠΑΕΙ: κάθε στήλη τουλάχιστον όσο η μακρύτερη λέξη της, με
    # τα έντονα της κεφαλίδας, και ό,τι λείπει το δίνουν οι φαρδιές αναλογικά.
    def word_w(cell, font):
        words = re.sub(r"\]\([^)]*\)|[\[`*]", " ", cell).split()
        return max([pdfmetrics.stringWidth(w, font, 9) for w in words] or [0])
    least = [max(word_w(head[i], "Sans-B"), *(word_w(r[i], "Sans-B") for r in body if i < len(r))) + 10
             for i in range(n)]
    short = [i for i in range(n) if widths[i] < least[i]]
    if short:
        extra = sum(least[i] - widths[i] for i in short)
        rest = [i for i in range(n) if i not in short]
        for i in short:
            widths[i] = least[i]
        rw = sum(widths[i] for i in rest)
        for i in rest:
            widths[i] -= extra * widths[i] / rw
    data = [[Paragraph(inline(c, other), HEAD) for c in head]]
    data += [[Paragraph(inline(c, other), CELL) for c in r + [""] * (n - len(r))] for r in body]
    t = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), TINT),
        ("LINEBELOW", (0, 0), (-1, 0), 0.8, RULE),
        ("LINEBELOW", (0, 1), (-1, -1), 0.3, RULE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
    return [t, Spacer(1, 8)]


def image(path, alt, base, width):
    img = Image(os.path.join(base, path))
    w, h = img.imageWidth, img.imageHeight
    k = min(width, 13 * cm) / w
    img.drawWidth, img.drawHeight = w * k, h * k
    return [KeepTogether([img, Paragraph(inline(alt, ""), CAPTION)])]


def keep_with_next(story):
    """Μια επικεφαλίδα ή ένα «…:» δεν μένει μόνο στο τέλος σελίδας: με την εικόνα
    που ακολουθεί σε ένα KeepTogether, και πριν από κάτι άλλο αλλαγή σελίδας αν
    δεν μένουν 4 cm. (Το keepWithNext του reportlab δεν έπιανε πριν από
    εικόνες και πίνακες.)"""
    out = []
    for f in story:
        k = len(out)
        while k and isinstance(out[k - 1], Spacer):
            k -= 1
        if isinstance(f, KeepTogether) and k and getattr(out[k - 1], "_lead", False):
            k -= 1
            while k and getattr(out[k - 1], "_lead", False):
                k -= 1
            lead = out[k:]
            del out[k:]
            out.append(KeepTogether(lead + list(f._content)))
            continue
        if getattr(f, "_lead", False) and not (out and getattr(out[-1], "_lead", False)):
            out.append(CondPageBreak(4 * cm))
        out.append(f)
    return out


def convert(md, pdf, title, other):
    base = os.path.dirname(md)
    lines = open(md, encoding="utf-8").read().split("\n")
    width = A4[0] - 4 * cm
    story, para, items = [], [], []
    seen_title = False

    def flush_para():
        if para:
            text = " ".join(para)
            lead = text.rstrip("*").endswith(":")          # και το **…:**
            story.append(Paragraph(inline(text, other), LEAD if lead else BODY))
            story[-1]._lead = lead
            para.clear()

    def flush_items():
        for level, marker, text in items:
            st = ParagraphStyle("li", BODY, leftIndent=14 + 16 * level, bulletIndent=2 + 16 * level,
                                spaceAfter=3)
            story.append(Paragraph(inline(text, other), st, bulletText=marker))
            story[-1]._lead = text.rstrip("*").endswith(":")
        if items:
            story.append(Spacer(1, 4))
        items.clear()

    i = 0
    while i < len(lines):
        ln = lines[i]
        s = ln.strip()
        m_item = re.match(r"^( *)(-|\d+\.) (.*)$", ln)
        if s.startswith("```"):
            flush_para(); flush_items()
            j = i + 1
            while not lines[j].strip().startswith("```"):
                j += 1
            ind = len(ln) - len(ln.lstrip())
            code = "\n".join(l[ind:] for l in lines[i + 1:j])
            x = XPreformatted(code.replace("&", "&amp;").replace("<", "&lt;"), CODE)
            box = Table([[x]], colWidths=[width], hAlign="LEFT")
            box.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), TINT),
                                     ("BOX", (0, 0), (-1, -1), 0.5, RULE),
                                     ("LEFTPADDING", (0, 0), (-1, -1), 8), ("TOPPADDING", (0, 0), (-1, -1), 6),
                                     ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
            story += [box, Spacer(1, 8)]
            i = j + 1
            continue
        if not s:
            flush_para()
            i += 1
            continue
        m_img = re.match(r"^!\[([^\]]*)\]\(([^)]+)\)$", s)
        if m_img:
            flush_para(); flush_items()
            story += image(m_img.group(2), m_img.group(1), base, width)
            i += 1
            continue
        if s.startswith("|"):
            flush_para(); flush_items()
            j = i
            while j < len(lines) and lines[j].strip().startswith("|"):
                j += 1
            story += table(lines[i:j], other, width)
            i = j
            continue
        if s == "---":
            flush_para(); flush_items()
            story.append(HRFlowable(width="100%", thickness=0.6, color=RULE, spaceBefore=6, spaceAfter=10))
            i += 1
            continue
        m_h = re.match(r"^(#{1,3}) (.*)$", ln)
        if m_h:
            flush_para(); flush_items()
            depth, text = len(m_h.group(1)), m_h.group(2)
            if depth == 1 and not seen_title:
                seen_title = True
                story.append(Paragraph(inline(text, other), TITLE))
                if i + 2 < len(lines) and re.match(r"^\*[^*].*\*$", lines[i + 2].strip()):
                    story.append(Paragraph(inline(lines[i + 2].strip()[1:-1], other), SUB))
                    i += 3
                    continue
            else:
                st = H1 if depth <= 2 else H2
                key = slug(text)
                story.append(Paragraph(f'<a name="{key}"/>' + inline(text, other), st))
                story[-1]._bookmark = (key, text, depth)
                story[-1]._lead = True
            i += 1
            continue
        if m_item:
            flush_para()
            level = len(m_item.group(1)) // 2
            marker = "•" if m_item.group(2) == "-" else m_item.group(2)
            items.append([level, marker, m_item.group(3)])
            i += 1
            continue
        if items and ln.startswith(" "):          # η συνέχεια του στοιχείου
            items[-1][2] += " " + s
            i += 1
            continue
        flush_items()
        para.append(s)
        i += 1
    flush_para(); flush_items()
    story = keep_with_next(story)

    class Doc(BaseDocTemplate):
        def afterFlowable(self, f):
            b = getattr(f, "_bookmark", None)
            if b:
                key, text, depth = b
                self.canv.bookmarkPage(key)
                self.canv.addOutlineEntry(re.sub(r"[`*]", "", text), key, level=max(0, depth - 2))

    def page(c, d):
        c.saveState()
        c.setFont("Sans", 8)
        c.setFillColor(SOFT)
        c.drawString(2 * cm, 1.2 * cm, title)
        c.drawRightString(A4[0] - 2 * cm, 1.2 * cm, str(d.page))
        c.restoreState()

    doc = Doc(pdf, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=1.8 * cm,
              bottomMargin=2 * cm, title=title, author="Habitat", subject="Habitat for the Amstrad CPC 6128")
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="f")
    doc.addPageTemplates([PageTemplate("p", [frame], onPage=page)])
    doc.build(story)


def main():
    mds = sys.argv[1:] or [os.path.join(ROOT, "docs", f) for f in ("manual-en.md", "manual-el.md")]
    for md in mds:
        lang = "el" if md.endswith("-el.md") else "en"
        other = "manual-en" if lang == "el" else "manual-el"
        first = open(md, encoding="utf-8").readline()[2:].strip()
        pdf = md[:-3] + ".pdf"
        convert(md, pdf, first, other)
        print(pdf, os.path.getsize(pdf))


if __name__ == "__main__":
    main()
