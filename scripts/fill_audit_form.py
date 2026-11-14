#!/usr/bin/env python3
"""يعبّئ استمارة تدقيق الخطة الدراسية الرسمية.

ترتيب الخلايا في الـXML من اليسار إلى اليمين (الجدول بلا bidiVisual)،
فالفهرس الأكبر هو الخانة اليمنى — وهي الفصل الأول.
"""
import re, sys

DOC = sys.argv[1]
x = open(DOC, encoding="utf-8").read()

FONT = '<w:rFonts w:ascii="Arimo" w:hAnsi="Arimo" w:cs="Arimo" w:eastAsia="Arimo"/>'

def para(text, align="end", size=20, bold=False, rtl=True):
    b = "<w:b/><w:bCs/>" if bold else ""
    r = "<w:rtl/>" if rtl else ""
    t = (text.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;"))
    return (f'<w:p><w:pPr><w:spacing w:after="0" w:before="0" w:line="259" w:lineRule="auto"/>'
            f'<w:ind w:firstLine="0" w:start="0"/><w:jc w:val="{align}"/></w:pPr>'
            f'<w:r><w:rPr>{FONT}{b}<w:color w:val="000000"/>'
            f'<w:sz w:val="{size}"/><w:szCs w:val="{size}"/>{r}</w:rPr>'
            f'<w:t xml:space="preserve">{t}</w:t></w:r></w:p>')

def set_cell(cell, paras):
    """يستبدل فقرات الخلية ويُبقي tcPr (فيه العرض والتظليل)."""
    m = re.match(r'(<w:tc><w:tcPr>.*?</w:tcPr>)', cell, re.S)
    return m.group(1) + "".join(paras) + "</w:tc>"

rows = re.findall(r'<w:tr\b.*?</w:tr>', x, re.S)

# (رقم الصف, فهرس الخلية) -> قائمة الفقرات
PLAN = {}
def put(r, c, lines, align="end", size=20, bold=False, rtl=True):
    PLAN[(r, c)] = [para(t, align, size, bold, rtl) for t in lines]

# ── ترويسة الفصول ──
put(1, 2, ["فصل: خريف 2026/2027"], "end", 22, True)
put(1, 1, ["فصل: ربيع 2026/2027"], "end", 22, True)
put(1, 0, ["فصل: خريف 2027/2028"], "end", 22, True)
put(5, 2, ["فصل: ربيع 2027/2028"], "end", 22, True)

# كل مقرر: (الساعات، أسطره). الأسطر مقطَّعة يدوياً لأن عمود «رمز المقرر»
# ضيّق (1.16 بوصة)؛ وتقطيعها يدوياً يجعل عدد الأسطر معلوماً، فتُحشى خلية
# الساعات بفقرات فارغة بنفس العدد ويبقى كل رقم بحذاء مقرره.
T1 = [("2", ["عربي1060", "اللغة العربية"]),
      ("3", ["ترفن1130", "الخزف 1 (إعادة)"]),
      ("3", ["منطر4027", "طرق تدريس", "التربية الفنية (2)"]),
      ("3", ["ترفن2110", "النسيج بالألياف", "المختلفة"]),
      ("3", ["ترفن3111", "الفن المعاصر"])]
T2 = [("2", ["ترفن4120", "النقد والتذوق", "الفني"]),
      ("3", ["ترفن3170", "جماليات التشكيل", "بالخط العربي"]),
      ("2", ["علنف4500", "المتعلمون ذوو", "الاحتياجات الخاصة"]),
      ("3", ["اصتر3050", "الإدارة والقيادة", "المدرسية"])]
T3 = [("2", ["ترفن4260", "المشروع الفني"]),
      ("3", ["ترفن3250", "تقنيات معاصرة", "في الفن"]),
      ("2", ["ترفن4130", "التثقيف بالفن", "وخدمة المجتمع"]),
      ("2", ["اجمع1005", "عمان: الدولة", "والإنسان"])]
T4 = [("7", ["منطر4600", "التدريب الميداني"]),
      ("2", ["منطر4400", "مشروع التخرج"])]

def course_lines(block):
    """أسطر عمود المقرر: الرمز غامق ثم اسمه، ثم سطر فاصل بين المقررات."""
    out = []
    for _, lines in block:
        out.append((lines[0], True))
        out += [(t, False) for t in lines[1:]]
        out.append(("", False))
    return out[:-1]

def hour_lines(block):
    """أرقام الساعات، مع فراغات تعادل بقية أسطر كل مقرر."""
    out = []
    for hrs, lines in block:
        out.append(hrs)
        out += [""] * (len(lines) - 1)
        out.append("")
    return out[:-1]

def put_block(row, ci_code, ci_hrs, block):
    PLAN[(row, ci_code)] = [para(t, "end", 16, b) for t, b in course_lines(block)]
    PLAN[(row, ci_hrs)]  = [para(t, "center", 16, False, False) for t in hour_lines(block)]

put_block(3, 5, 4, T1)     # خريف 2026/2027 — اليمين
put_block(3, 3, 2, T2)     # ربيع 2026/2027 — الوسط
put_block(3, 1, 0, T3)     # خريف 2027/2028 — اليسار
put_block(7, 6, 5, T4)     # ربيع 2027/2028 — فصل التخرج

# ── المجاميع ──
put(4, 4, ["14"], "center", 22, True, False)
put(4, 2, ["10"], "center", 22, True, False)
put(4, 0, ["9"],  "center", 22, True, False)
put(11, 3, ["9"], "center", 22, True, False)

# ── المعادلة ──
put(7, 2, ["لا يوجد"])

for (ri, ci), paras in PLAN.items():
    cells = re.findall(r'<w:tc>.*?</w:tc>', rows[ri], re.S)
    old = cells[ci]
    new = set_cell(old, paras)
    rows[ri] = rows[ri].replace(old, new, 1)

# أعِد بناء المستند بالصفوف المعدَّلة
orig = re.findall(r'<w:tr\b.*?</w:tr>', x, re.S)
for o, n in zip(orig, rows):
    if o != n:
        x = x.replace(o, n, 1)

# ── حقول الترويسة: استبدال سلاسل النقاط بالقيم ──
HEAD = [("اسم الطالب:", "يوسف صالح عبدالله البلوشي"),
        ("الرقم الجامعي:", "141386"),
        ("التخصص:", "التربية الفنية"),
        ("الدفعة:", "2022"),
        ("فصل توقع التخرج:", "ربيع 2027/2028"),
        ("اسم المرشد الأكاديمي:", "د. سلمان الحجري")]
VAL_KEEP = {"يوسف صالح عبدالله البلوشي":18, "141386":26, "التربية الفنية":40,
            "2022":45, "ربيع 2027/2028":16, "د. سلمان الحجري":32}
for label, val in HEAD:
    # النقاط في run مستقل يلي run العنوان مباشرةً
    pat = re.compile(r'(<w:t[^>]*>\s*' + re.escape(label) + r'\s*</w:t></w:r>)'
                     r'<w:r><w:rPr>((?:(?!</w:rPr>).)*)</w:rPr><w:t[^>]*>\s*\.+\s*</w:t></w:r>', re.S)
    m = pat.search(x)
    if not m:
        print(f"  \u2718 {label}"); continue
    rpr = m.group(2)
    dark = re.sub(r'<w:color w:val="[0-9a-fA-F]{6}"/>', '<w:color w:val="000000"/>', rpr)
    if "<w:b/>" not in dark:
        dark = "<w:b/><w:bCs/>" + dark
    keep = VAL_KEEP.get(val, 20)
    rep = (m.group(1)
           + f'<w:r><w:rPr>{dark}</w:rPr><w:t xml:space="preserve"> {val} </w:t></w:r>'
           + f'<w:r><w:rPr>{rpr}</w:rPr><w:t xml:space="preserve">{"." * keep}</w:t></w:r>')
    x = x[:m.start()] + rep + x[m.end():]
    print(f"  \u2713 {label} \u2190 {val}")

open(DOC, "w", encoding="utf-8").write(x)
print(f"\n✓ كُتب {len(PLAN)} خلية")
