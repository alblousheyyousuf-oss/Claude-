#!/usr/bin/env python3
"""Build a university report (.docx) from one Markdown file.

    python3 build_report.py report.md -o report.docx [--preview OUT_DIR]

The Markdown file starts with a YAML front-matter block (cover page data and
layout settings) followed by the report body. See `../assets/report-template-ar.md`
and `../assets/report-template-en.md` for every supported key and block.

Arabic reports are written with `ArabicDocx` from the `arabic-docx` skill
(MIT, installed next to this skill), which handles RTL direction flags,
complex-script fonts and mixed Arabic/Latin runs. English reports use
`LatinDocx`, a left-to-right subclass of the same builder, so both languages
share one tested implementation of captions, TOC, page numbers and tables.

Supported body syntax
---------------------
    # Heading 1 / ## Heading 2 / ### Heading 3 / #### Heading 4
    # Abstract {-}            -> unnumbered heading (also automatic for
                                 Abstract, References, Appendix, الملخص, المراجع …)
    Plain paragraphs, **bold**, *italic*
    - bullet / * bullet       -> bulleted list
    1. item                   -> numbered list (restarts at 1 for every list)
    > quotation               -> indented block quotation
    | a | b |  (pipe table)   -> table; caption from a line `Table: …` or
                                 `جدول: …` directly above or below it
    ![caption](img.png){width=12}  -> centred figure, numbered caption below
    [TOC]                     -> table of contents here (else after the cover)
    \\newpage                  -> page break
    Under a References / المراجع heading every paragraph or list item becomes
    a reference entry with a hanging indent; an English entry inside an Arabic
    report is laid out left-to-right.

Requires python-docx and PyYAML; --preview also needs LibreOffice or Word.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ARABIC_DOCX_DIR = HERE.parent.parent / "arabic-docx" / "scripts"
sys.path.insert(0, str(ARABIC_DOCX_DIR))

try:
    import yaml
    from docx.oxml.ns import qn
    from docx.shared import Cm, Pt, RGBColor
    from arabic_docx import (ArabicDocx, _add_field, _flag, _sub, _unflag,
                             audit_docx, preview)
except ImportError as exc:  # pragma: no cover - environment message
    sys.exit(f"Missing dependency ({exc}). Install: pip install python-docx pyyaml "
             f"and keep the arabic-docx skill at {ARABIC_DOCX_DIR.parent}")

ARABIC = re.compile(r"[؀-ۿݐ-ݿࢠ-ࣿﭐ-﷿ﹰ-﻿]")

LABELS = {
    "ar": dict(toc="المحتويات", lof="قائمة الأشكال", lot="قائمة الجداول",
               figure="الشكل", table="الجدول", prepared_by="إعداد",
               student_id="الرقم الجامعي", submitted_to="مقدَّم إلى",
               course="المقرر", semester="الفصل الدراسي", date="التاريخ",
               section="الشعبة", missing="صورة غير موجودة"),
    "en": dict(toc="Table of Contents", lof="List of Figures", lot="List of Tables",
               figure="Figure", table="Table", prepared_by="Prepared by",
               student_id="Student ID", submitted_to="Submitted to",
               course="Course", semester="Semester", date="Date",
               section="Section", missing="Missing image"),
}

UNNUMBERED = {
    "abstract", "executive summary", "summary", "acknowledgements", "acknowledgments",
    "declaration", "dedication", "references", "reference list", "bibliography",
    "works cited", "list of abbreviations", "glossary", "table of contents",
    "الملخص", "ملخص", "المستخلص", "مستخلص", "الملخص التنفيذي", "شكر وتقدير",
    "الشكر والتقدير", "الإهداء", "إهداء", "الإقرار", "إقرار", "المراجع",
    "قائمة المراجع", "المصادر والمراجع", "المصادر", "قائمة المختصرات", "المختصرات",
    "المحتويات",
}
REFERENCE_HEADINGS = {
    "references", "reference list", "bibliography", "works cited",
    "المراجع", "قائمة المراجع", "المصادر والمراجع", "المصادر", "المراجع والمصادر",
}
APPENDIX = re.compile(r"^(appendix|appendices|ملحق|الملحق|الملاحق|ملاحق)\b", re.I)


# --------------------------------------------------------------------------
# Left-to-right variant of the arabic-docx builder
# --------------------------------------------------------------------------

class LatinDocx(ArabicDocx):
    """ArabicDocx with every RTL switch turned off.

    Keeps the builder's fields, captions, TOC cache, table geometry and
    complex-script font slots (an Arabic name in an English report still
    renders correctly), but paragraphs, tables and sections run left to right.
    """

    CAPTIONS = {"figure": "Figure", "table": "Table"}

    def _patch_styles(self):
        super()._patch_styles()
        ppr = (self.doc.styles.element.find(qn("w:docDefaults"))
               .find(qn("w:pPrDefault")).find(qn("w:pPr")))
        _unflag(ppr, "w:bidi")

    def _patch_sections(self):
        pass

    def _rtl_para(self, p, align="start"):
        align = {"left": "start", "right": "end", "centre": "center",
                 "justify": "both"}.get(align, align)
        ppr = p._p.get_or_add_pPr()
        _unflag(ppr, "w:bidi")
        _flag(ppr, "w:jc", align)
        return p

    def caption(self, text, kind="figure", label=None):
        return super().caption(text, kind, label or self.CAPTIONS.get(kind, kind))

    def table(self, *args, **kwargs):
        super().table(*args, **kwargs)
        _unflag(self.doc.tables[-1]._tbl.tblPr, "w:bidiVisual")
        return self


# --------------------------------------------------------------------------
# Markdown subset parser
# --------------------------------------------------------------------------

HEADING = re.compile(r"^(#{1,4})\s+(.+?)\s*#*\s*$")
IMAGE = re.compile(r"^!\[(.*?)\]\((.+?)\)(?:\{\s*width\s*=\s*([\d.]+)\s*(?:cm)?\s*\})?\s*$")
BULLET = re.compile(r"^\s*[-*+]\s+(.*)$")
NUMBER = re.compile(r"^\s*\d+[.)]\s+(.*)$")
CAPTION = re.compile(r"^(?:Table|جدول|الجدول)\s*[:：]\s*(.+)$", re.I)
TOC_MARK = {"[toc]", "[[toc]]", "<!-- toc -->"}
BREAK_MARK = {"\\newpage", "\\pagebreak", "<!-- pagebreak -->"}


def split_front_matter(text):
    if text.startswith("﻿"):
        text = text[1:]
    if not text.startswith("---"):
        return {}, text
    end = re.search(r"^---\s*$", text[3:], re.M)
    if not end:
        return {}, text
    meta = yaml.safe_load(text[3:3 + end.start()]) or {}
    return meta, text[3 + end.end():]


def _starts_block(s):
    return (HEADING.match(s) or IMAGE.match(s) or BULLET.match(s) or NUMBER.match(s)
            or s.startswith("|") or s.startswith(">") or s.lower() in TOC_MARK
            or s in BREAK_MARK)


def _row(line):
    cells = line.strip().strip("|").split("|")
    return [c.strip() for c in cells]


def parse_blocks(body):
    lines = body.splitlines()
    blocks, i, n = [], 0, len(lines)
    while i < n:
        s = lines[i].strip()
        if not s:
            i += 1
            continue
        if s.startswith("<!--") and s not in BREAK_MARK and s.lower() not in TOC_MARK:
            while i < n and "-->" not in lines[i]:      # skip guidance comments
                i += 1
            i += 1
            continue
        if s.lower() in TOC_MARK:
            blocks.append(("toc",)); i += 1; continue
        if s in BREAK_MARK:
            blocks.append(("break",)); i += 1; continue
        m = HEADING.match(s)
        if m:
            text = m.group(2)
            unnumbered = bool(re.search(r"\{\s*(-|\.unnumbered)\s*\}\s*$", text))
            text = re.sub(r"\s*\{\s*(-|\.unnumbered)\s*\}\s*$", "", text)
            blocks.append(("heading", len(m.group(1)), text, unnumbered)); i += 1; continue
        m = IMAGE.match(s)
        if m:
            width = float(m.group(3)) if m.group(3) else None
            blocks.append(("image", m.group(1), m.group(2), width)); i += 1; continue
        if s.startswith("|"):
            rows = []
            while i < n and lines[i].strip().startswith("|"):
                cells = _row(lines[i])
                if not all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
                    rows.append(cells)
                i += 1
            caption = None
            if blocks and blocks[-1][0] == "para" and CAPTION.match(blocks[-1][1]):
                caption = CAPTION.match(blocks.pop()[1]).group(1)
            else:
                j = i
                while j < n and not lines[j].strip():
                    j += 1
                if j < n and CAPTION.match(lines[j].strip()):
                    caption = CAPTION.match(lines[j].strip()).group(1)
                    i = j + 1
            if rows:
                width = max(len(r) for r in rows)
                rows = [r + [""] * (width - len(r)) for r in rows]
                blocks.append(("table", rows[0], rows[1:], caption))
            continue
        if BULLET.match(s) or NUMBER.match(s):
            kind = "bullets" if BULLET.match(s) else "numbered"
            pattern = BULLET if kind == "bullets" else NUMBER
            items = []
            while i < n and lines[i].strip():
                line = lines[i]
                m = pattern.match(line)
                if m:
                    items.append(m.group(1).strip())
                elif items and not _starts_block(line.strip()):
                    items[-1] += " " + line.strip()      # wrapped continuation
                else:
                    break
                i += 1
            blocks.append((kind, items)); continue
        if s.startswith(">"):
            parts = []
            while i < n and lines[i].strip().startswith(">"):
                parts.append(lines[i].strip()[1:].strip()); i += 1
            blocks.append(("quote", " ".join(p for p in parts if p))); continue
        parts = [s]; i += 1
        while i < n and lines[i].strip() and not _starts_block(lines[i].strip()):
            parts.append(lines[i].strip()); i += 1
        blocks.append(("para", " ".join(parts)))
    return blocks


INLINE = re.compile(r"(\*\*[^*]+?\*\*|\*[^*\s][^*]*?\*)")


def inline_segments(text):
    """'a **b** *c*' -> [('a ', False, False), ('b', True, False), …]."""
    out = []
    for part in INLINE.split(text):
        if not part:
            continue
        if part.startswith("**") and part.endswith("**") and len(part) > 4:
            out.append((part[2:-2], True, False))
        elif part.startswith("*") and part.endswith("*") and len(part) > 2:
            out.append((part[1:-1], False, True))
        else:
            out.append((part, False, False))
    return out


def plain(text):
    return "".join(seg for seg, _, _ in inline_segments(text))


# --------------------------------------------------------------------------
# Report builder
# --------------------------------------------------------------------------

class Report:
    def __init__(self, meta, base_dir):
        self.meta, self.base = meta, base_dir
        title = str(meta.get("title", ""))
        self.lang = str(meta.get("lang") or ("ar" if ARABIC.search(title) else "en"))[:2]
        if self.lang not in LABELS:
            sys.exit(f"lang must be 'ar' or 'en', got {self.lang!r}")
        self.L = LABELS[self.lang]
        self.rtl = self.lang == "ar"
        font = meta.get("font", "Times New Roman")
        cs_font = meta.get("cs_font", "Simplified Arabic" if self.rtl else font)
        self.size = float(meta.get("size", 14 if self.rtl else 12))
        cls = ArabicDocx if self.rtl else LatinDocx
        if meta.get("template"):
            self.doc = cls.from_template(self._path(meta["template"]), clear_body=True,
                                         clear_headers=True, cs_font=cs_font,
                                         latin_font=font, size=self.size)
        else:
            self.doc = cls(cs_font=cs_font, latin_font=font, size=self.size)
            self._page_setup()
        self._styles()
        self.counters = [0, 0, 0, 0]
        self.pending_break = False
        self.unnumbered_chapter = False
        self.refs_level = None
        self.words = 0
        self.toc_done = False
        self.warnings = []

    # -- setup -------------------------------------------------------------

    def _path(self, value):
        p = Path(str(value))
        return p if p.is_absolute() else (self.base / p)

    def _page_setup(self):
        sec = self.doc.doc.sections[0]
        if str(self.meta.get("page_size", "A4")).lower() == "letter":
            sec.page_width, sec.page_height = Cm(21.59), Cm(27.94)
        else:
            sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
        m = float(self.meta.get("margins_cm", 2.5))
        sec.left_margin = sec.right_margin = sec.top_margin = sec.bottom_margin = Cm(m)

    def _styles(self):
        styles = self.doc.doc.styles
        normal = styles["Normal"].paragraph_format
        normal.line_spacing = float(self.meta.get("line_spacing", 1.5))
        normal.space_after = Pt(6)
        black = RGBColor(0, 0, 0)
        for name in ("Heading 1", "Heading 2", "Heading 3", "Heading 4", "Title",
                     "TOC Heading", "Caption"):
            try:
                st = styles[name]
            except KeyError:
                continue
            st.font.color.rgb = black
            if name == "Caption":
                st.font.italic = False
            st.paragraph_format.line_spacing = 1.15

    @property
    def text_width_cm(self):
        sec = self.doc.doc.sections[-1]
        return (sec.page_width - sec.left_margin - sec.right_margin) / 360000

    # -- low-level paragraph helpers ---------------------------------------

    def _ltr(self, p, align="start"):
        ppr = p._p.get_or_add_pPr()
        _unflag(ppr, "w:bidi")
        _flag(ppr, "w:jc", align)

    def _rich(self, p, text, bold=False, italic=False, size=None):
        for seg, b, it in inline_segments(text):
            self.doc._add_runs(p, seg, bold=bold or b, italic=italic or it, size=size)
        return p

    def _para(self, text, align=None, bold=False, italic=False, size=None,
              count=True, style=None):
        self._flush_break()
        p = self.doc._new_p(style)
        body = align is None
        justify = self.meta.get("justify", True)
        align = align or ("both" if justify else "start")
        indent = float(self.meta.get("first_line_indent_cm") or 0)
        if body and indent:
            p.paragraph_format.first_line_indent = Cm(indent)
        self.doc._rtl_para(p, align=align)
        if self.rtl and not ARABIC.search(text) and len(text.split()) >= 3:
            self._ltr(p, align if align in ("both", "center") else "start")
        self._rich(p, text, bold=bold, italic=italic, size=size)
        if count:
            self.words += len(plain(text).split())
        return p

    def _flush_break(self):
        if self.pending_break:
            self.pending_break = False
            self.doc.page_break()

    def _hanging(self, p, rtl):
        ind = _sub(p._p.get_or_add_pPr(), "w:ind")
        ind.set(qn("w:start" if rtl else "w:left"), "720")
        ind.set(qn("w:hanging"), "720")

    # -- cover -------------------------------------------------------------

    def cover(self):
        m, L, s = self.meta, self.L, self.size
        center = lambda text, **kw: self._para(str(text), align="center", count=False, **kw)
        if m.get("logo"):
            logo = self._path(m["logo"])
            if logo.exists():
                self.doc.figure(logo, width_cm=float(m.get("logo_width_cm", 4)))
            else:
                self.warnings.append(f"logo not found: {logo}")
        for key, extra, bold in (("university", 4, True), ("college", 2, True),
                                 ("department", 1, False)):
            if m.get(key):
                center(m[key], size=s + extra, bold=bold)
        self.doc.spacer(48)
        if m.get("report_type"):
            center(m["report_type"], size=s + 1, italic=True)
        if m.get("title"):
            center(m["title"], size=s + 10, bold=True)
        if m.get("subtitle"):
            center(m["subtitle"], size=s + 2)
        self.doc.spacer(48)
        if m.get("course"):
            center(f"**{L['course']}:** {m['course']}")
        if m.get("section"):
            center(f"**{L['section']}:** {m['section']}")
        authors = m.get("authors") or ([m["author"]] if m.get("author") else [])
        if authors:
            self.doc.spacer(12)
            center(f"**{m.get('prepared_by_label', L['prepared_by'])}**")
            for a in authors:
                if isinstance(a, dict):
                    line = str(a.get("name", ""))
                    if a.get("id"):
                        line += f" — {L['student_id']}: {a['id']}"
                else:
                    line = str(a)
                center(line)
        if m.get("instructor"):
            self.doc.spacer(12)
            center(f"**{m.get('instructor_label', L['submitted_to'])}**")
            center(m["instructor"])
        self.doc.spacer(24)
        if m.get("semester"):
            center(f"{L['semester']}: {m['semester']}")
        if m.get("date"):
            d = m["date"]
            d = d.isoformat() if isinstance(d, (_dt.date, _dt.datetime)) else d
            center(f"{L['date']}: {d}")
        self.pending_break = True

    # -- blocks ------------------------------------------------------------

    def toc(self):
        self._flush_break()
        self.doc.toc(title=self.L["toc"])
        for flag, label, seq in (("list_of_figures", "lof", "figure"),
                                 ("list_of_tables", "lot", "table")):
            if self.meta.get(flag):
                t = self.doc._new_p("TOC Heading")
                self.doc._rtl_para(t)
                self.doc._add_runs(t, self.L[label], bold=True, size=self.size + 4)
                t.paragraph_format.page_break_before = True
                p = self.doc._new_p()
                self.doc._rtl_para(p)
                _add_field(p, f'TOC \\h \\z \\c "{self.L[seq]}"',
                           "حدِّث الحقول لعرض القائمة" if self.rtl else
                           "Update fields (F9) to show this list")
        self.toc_done = True
        self.pending_break = True

    def heading(self, level, text, unnumbered):
        key = plain(text).strip().lower()
        if level == 1:
            self.unnumbered_chapter = bool(unnumbered or key in UNNUMBERED or APPENDIX.match(key))
        if self.refs_level is not None and level <= self.refs_level:
            self.refs_level = None
        if key in REFERENCE_HEADINGS:
            self.refs_level = level
        numbered = (self.meta.get("number_headings", True) and not unnumbered
                    and key not in UNNUMBERED and not self.unnumbered_chapter
                    and self.refs_level is None)
        label = plain(text)
        if numbered:
            self.counters[level - 1] += 1
            for k in range(level, 4):
                self.counters[k] = 0
            nums = [str(c) for c in self.counters[:level]]
            label = (nums[0] + "." if level == 1 else ".".join(nums)) + " " + label
        brk = self.pending_break or (level == 1 and self.meta.get("chapter_page_break", True))
        self.pending_break = False
        self.doc.heading(label, level=level, page_break=brk)
        if self.rtl and not ARABIC.search(label):
            self._ltr(self.doc.doc.paragraphs[-1])

    def reference(self, text):
        self._flush_break()
        p = self.doc._new_p()
        self.doc._rtl_para(p, align="start")
        rtl = self.rtl and bool(ARABIC.search(text))
        if self.rtl and not rtl:
            self._ltr(p)
        self._rich(p, text)
        self._hanging(p, rtl)
        p.paragraph_format.space_after = Pt(6)

    def list_(self, items, numbered):
        if self.refs_level is not None:
            for it in items:
                self.reference(it)
            return
        self._flush_break()
        style = "List Number" if numbered else "List Bullet"
        num_id = self._restart_numbering() if numbered else None
        for it in items:
            p = self.doc._new_p(style)
            self.doc._rtl_para(p)
            if self.rtl and not ARABIC.search(it) and len(it.split()) >= 3:
                self._ltr(p)
            if num_id is not None:
                numpr = p._p.get_or_add_pPr().get_or_add_numPr()
                numpr.get_or_add_ilvl().val = 0
                numpr.get_or_add_numId().val = num_id
            self._rich(p, it)
            self.words += len(plain(it).split())

    def _restart_numbering(self):
        """New w:num for each numbered list, so every list starts at 1."""
        try:
            numbering = self.doc.doc.part.numbering_part.element
            style = self.doc.doc.styles["List Number"]
            num_id = style.element.pPr.numPr.numId.val
            num = numbering.xpath(f'./w:num[@w:numId="{num_id}"]')[0]
            new = numbering.add_num(num.abstractNumId.val)
            new.add_lvlOverride(ilvl=0).add_startOverride(1)
            return new.numId
        except Exception:      # template without numbering: Word's own default
            return None

    def quote(self, text):
        p = self._para(text, align="start")
        p.paragraph_format.left_indent = Cm(1.27)
        p.paragraph_format.right_indent = Cm(1.27)

    def table(self, header, rows, caption):
        self._flush_break()
        cols = len(header)
        lengths = [max(4, min(40, max(len(plain(r[c])) for r in [header] + rows)))
                   for c in range(cols)]
        total = sum(lengths)
        widths = [round(self.text_width_cm * l / total, 2) for l in lengths]
        self.doc.table([plain(h) for h in header], [[plain(c) for c in r] for r in rows],
                       widths, caption=caption, header_fill="D9D9D9")
        t = self.doc.doc.tables[-1]
        for row in t.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    p.paragraph_format.line_spacing = 1.0
                    p.paragraph_format.space_after = Pt(2)
        self.doc.spacer(6)

    def image(self, caption, path, width):
        self._flush_break()
        img = self._path(path)
        if not img.exists():
            self.warnings.append(f"image not found: {img}")
            self._para(f"[{self.L['missing']}: {path}]", align="center", count=False)
            return
        if caption and str(self.meta.get("figure_caption", "below")).lower() == "above":
            self.doc.caption(caption, kind="figure")              # APA 7: number and title above
            self.doc.doc.paragraphs[-1].paragraph_format.keep_with_next = True
            self.doc.figure(img, caption=None, width_cm=width)
        else:
            self.doc.figure(img, caption=caption or None, width_cm=width)

    def header_footer(self):
        if self.meta.get("header_text"):
            for sec in self.doc.doc.sections:
                hdr = sec.header
                hdr.is_linked_to_previous = False
                p = hdr.paragraphs[0] if hdr.paragraphs else hdr.add_paragraph()
                self.doc._rtl_para(p, align="center")
                self.doc._add_runs(p, str(self.meta["header_text"]), size=self.size - 2)
        self.doc.page_numbers(align="center", skip_first=self.meta.get("cover", True),
                              start=0 if self.meta.get("cover", True) else None)

    # -- driver --------------------------------------------------------------

    def build(self, blocks, out):
        if self.meta.get("cover", True):
            self.cover()
        wants_toc = self.meta.get("toc", True)
        has_marker = any(b[0] == "toc" for b in blocks)
        if wants_toc and not has_marker:
            self.toc()
        for b in blocks:
            kind = b[0]
            if kind == "toc":
                if wants_toc and not self.toc_done:
                    self.toc()
            elif kind == "break":
                self.pending_break = True
            elif kind == "heading":
                self.heading(b[1], b[2], b[3])
            elif kind == "para":
                if self.refs_level is not None:
                    self.reference(b[1])
                else:
                    self._para(b[1])
            elif kind == "bullets":
                self.list_(b[1], numbered=False)
            elif kind == "numbered":
                self.list_(b[1], numbered=True)
            elif kind == "quote":
                self.quote(b[1])
            elif kind == "table":
                self.table(b[1], b[2], b[3])
            elif kind == "image":
                self.image(b[1], b[2], b[3])
        self.header_footer()
        self.doc.save(out)
        return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("markdown", type=Path)
    ap.add_argument("-o", "--output", type=Path)
    ap.add_argument("--preview", type=Path, metavar="DIR",
                    help="render every page to PNG in DIR (LibreOffice or Word)")
    args = ap.parse_args(argv)

    text = args.markdown.read_text(encoding="utf-8")
    meta, body = split_front_matter(text)
    out = args.output or args.markdown.with_suffix(".docx")
    out.parent.mkdir(parents=True, exist_ok=True)
    report = Report(meta, args.markdown.resolve().parent)
    report.build(parse_blocks(body), out)
    print(f"written: {out}")
    print(f"language: {report.lang} | body words (excluding cover and references): {report.words}")
    if meta.get("word_limit"):
        limit = int(meta["word_limit"])
        print(f"word limit: {limit} ({report.words - limit:+d})")
    for w in report.warnings:
        print(f"warning: {w}")
    if report.rtl:
        findings = audit_docx(out)
        print("audit: clean" if not findings else "audit findings:\n  " + "\n  ".join(map(str, findings)))
    if args.preview:
        pages = preview(out, args.preview)
        print(f"preview: {len(pages) if pages else 0} page(s) in {args.preview}")


if __name__ == "__main__":
    main()
