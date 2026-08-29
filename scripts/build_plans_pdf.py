#!/usr/bin/env python3
"""وثيقة الخطط وحدها — استمارة تدقيق مقررات مملوءة لكل تشكيلة، لا أكثر.

صفحة واحدة لكل تشكيلة، بنفس تخطيط استمارة «ملخص تدقيق الخطة الدراسية»
الرسمية: خانة لكل فصل، فيها المقررات وساعاتها ومجموعها. لا تحليل ولا
جداول أسبوعية ولا رسوم — الجداول فقط.

الترتيب: من الأسرع تخرّجاً إلى الأبطأ.
"""
import json
import pathlib
import re
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import build_pdf as B

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "docs" / "data" / "study-plan.json"
HTML_OUT = ROOT / "docs" / "plans-only-print.html"
PDF_OUT = ROOT / "docs" / "الخطط-الدراسية-جداول-الفصول.pdf"

# الموصى بها أولاً، ثم الأسرع، ثم البقية — كترتيب جدول المقارنة في بقية الوثائق.
# وأثره العملي أن أول ما يُرى عند فتح الملف خطةٌ لا تطلب أي استثناء.
ORDER = ["B", "A", "C", "D"]

# الوصف الثاني يُبنى من البيانات لا يُكتب يدوياً، فلا يتقادم عند تغيّر الاستثناءات.
LABEL = {"A": "الأسرع", "B": "الموصى بها", "C": "حماية المعدل", "D": "الطوارئ"}
NOTE = {"D": "تُفعَّل فقط لو رسبتَ في ترفن4260"}
WORDS = {3: "ثلاثة", 4: "أربعة", 5: "خمسة", 6: "ستة"}


def badge(d, key):
    s = d["scenarios"][key]
    n = len(s["terms"])
    m = re.search(r"\(([^)]*)\)", s["graduation"])
    grad = m.group(1).strip() if m else s["graduation"].split("—")[0].strip()
    exc = s["requires_exceptions"]
    tail = (NOTE[key] if key in NOTE else
            "بلا أي استثناء" if not exc else
            "يتطلب استثناء " + exc[0] if len(exc) == 1 else
            "يتطلب استثناءَي " + " و".join(exc))
    return LABEL[key], f"{WORDS.get(n, n)} فصول · التخرج {grad} · {tail}"

EXTRA_CSS = """
.pbadge{ display:flex; align-items:baseline; gap:4.5mm; justify-content:center;
  margin:0 0 3mm; padding-bottom:2.5mm; border-bottom:.8pt solid var(--ink) }
.pbadge .n{ font-family:"Reem Kufi",sans-serif; font-size:15pt; font-weight:600 }
.pbadge .s{ font-size:9pt; color:var(--ink-2) }
.pbadge .r{ font-size:7.6pt; border:.6pt solid var(--ok); color:var(--ok);
  border-radius:2mm; padding:.6mm 2mm; font-weight:600 }
.fgrid.g2{ grid-template-columns:repeat(2,1fr) }
/* تُمدَّد خانات الفصول لتملأ الصفحة، ويهبط مجموع الساعات إلى أسفل الخانة
   تماماً كما في الاستمارة الورقية */
.form .fgrid{ flex:1 }
.form .ftot{ margin-top:auto }
.form .fsig{ margin-top:0; padding-top:9mm }
.ptot{ display:flex; justify-content:space-between; align-items:baseline;
  border:.8pt solid var(--ink); border-top:0; padding:2.2mm 3mm;
  font-size:9pt; font-weight:600; background:var(--wash) }
.ptot .sub{ font-weight:400; font-size:8pt; color:var(--ink-2) }
.pfoot{ font-size:7.6pt; color:var(--stamp); margin:1.5mm 0 0; text-align:center }
"""


def plan_page(doc, d, key):
    """صفحة واحدة: استمارة تدقيق مملوءة بمقررات كل فصل في هذه التشكيلة."""
    s, m = d["scenarios"][key], d["meta"]
    ar = B.AR_KEY[key]
    label, sub = badge(d, key)
    terms = s["terms"]
    total = sum(B.credits(d, t["courses"]) for t in terms)
    active = [t for t in terms if t["courses"]]

    # صفّان بثلاث خانات، أو صفوف بخانتين لو كانت الفصول أربعة
    per = 2 if len(terms) == 4 else 3
    cls = " g2" if per == 2 else ""
    bands = [terms[i:i + per] for i in range(0, len(terms), per)]
    grid = "".join(
        f'<div class="fgrid{cls}">'
        + "".join(B.form_cell(d, t) for t in band)
        + ("<div></div>" * (per - len(band)))
        + "</div>" for band in bands)

    rec = '<span class="r">الموصى بها</span>' if s.get("recommended") else ""
    base = m["credits_remaining"]
    extra = ("" if total == base else
             f'<p class="pfoot">{total} ساعة = {base} ساعة متبقية + '
             f'{total - base} ساعة إعادة لمقرر مرسوب فيه ضمن هذه الخطة.</p>')
    exc = " و".join(s["requires_exceptions"]) or "لا يوجد"

    doc.sheet(f"""
<div class="form">
  <div class="pbadge"><span class="n">التشكيلة {ar}</span>
    <span class="s">{label} — {sub}</span>{rec}</div>
  <div class="fields">
    <span>اسم الطالب</span>: <b>{m["student"]}</b><br>
    <span>الرقم الجامعي</span>: <b>{m["student_id"]}</b>
    &nbsp;&nbsp;<span style="min-width:0">التخصص</span>: <b>التربية الفنية</b>
    &nbsp;&nbsp;<span style="min-width:0">الدفعة</span>: <b>{m["cohort"]}</b><br>
    <span>الاستثناء المطلوب</span>: <b>{exc}</b>
    &nbsp;&nbsp;<span style="min-width:0">توقع التخرج</span>: <b>{s["graduation"].split("(")[-1].rstrip(")").split("—")[0].strip()}</b>
  </div>
  {grid}
  <div class="ptot"><span>مجموع ساعات التشكيلة {ar}</span>
    <span class="sub">{len(active)} فصلاً مسجَّلاً · {sum(len(t["courses"]) for t in terms)} مقرراً</span>
    <span>{total} ساعة</span></div>{extra}
  <div class="fsig"><div>توقيع الطالب</div><div>توقيع المرشد الأكاديمي</div></div>
  <p class="ffoot">بتوقيع الطالب على هذه الاستمارة فإنه يؤكد قيامه بمراجعة الخطة مع مرشده الأكاديمي
  ويعزم على الالتزام بما جاء بها حتى يتخرج في الوقت المحدد<br>
  مكتب مساعد العميد للدراسات الجامعية — كلية التربية · جامعة السلطان قابوس</p>
</div>""")


def main():
    d = json.loads(DATA.read_text(encoding="utf-8"))
    doc = B.Doc(d["meta"])
    for key in ORDER:
        plan_page(doc, d, key)

    html = doc.html(B.font_css()).replace("</style></head>", EXTRA_CSS + "</style></head>")
    HTML_OUT.write_text(html, encoding="utf-8")
    print(f"✓ {HTML_OUT.name}  —  {len(doc.pages)} صفحة")

    if not pathlib.Path(B.CHROME).exists():
        sys.exit(f"✘ متصفح Chromium غير موجود عند {B.CHROME}")
    subprocess.run([B.CHROME, "--headless", "--disable-gpu", "--no-sandbox",
                    "--no-pdf-header-footer", "--run-all-compositor-stages-before-draw",
                    "--virtual-time-budget=20000",
                    f"--print-to-pdf={PDF_OUT}", HTML_OUT.as_uri()],
                   check=True, capture_output=True)
    print(f"✓ {PDF_OUT.name}  —  {PDF_OUT.stat().st_size // 1024} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
