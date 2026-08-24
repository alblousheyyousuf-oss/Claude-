#!/usr/bin/env python3
"""يبني وثيقة PDF لخارطة طريق التخرج من docs/data/study-plan.json.

الجداول الفصلية تُولَّد من نفس البيانات التي يفحصها scripts/validate_roadmap.py،
فلا يمكن أن ينحرف الـ PDF عن الخطة المدقَّقة.

الاستخدام:  python3 scripts/build_pdf.py
المخرجات:   docs/graduation-roadmap-print.html  ثم  docs/خارطة-طريق-التخرج.pdf
"""

import base64
import json
import pathlib
import re
import subprocess
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "docs" / "data" / "study-plan.json"
HTML_OUT = ROOT / "docs" / "graduation-roadmap-print.html"
PDF_OUT = ROOT / "docs" / "خارطة-طريق-التخرج.pdf"
FONT_CACHE = ROOT / "docs" / "fonts" / "fonts.css"
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/126.0.0.0 Safari/537.36")
FONT_URL = ("https://fonts.googleapis.com/css2"
            "?family=Reem+Kufi:wght@600"
            "&family=IBM+Plex+Sans+Arabic:wght@400;600"
            "&family=IBM+Plex+Mono:wght@400;500&display=swap")


# ══════════════════════════════════════════════════════════════
# الخطوط — تُنزَّل مرة وتُضمَّن كـ data URI ليصبح العرض غير معتمد على الشبكة
# ══════════════════════════════════════════════════════════════
def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def font_css():
    if FONT_CACHE.exists():
        return FONT_CACHE.read_text(encoding="utf-8")
    print("… تنزيل الخطوط وتضمينها")
    css = fetch(FONT_URL).decode("utf-8")
    for url in sorted(set(re.findall(r"url\((https://fonts\.gstatic\.com/[^)]+)\)", css))):
        blob = base64.b64encode(fetch(url)).decode("ascii")
        css = css.replace(url, f"data:font/woff2;base64,{blob}")
        print(f"   ✓ {url.rsplit('/', 1)[-1][:26]}  {len(blob)//1024} KB")
    FONT_CACHE.parent.mkdir(parents=True, exist_ok=True)
    FONT_CACHE.write_text(css, encoding="utf-8")
    return css


# ══════════════════════════════════════════════════════════════
# أدوات
# ══════════════════════════════════════════════════════════════
SEASON_AR = {"fall": "خريف", "spring": "ربيع"}


def credits(d, codes):
    return sum(d["courses"][c]["cr"] for c in codes)


def reason_for(d, scen_key, code):
    return d.get("reasons_by_scenario", {}).get(scen_key, {}).get(code) \
        or d["reasons"].get(code, "")


def prereq_cell(d, code, done):
    info = d["courses"][code]
    pre = info.get("prereq", [])
    if not pre:
        return "✅ بلا متطلب"
    missing = [p for p in pre if p not in done]
    if not missing:
        names = " · ".join(d["courses"][p]["ar"] for p in pre[:3])
        more = f" +{len(pre) - 3}" if len(pre) > 3 else ""
        return f"✅ {names}{more}"
    return "⚠️ " + " · ".join(d["courses"][p]["ar"] for p in missing)


BUDGET = 24        # ما يسعه سطح A4 من «صفوف» تقديرية
INTRO = 4          # ما تستهلكه مقدمة السيناريو في صفحته الأولى


def pack_terms(terms, budget=BUDGET):
    """يوزّع الفصول على صفحات بحيث لا يتجاوز وزن الصفحة الواحدة الميزانية.

    وزن الفصل = عدد مقرراته + 3 (ترويسة الفصل وترويسة الجدول). والصفحة الأولى
    من كل سيناريو تحمل مقدمته، فتُخصم منها INTRO.
    """
    pages, cur, w = [], [], 0
    for t in terms:
        n = max(len(t["courses"]), 1) + 3
        cap = budget - (INTRO if not pages else 0)
        if cur and w + n > cap:
            pages.append(cur)
            cur, w = [], 0
        cur.append(t)
        w += n
    if cur:
        pages.append(cur)
    return pages


# ══════════════════════════════════════════════════════════════
# التنسيق
# ══════════════════════════════════════════════════════════════
CSS = """
:root{
  --ink:#16211E; --ink-2:#4E5C58; --ink-3:#7A8783;
  --paper:#FFFFFF; --wash:#F2F5F2;
  --rule:#C9D2CD; --rule-2:#E3E8E5;
  --fall:#8A6A2F; --fall-wash:#F5F0E5;
  --spring:#1D6B62; --spring-wash:#E6F0EE;
  --stamp:#9E3226; --stamp-wash:#F7E9E6;
  --ok:#3B6F4B; --ok-wash:#E9F1EB;
}
@page{ size:A4; margin:0 }
*{ box-sizing:border-box; -webkit-print-color-adjust:exact; print-color-adjust:exact }
html,body{ margin:0; padding:0; background:#fff }
body{
  font-family:"IBM Plex Sans Arabic",sans-serif; color:var(--ink);
  direction:rtl; text-align:right; font-variant-numeric:tabular-nums;
  font-size:9.6pt; line-height:1.62;
}
.kufi,h1,h2,h3{ font-family:"Reem Kufi","IBM Plex Sans Arabic",sans-serif; font-weight:600 }
.mono{ font-family:"IBM Plex Mono","IBM Plex Sans Arabic",monospace; direction:ltr;
  unicode-bidi:isolate }

.sheet{
  width:210mm; height:297mm; padding:15mm 14mm 19mm; position:relative;
  page-break-after:always; overflow:hidden; background:var(--paper);
}
.sheet:last-child{ page-break-after:auto }
.ft{
  position:absolute; bottom:7mm; left:14mm; right:14mm;
  display:flex; justify-content:space-between; align-items:center;
  border-top:.5pt solid var(--rule-2); padding-top:2mm;
  font-size:7pt; color:var(--ink-3);
}
.hd{
  display:flex; justify-content:space-between; align-items:baseline;
  border-bottom:1.2pt solid var(--ink); padding-bottom:2.5mm; margin-bottom:6mm;
}
.hd h2{ font-size:15pt; margin:0 }
.hd .tag{ font-size:7.5pt; color:var(--ink-3) }

h3{ font-size:10.5pt; margin:0 0 1.5mm }
p{ margin:0 0 3mm }
.lede{ color:var(--ink-2); margin-bottom:5mm }
.sm{ font-size:8.4pt }
strong{ font-weight:600 }

table{ border-collapse:collapse; width:100%; font-size:8pt }
th,td{ padding:1.5mm 2mm; text-align:right; vertical-align:top; border-bottom:.5pt solid var(--rule-2) }
thead th{ background:var(--wash); font-weight:600; font-size:7.4pt; color:var(--ink-2);
  border-bottom:.8pt solid var(--rule); white-space:nowrap }
td.c{ font-family:"IBM Plex Mono","IBM Plex Sans Arabic",monospace; font-size:7.6pt;
  white-space:nowrap; color:var(--ink-2) }
td.n{ white-space:nowrap; text-align:center }
table.bx{ border:.8pt solid var(--rule) }

.term{ border:.8pt solid var(--rule); border-top:2pt solid var(--rule); margin-bottom:5mm }
.term.fall{ border-top-color:var(--fall) } .term.spring{ border-top-color:var(--spring) }
.term-hd{ display:flex; align-items:baseline; gap:3mm; padding:2mm 3mm;
  border-bottom:.5pt solid var(--rule-2); background:var(--wash) }
.term-hd .t{ font-family:"Reem Kufi",sans-serif; font-weight:600; font-size:10pt }
.term-hd .ld{ margin-inline-start:auto; font-size:8pt; color:var(--ink-2) }

.chip{ display:inline-block; font-size:7pt; font-weight:600; padding:.3mm 1.6mm;
  border:.6pt solid currentColor; white-space:nowrap; line-height:1.5 }
.chip.fall{ color:var(--fall) } .chip.spring{ color:var(--spring) }
.chip.stamp{ color:var(--stamp) } .chip.ok{ color:var(--ok) }

.box{ border:.8pt solid var(--rule); padding:3.5mm 4mm; margin-bottom:4mm }
.box.stamp{ border-color:var(--stamp); border-top-width:2pt; background:var(--stamp-wash) }
.box.ok{ border-color:var(--ok); border-top-width:2pt; background:var(--ok-wash) }
.box .lbl{ font-family:"Reem Kufi",sans-serif; font-weight:600; font-size:9.5pt; display:block; margin-bottom:1.5mm }
.box.stamp .lbl{ color:var(--stamp) } .box.ok .lbl{ color:var(--ok) }
.box p:last-child{ margin-bottom:0 }

.cols{ display:grid; grid-template-columns:1fr 1fr; gap:4mm }
.cols3{ display:grid; grid-template-columns:repeat(3,1fr); gap:3mm }
.stat{ border:.8pt solid var(--rule); padding:3mm; text-align:center }
.stat .v{ font-family:"Reem Kufi",sans-serif; font-size:17pt; font-weight:600; line-height:1.1; display:block }
.stat .k{ font-size:7.6pt; color:var(--ink-2) }

figure{ margin:0 0 4mm } figure svg{ display:block; width:100%; height:auto; color:var(--ink) }
figcaption{ margin-top:2.5mm; padding-top:2mm; border-top:.5pt solid var(--rule-2);
  font-size:8pt; color:var(--ink-2); line-height:1.6 }
.s-t{ fill:currentColor; font-family:"IBM Plex Sans Arabic",sans-serif; font-size:13px }
.s-s{ fill:var(--ink-3); font-family:"IBM Plex Sans Arabic",sans-serif; font-size:11.5px }
.s-lbl{ font-family:"Reem Kufi",sans-serif; font-size:13px; font-weight:600 }
.s-node{ fill:#fff; stroke:currentColor; stroke-width:1.5 }
.s-line{ stroke:currentColor; fill:none; stroke-width:1.5 }
.s-hair{ stroke:var(--rule); stroke-width:1; fill:none }
.s-fall{ fill:var(--fall) } .s-spring{ fill:var(--spring) } .s-stamp{ fill:var(--stamp) }
.s-fall-s{ stroke:var(--fall) } .s-spring-s{ stroke:var(--spring) } .s-stamp-s{ stroke:var(--stamp) }
.s-lane-f{ fill:var(--fall-wash) } .s-lane-s{ fill:var(--spring-wash) }
.s-dash{ stroke-dasharray:5 4 }

ol.ck{ list-style:none; padding:0; margin:0; counter-reset:c }
ol.ck li{ counter-increment:c; display:flex; gap:2.5mm; padding:1.6mm 0;
  border-bottom:.5pt solid var(--rule-2); font-size:8.4pt }
ol.ck li::before{ content:"☐"; color:var(--ink-3); flex:0 0 auto }
.risk{ display:flex; gap:2.5mm; padding:2mm 0; border-bottom:.5pt solid var(--rule-2) }
.risk .d{ flex:0 0 auto; width:2mm; height:2mm; margin-top:2mm; background:var(--ink-3) }
.risk.hi .d{ background:var(--stamp) } .risk.mid .d{ background:var(--fall) }
.risk p{ margin:0; font-size:8.4pt } .risk p.t{ font-weight:600 }
.letter{ border:.8pt solid var(--rule); padding:6mm 7mm; font-size:9pt; line-height:1.9 }
.sig{ display:flex; justify-content:space-between; margin-top:9mm; font-size:8.4pt; color:var(--ink-2) }
.sig div{ border-top:.5pt solid var(--rule); padding-top:1.5mm; width:58mm; text-align:center }
"""


# ══════════════════════════════════════════════════════════════
# المخططات
# ══════════════════════════════════════════════════════════════
ARROW_DEFS = """<defs><marker id="ah" viewBox="0 0 10 10" refX="9" refY="5"
 markerWidth="7" markerHeight="7" orient="auto-start-reverse">
 <path d="M0,1 L9,5 L0,9 z" fill="currentColor"/></marker></defs>"""


def fig_critical_path():
    return f"""<svg viewBox="0 0 900 344" role="img" aria-label="سلسلة من ثلاثة مقررات: منطر3027 ربيعي يؤدي إلى منطر4027 خريفي الذي يؤدي إلى التدريب الميداني في الربيع التالي، ولا اختصار عبر الصيف.">
{ARROW_DEFS}
<rect x="40" y="52" width="800" height="74" class="s-lane-f"/>
<rect x="40" y="206" width="800" height="74" class="s-lane-s"/>
<text x="812" y="46" class="s-lbl s-fall" text-anchor="middle">خريف</text>
<text x="812" y="200" class="s-lbl s-spring" text-anchor="middle">ربيع</text>
<line x1="40" y1="30" x2="860" y2="30" class="s-hair"/>
<text x="740" y="22" class="s-s" text-anchor="middle">خريف 2026</text>
<text x="540" y="22" class="s-s" text-anchor="middle">ربيع 2027</text>
<text x="340" y="22" class="s-s" text-anchor="middle">خريف 2027</text>
<text x="150" y="22" class="s-s" text-anchor="middle">ربيع 2028</text>
<line x1="740" y1="26" x2="740" y2="34" class="s-hair"/><line x1="540" y1="26" x2="540" y2="34" class="s-hair"/>
<line x1="340" y1="26" x2="340" y2="34" class="s-hair"/><line x1="150" y1="26" x2="150" y2="34" class="s-hair"/>
<rect x="452" y="222" width="176" height="44" class="s-node s-spring-s"/>
<text x="540" y="242" class="s-t" text-anchor="middle" font-weight="600">منطر3027</text>
<text x="540" y="258" class="s-s" text-anchor="middle">طرق تدريس (1) · 3 شعب</text>
<rect x="252" y="68" width="176" height="44" class="s-node s-fall-s"/>
<text x="340" y="88" class="s-t" text-anchor="middle" font-weight="600">منطر4027</text>
<text x="340" y="104" class="s-s" text-anchor="middle">طرق تدريس (2) · 3 شعب</text>
<rect x="62" y="222" width="176" height="44" class="s-node s-stamp-s" stroke-width="2"/>
<text x="150" y="242" class="s-t s-stamp" text-anchor="middle" font-weight="600">منطر4600</text>
<text x="150" y="258" class="s-s" text-anchor="middle">التدريب الميداني · 7 س</text>
<path d="M452,236 L400,236 L400,90 L432,90" class="s-line" marker-end="url(#ah)"/>
<text x="404" y="165" class="s-s" text-anchor="middle">متطلب سابق</text>
<path d="M252,90 L200,90 L200,236 L242,236" class="s-line" marker-end="url(#ah)"/>
<text x="204" y="165" class="s-s" text-anchor="middle">متطلب سابق</text>
<path d="M452,288 C384,308 240,308 172,292" class="s-line s-dash s-stamp-s" marker-end="url(#ah)" opacity=".7"/>
<text x="312" y="334" class="s-s s-stamp" text-anchor="middle">✕ لا اختصار عبر الفصل الصيفي — القسم لا يطرحه</text>
<text x="740" y="94" class="s-s" text-anchor="middle">نقطة الانطلاق</text>
<line x1="700" y1="88" x2="640" y2="88" class="s-line s-hair" marker-end="url(#ah)"/>
</svg>"""


def fig_bottleneck():
    def chips(x0, w, gap, n, cls, y=104, h=30):
        return "".join(
            f'<rect x="{x0 + i * (w + gap)}" y="{y}" width="{w}" height="{h}" class="s-node {cls}"/>'
            for i in range(n))
    return f"""<svg viewBox="0 0 900 258" role="img" aria-label="مقارنة بين ثلاث حالات لربيع 2027: بلا استثناء تتجاوز المقررات السبعة سقف الستة؛ الاستثناء E1 ينقل ترفن3210 إلى الخريف؛ الاستثناء E2 يرفع السقف إلى سبعة.">
{ARROW_DEFS}
<text x="750" y="24" class="s-lbl" text-anchor="middle">بلا استثناء</text>
{chips(614, 34, 4, 6, "s-spring-s")}
<rect x="576" y="104" width="34" height="30" class="s-node s-stamp-s" stroke-width="2"/>
<text x="593" y="124" class="s-t s-stamp" text-anchor="middle" font-size="15">7</text>
<text x="593" y="96" class="s-s s-stamp" text-anchor="middle">الزائد</text>
<path d="M648,148 L648,158 L838,158 L838,148" class="s-line s-spring-s"/>
<text x="743" y="176" class="s-s s-spring" text-anchor="middle">المسموح: 6 مقررات</text>
<text x="750" y="206" class="s-t s-stamp" text-anchor="middle" font-weight="600">✕ يتعذّر — التخرج يناير 2029</text>
<line x1="540" y1="40" x2="540" y2="228" class="s-hair"/>
<text x="390" y="24" class="s-lbl" text-anchor="middle">الاستثناء E1</text>
<rect x="330" y="46" width="120" height="26" class="s-lane-f"/>
<rect x="372" y="49" width="34" height="20" class="s-node s-fall-s"/>
<text x="290" y="63" class="s-s s-fall" text-anchor="middle">خريف 2026</text>
<path d="M389,104 L389,78" class="s-line s-fall-s" marker-end="url(#ah)"/>
<text x="389" y="92" class="s-s s-fall" text-anchor="middle">ترفن3210 يُسحب للخريف</text>
{chips(290, 34, 4, 2, "s-spring-s")}{chips(404, 34, 4, 3, "s-spring-s")}
<rect x="366" y="104" width="34" height="30" class="s-node s-spring-s s-dash" opacity=".4"/>
<path d="M290,148 L290,158 L514,158 L514,148" class="s-line s-spring-s"/>
<text x="402" y="176" class="s-s s-spring" text-anchor="middle">6 مقررات ضمن السقف</text>
<text x="390" y="206" class="s-t" text-anchor="middle" font-weight="600" fill="var(--ok)">✓ التخرج يونيو 2028</text>
<line x1="252" y1="40" x2="252" y2="228" class="s-hair"/>
<text x="126" y="24" class="s-lbl" text-anchor="middle">الاستثناء E2</text>
{chips(26, 28, 4, 7, "s-spring-s")}
<path d="M26,148 L26,158 L246,158 L246,148" class="s-line s-spring-s"/>
<text x="136" y="176" class="s-s s-spring" text-anchor="middle">السقف يُرفع إلى 7 — 18 ساعة</text>
<text x="126" y="206" class="s-t" text-anchor="middle" font-weight="600" fill="var(--ok)">✓ التخرج يونيو 2028</text>
</svg>"""


def fig_gantt(d):
    """أشرطة زمنية للسيناريوهات الأربعة على محور واحد — RTL: الفصل 9 يمين."""
    keys = ["A", "B", "C", "D"]
    names = {"A": "أ · الأسرع", "B": "ب · التوازن", "C": "ج · أقل ضغط", "D": "د · الطوارئ"}
    x_end, span, bw = 758, 118, 106
    def tx(i):                       # الفصل 9 أقصى اليمين، والزمن يمضي يساراً
        return x_end - (i - 9) * span
    head = [f'<text x="{tx(i) - bw / 2}" y="26" class="s-s" text-anchor="middle">'
            f'{SEASON_AR["fall" if i % 2 else "spring"]} {2026 + (i - 9 + 1) // 2}</text>'
            f'<line x1="{tx(i) - bw / 2}" y1="32" x2="{tx(i) - bw / 2}" y2="40" class="s-hair"/>'
            for i in range(9, 15)]
    rows, y = [], 56
    for k in keys:
        s = d["scenarios"][k]
        rec = s.get("recommended")
        if rec:
            rows.append(f'<rect x="10" y="{y - 6}" width="878" height="42" fill="var(--ok-wash)"/>')
        fill = ' fill="var(--ok)"' if rec else ''
        rows.append(f'<text x="828" y="{y + 19}" class="s-lbl" text-anchor="middle"{fill}>{names[k]}</text>')
        for t in s["terms"]:
            cr = credits(d, t["courses"])
            x = tx(t["index"]) - bw
            cls = "s-lane-f" if t["season"] == "fall" else "s-lane-s"
            stroke = "s-fall-s" if t["season"] == "fall" else "s-spring-s"
            rows.append(f'<rect x="{x}" y="{y}" width="{bw}" height="28" class="{cls} {stroke}"'
                        f' stroke-width="1" fill-opacity="1"/>')
            label = f"{cr} س" if cr else "معطَّل"
            rows.append(f'<text x="{x + bw / 2}" y="{y + 19}" class="s-t" text-anchor="middle"'
                        f' font-size="12">{label}</text>')
            if t.get("final"):
                rows.append(f'<circle cx="{x - 7}" cy="{y + 14}" r="6" fill="var(--ok)"/>')
                rows.append(f'<text x="{x - 38}" y="{y + 19}" class="s-s" text-anchor="middle"'
                            f' fill="var(--ok)">تخرّج</text>')
        y += 46
    return f"""<svg viewBox="0 0 900 {y + 26}" role="img" aria-label="مخطط زمني يقارن السيناريوهات الأربعة على محور واحد من خريف 2026 إلى ربيع 2029، وعليه عبء كل فصل ونقطة التخرج في كل سيناريو.">
<line x1="20" y1="40" x2="880" y2="40" class="s-hair"/>
{''.join(head)}
{''.join(rows)}
<text x="450" y="{y + 18}" class="s-s" text-anchor="middle">الرقم داخل الشريط = عدد الساعات المسجَّلة في ذلك الفصل · اللون = الموسم · الفصل الأول يميناً</text>
</svg>"""


# ══════════════════════════════════════════════════════════════
# بناء الصفحات
# ══════════════════════════════════════════════════════════════
class Doc:
    def __init__(self, meta):
        self.pages, self.meta = [], meta

    def sheet(self, inner, title=None, tag=""):
        n = len(self.pages) + 1
        head = (f'<div class="hd"><h2>{title}</h2><span class="tag">{tag}</span></div>'
                if title else "")
        self.pages.append(
            f'<div class="sheet">{head}{inner}'
            f'<div class="ft"><span>{self.meta["student"]} · {self.meta["student_id"]}</span>'
            f'<span>خارطة طريق التخرج — التربية الفنية · جامعة السلطان قابوس</span>'
            f'<span class="mono">{n}</span></div></div>')

    def html(self, css):
        return ("<!doctype html><html lang=\"ar\" dir=\"rtl\"><head><meta charset=\"utf-8\">"
                "<title>خارطة طريق التخرج</title>"
                f"<style>{css}</style><style>{CSS}</style></head><body>"
                + "".join(self.pages) + "</body></html>")


def term_block(d, scen_key, term, done):
    """يبني جدول فصل واحد ويحدّث مجموعة المنجَز."""
    season = term["season"]
    cr = credits(d, term["courses"])
    chip = f'<span class="chip {season}">{SEASON_AR[season]}</span>'
    final = '<span class="chip ok">فصل التخرج</span>' if term.get("final") else ""
    exc = (f'<span class="chip stamp">استثناء {term["exception"]}</span>'
           if term.get("exception") else "")
    if not term["courses"]:
        body = (f'<div style="padding:3mm;font-size:8.4pt;color:var(--stamp)">'
                f'{term.get("note", "فصل بلا تسجيل")}</div>')
    else:
        rows = []
        for c in term["courses"]:
            info = d["courses"][c]
            failed = c in term.get("failed", [])
            mark = ' <span class="chip stamp">رسوب</span>' if failed else ""
            rows.append(
                f'<tr><td class="c">{info["ar"]}</td><td>{info["name"]}{mark}</td>'
                f'<td class="n">{info["cr"]}</td><td class="n">{info["cat"]}</td>'
                f'<td>{prereq_cell(d, c, done)}</td>'
                f'<td>{reason_for(d, scen_key, c)}</td></tr>')
        body = ('<table><thead><tr><th>الرمز</th><th>المقرر</th><th>س.م</th><th>الفئة</th>'
                '<th>المتطلب</th><th>سبب التوقيت</th></tr></thead><tbody>'
                + "".join(rows) + "</tbody></table>")
    done |= {c for c in term["courses"] if c not in term.get("failed", [])}
    return (f'<div class="term {season}"><div class="term-hd">{chip}'
            f'<span class="t">{term["name"]}</span>{final}{exc}'
            f'<span class="ld">{cr} ساعة · {len(term["courses"])} مقررات</span></div>'
            f'{body}</div>')


def scenario_pages(doc, d, key):
    s = d["scenarios"][key]
    done = {c for c, v in d["courses"].items() if v["status"] == "completed"}
    blocks = [term_block(d, key, t, done) for t in s["terms"]]
    exc = " + ".join(s["requires_exceptions"]) or "لا شيء"
    rec = ' <span class="chip ok">الموصى به</span>' if s.get("recommended") else ""
    intro = (f'<p class="lede">{s["title"].split("—")[0].strip()}{rec} — '
             f'الاستثناءات المطلوبة: <strong>{exc}</strong> · '
             f'التخرج: <strong>{s["graduation"]}</strong>'
             + (f'<br><span class="sm" style="color:var(--stamp)">⚠️ {s["warning"]}</span>'
                if s.get("warning") else "") + '</p>')
    pages = pack_terms(s["terms"])
    idx, first = 0, True
    for grp in pages:
        chunk = "".join(blocks[idx:idx + len(grp)])
        idx += len(grp)
        tag = f"السيناريو {key}" + ("" if first else " — تتمة")
        doc.sheet((intro if first else "") + chunk,
                  title=f"السيناريو {key} · {s['title'].split('—')[0].strip()}", tag=tag)
        first = False


def build(d):
    doc = Doc(d["meta"])
    m = d["meta"]
    ev = d["seasonality_evidence"]
    C = d["courses"]

    # ── 1 · الغلاف ────────────────────────────────────────────
    doc.sheet(f"""
<div style="height:100%;display:flex;flex-direction:column;justify-content:center">
 <p style="font-size:8.5pt;color:var(--ink-3);margin-bottom:6mm">
   {m["university"]} · {m["college"]} · {m["department"]}</p>
 <h1 class="kufi" style="font-size:31pt;line-height:1.25;margin:0 0 4mm">خارطة طريق التخرج</h1>
 <p style="font-size:13pt;color:var(--ink-2);margin-bottom:10mm;max-width:150mm">
   تدقيق ما تبقّى من خطة بكالوريوس التربية الفنية — 50 ساعة معتمدة، أربعة سيناريوهات،
   ومسار حرج واحد يحكمها جميعاً.</p>
 <table class="bx" style="max-width:150mm;margin-bottom:9mm">
   <tbody>
     <tr><th style="width:38mm">الطالب</th><td>{m["student"]}</td></tr>
     <tr><th>الرقم الجامعي</th><td class="mono">{m["student_id"]}</td></tr>
     <tr><th>التخصص · الدفعة</th><td>التربية الفنية · {m["cohort"]}</td></tr>
     <tr><th>المرشد الأكاديمي</th><td>{m["advisor"]}</td></tr>
     <tr><th>المعدل التراكمي</th><td>{m["cgpa_band"]}</td></tr>
     <tr><th>نقطة الانطلاق</th><td>{m["start_term"]}</td></tr>
   </tbody>
 </table>
 <div class="box stamp" style="max-width:150mm"><span class="lbl">الحكم</span>
  <p>مقترح المرشد لا يمكن تنفيذه بدءاً من سبتمبر 2026: فصله الأول مقرراته <strong>ربيعية بالكامل</strong>،
  وفيه مخالفة متطلب سابق، والتدريب الميداني غائب عنه. وأبكر تخرج ممكن هو <strong>يونيو 2028</strong> —
  لكنه يستلزم <strong>استثناءً إدارياً واحداً لا مفرّ منه</strong>.</p></div>
 <p class="sm" style="color:var(--ink-3);margin-top:8mm">
   حُرّر في 24 أغسطس 2026 · موسمية المقررات مثبتة من جدولَي الخريف والربيع 2025/2026 الرسميين ·
   وثيقة تخطيط وتفاوض لا قرار أكاديمي</p>
</div>""")

    # ── 2 · الخلاصة ───────────────────────────────────────────
    cards = "".join(
        f'<div class="stat" style="{"border-color:var(--ok);border-top:2pt solid var(--ok)" if d["scenarios"][k].get("recommended") else ""}">'
        f'<span class="v">{d["scenarios"][k]["graduation"].split("(")[-1].rstrip(")").split("—")[0].strip()}</span>'
        f'<span class="k">{k} — {d["scenarios"][k]["title"].split("—")[0].strip()}<br>'
        f'{" + ".join(d["scenarios"][k]["requires_exceptions"]) or "بلا استثناء"} · '
        f'{len(d["scenarios"][k]["terms"])} فصول</span></div>'
        for k in ["A", "B", "C", "D"])
    # فهرس محسوب من نفس دالة التوزيع التي تبني الصفحات
    left = [(3, "الحالة الأكاديمية — المتبقي مصنَّفاً بالموسم"),
            (4, "دليل الموسمية — الدوران المنفصل بين الفصلين"),
            (5, "تدقيق مقترح المرشد"),
            (6, "المسار الحرج"),
            (7, "اختناق الربيع وسلّم الاستثناءات"),
            (8, "مقارنة الخطط الأربع على محور زمني")]
    right, n = [], 8
    for k, ar in [("A", "أ"), ("B", "ب"), ("C", "ج"), ("D", "د")]:
        cnt = len(pack_terms(d["scenarios"][k]["terms"]))
        rng = f"{n + 1}" if cnt == 1 else f"{n + 1}–{n + cnt}"
        right.append((rng, f"السيناريو {ar} · جداول فصلية كاملة"))
        n += cnt
    right.append((str(n + 1), "المخاطر وقائمة التحقق"))
    right.append((str(n + 2), "مسودة خطاب الاستثناء"))
    toc = "".join(
        f'<tr><td class="n mono">{lp}</td><td>{lt}</td>'
        f'<td class="n mono">{right[i][0]}</td><td>{right[i][1]}</td></tr>'
        for i, (lp, lt) in enumerate(left))

    doc.sheet(f"""
<div class="cols3" style="margin-bottom:6mm">
  <div class="stat"><span class="v">75</span><span class="k">ساعة منجَزة</span></div>
  <div class="stat"><span class="v">50</span><span class="k">ساعة متبقية</span></div>
  <div class="stat"><span class="v">125</span><span class="k">مجموع الخطة</span></div>
</div>
<h3>الخلاصة في ثلاث نقاط</h3>
<p><strong>١ · مقترح المرشد ينكسر من أول فصل.</strong> الاستمارة تقترح البدء بخمسة مقررات
ربيعية كلها — لا يُطرح أيٌّ منها خريفاً. وفيها مخالفة متطلب سابق (ترفن4260 مع ترفن2110 وترفن3111)،
والتدريب الميداني (7 ساعات) غائب تماماً، فمجموعها 43 ساعة لا 50.</p>
<p><strong>٢ · المسار الحرج يضع أرضية صلبة.</strong> منطر3027 (ربيعي حصراً) ← منطر4027 (خريفي حصراً)
← التدريب الميداني. ثلاث حلقات كلٌّ في موسم، ولا فصل صيفي يختصر. <strong>لا تخرج قبل يونيو 2028
بأي حال.</strong></p>
<p><strong>٣ · الاستثناء ليس اختياراً.</strong> المقررات الربيعية المتبقية سبعة، وربيع 2028 محجوز
للتدريب الميداني الذي يشترط إنهاء كل شيء قبله ⇒ السبعة كلها في ربيع 2027 وحده. مجموعها 18 ساعة
(داخل سقف الساعات تماماً) لكن عددها يتجاوز سقف الـ6 مقررات. <strong>السؤال ليس «هل نحتاج استثناءً»
بل «أيّها نطلب».</strong></p>
<h3 style="margin-top:6mm">السيناريوهات الأربعة</h3>
<div class="cols" style="grid-template-columns:repeat(4,1fr);margin-bottom:5mm">{cards}</div>
<div class="box ok"><span class="lbl">التوصية</span>
<p>{m["recommendation_rationale"]}</p></div>
<h3>محتويات الوثيقة</h3>
<table class="bx"><tbody>{toc}</tbody></table>""", title="الخلاصة التنفيذية", tag="صفحة 2")

    # ── 3 · الحالة الأكاديمية ─────────────────────────────────
    groups = [("ربيعي حصراً", "spring", ["CUTM3027","ARED4111","ARED2130","ARED3140","ARED3210","ARED3170","ARED4120"]),
              ("خريفي حصراً", "fall", ["ARED2110","ARED3111","ARED3250","ARED4140","CUTM4027","ARED4260"]),
              ("يُطرح في الفصلين", "", ["PSYC4500","EDUC3050"]),
              ("خريفي (تحوّطاً)", "fall", ["SOCY1005"]),
              ("ختامي", "", ["CUTM4600","CUTM4400"])]
    rows = []
    for label, cls, codes in groups:
        chip = f'<span class="chip {cls}">{label}</span>' if cls else f'<span class="chip">{label}</span>'
        rows.append(f'<tr><td>{chip}</td><td>{" · ".join(C[c]["ar"] + " " + C[c]["name"].split("—")[0].strip() for c in codes)}</td>'
                    f'<td class="n">{credits(d, codes)}</td></tr>')
    elective_rows = "".join(
        f'<tr><td>{lst}</td><td class="c">{C[sel]["ar"]}</td><td>{C[sel]["name"].split("—")[0].strip()}</td>'
        f'<td class="sm">{" · ".join(C[sel].get("alternatives", []))}</td></tr>'
        for lst, sel in [("ز1 — اختياري (أ)", "ARED3140"), ("ز2 — اختياري (ب)", "ARED3250"),
                         ("ز3 — اختياري (ج)", "ARED3170"), ("ز4 — اختياري (د)", "ARED4140")])
    doc.sheet(f"""
<p class="lede">المنجَز <strong>75 ساعة</strong> · المتبقي <strong>50 ساعة</strong> · المجموع 125 ✓</p>
<div class="box stamp" style="border-top-width:1pt"><span class="lbl">فرضية معلَنة</span>
<p class="sm">بُني «المنجَز» على إفادة الطالب أنه أنهى كل الخطة عدا ما ورد في استمارة التدقيق.
الحساب يُغلِق تماماً (75 + 50 = 125)، وهو مؤشر قوي على صحته — لكنه يبقى استنتاجاً يحتاج
تثبيتاً من كشف الدرجات الرسمي.</p></div>
<h3>المتبقي مصنَّفاً بالموسم</h3>
<table class="bx" style="margin-bottom:6mm"><thead><tr><th style="width:30mm">الموسم</th>
<th>المقررات</th><th class="n">الساعات</th></tr></thead><tbody>{"".join(rows)}</tbody></table>
<h3>متطلبات الجامعة — 3 مقررات × 2 ساعة</h3>
<table class="bx" style="margin-bottom:6mm"><tbody>
<tr><td class="c">عربي1060</td><td>اللغة العربية</td><td class="n">2</td><td><span class="chip ok">منجَز</span></td></tr>
<tr><td class="c">اجمع1005</td><td>عمان: الدولة والإنسان</td><td class="n">2</td><td><span class="chip stamp">متبقٍ</span></td></tr>
<tr><td class="c">تاريخ1010 / اسلم1010</td><td>عمان والحضارة الإسلامية <em>أو</em> الثقافة الإسلامية — يُختار أحدهما</td>
    <td class="n">2</td><td><span class="chip ok">منجَز</span></td></tr>
</tbody></table>
<p class="sm">واختياري الجامعة (6 ساعات) مُنجَز بالكامل.</p>
<h3 style="margin-top:5mm">اختياري التخصص — المُختار وبدائله</h3>
<table class="bx"><thead><tr><th>القائمة</th><th>الرمز</th><th>المُختار</th><th>البدائل من نفس القائمة</th></tr></thead>
<tbody>{elective_rows}</tbody></table>
<p class="sm" style="margin-top:3mm">البدائل لها نفس الساعات ونفس الموسم، فاستبدال أيٍّ منها
لا يغيّر شيئاً في الجداول.</p>""", title="الحالة الأكاديمية", tag="صفحة 3")
    pages_rest(doc, d)
    return doc

def pages_rest(doc, d):
    C, ev = d["courses"], d["seasonality_evidence"]

    # ── 4 · دليل الموسمية ─────────────────────────────────────
    pairs = [("ARED2110","ARED2130"),("ARED3111","ARED3210"),("ARED3250","ARED3170"),
             ("ARED4140","ARED4111"),("ARED4260","ARED4120"),("CUTM4027","CUTM3027")]
    rows = "".join(
        f'<tr><td class="c">{C[f]["ar"]}</td><td>{C[f]["name"].split("—")[0].strip()}</td>'
        f'<td class="c">{C[s_]["ar"]}</td><td>{C[s_]["name"].split("—")[0].strip()}</td></tr>'
        for f, s_ in pairs)
    TIGHT = '<span class="chip stamp">ضيق</span> '
    def sec_row(c):
        s_ = C[c]["sections_2026"]
        flag = TIGHT if s_.get("tight") else ""
        enr = s_["enrolled"] if s_["enrolled"] is not None else "—"
        return (f'<tr><td class="c">{C[c]["ar"]}</td>'
                f'<td>{C[c]["name"].split("—")[0].strip()}</td>'
                f'<td class="n">{s_["term"]}</td><td class="n">{s_["sections"]}</td>'
                f'<td class="n">{s_["capacity"] or "—"}</td><td class="n">{enr}</td>'
                f'<td class="sm">{flag}{s_.get("note", "")}</td></tr>')
    sec_rows = "".join(sec_row(c) for c in
                       ["CUTM3027","CUTM4027","ARED4260","ARED4111","ARED3170",
                        "ARED4120","ARED3210","ARED2130"])
    doc.sheet(f"""
<p class="lede">الموسمية هنا ليست تقديراً. قُورنت قائمة مقررات الخطة بجدولَي المقررات الرسميين
لخريف 2025/2026 وربيع 2025/2026.</p>
<div class="box ok"><span class="lbl">الاكتشاف الحاكم</span>
<p>تقاطع قائمتَي مقررات قسم التربية الفنية بين الفصلين = <strong>صفر</strong>. أربعة وثلاثون مقرراً
موزّعة على الفصلين <strong>بلا تقاطع واحد</strong> — أي أن القسم يدير <strong>دوراناً منفصلاً تماماً</strong>
ولا يطرح أي مقرر في الفصلين معاً.</p></div>
<h3>عيّنة من الدوران — المقررات المتبقية</h3>
<table class="bx" style="margin-bottom:6mm">
<thead><tr><th colspan="2" style="color:var(--fall)">يُطرح خريفاً فقط</th>
<th colspan="2" style="color:var(--spring)">يُطرح ربيعاً فقط</th></tr></thead>
<tbody>{rows}</tbody></table>
<p class="sm" style="margin-bottom:6mm"><strong>أثر ذلك على الاستثناءات:</strong> طلب طرح ترفن3210
خريفاً (الاستثناء E1) يعني مطالبة القسم بكسر نمط يلتزم به عبر مقرراته كلها بلا استثناء واحد.
ولهذا تقدّم الاستثناء E2 — الذي يبقى داخل سقف الساعات ولا يمسّ الدوران — على E1 في التوصية.</p>
<h3>سعات الشعب — من فصلَي 2025/2026 كمؤشر</h3>
<table class="bx"><thead><tr><th>الرمز</th><th>المقرر</th><th class="n">الموسم</th>
<th class="n">الشعب</th><th class="n">السعة</th><th class="n">مسجَّل</th><th>ملاحظة</th></tr></thead>
<tbody>{sec_rows}</tbody></table>
<p class="sm" style="margin-top:2mm">الربيع أضيق من الخريف: ترفن3170 شعبته الوحيدة كانت
<strong>ممتلئة 20/20</strong>، وترفن4111 إحدى شعبتيه ممتلئة. التسجيل في اليوم الأول ضرورة لا احتياط.
<span style="color:var(--ink-3)"> — الفجوة الوحيدة: {ev["gaps"][0]}</span></p>""",
        title="دليل الموسمية", tag="صفحة 4")

    # ── 5 · تدقيق مقترح المرشد ────────────────────────────────
    audit = [("الفصل الأول: منطر3027 · ترفن4111 · ترفن2130 · ترفن3140 · ترفن3210",
              "قاتل", "stamp", "خمستها ربيعية — لا يُطرح أيٌّ منها خريفاً", "ابدأ بالكتلة الخريفية أولاً"),
             ("ترفن4260 المشروع الفني مع ترفن2110 وترفن3111 في الفصل نفسه",
              "مخالفة", "stamp", "كلاهما من متطلباته السبعة", "2110 و3111 خريف 2026، والمشروع خريف 2027"),
             ("منطر4600 التدريب الميداني — 7 ساعات",
              "غائب", "stamp", "لا ذكر له في الاستمارة", "فصل رابع مخصص له"),
             ("منطر4400 مشروع التخرج في فصل منفصل عن التدريب",
              "تحفّظ", "fall", "الخطة تنصّ أنه «مصاحب» للتدريب", "ضمّهما في الفصل الأخير"),
             ("مجموع المقترح 43 ساعة",
              "نقص", "fall", "المتبقي الفعلي 50 ساعة", "الفارق 7 = التدريب الميداني"),
             ("ترتيب ربيع ← خريف ← ربيع",
              "سليم", "ok", "صحيح موسمياً", "المنطق صحيح، ونقطة البداية خاطئة")]
    arows = "".join(
        f'<tr><td>{a}</td><td><span class="chip {cls}">{v}</span> {why}</td><td>{fix}</td></tr>'
        for a, v, cls, why, fix in audit)
    doc.sheet(f"""
<p class="lede">الاستمارة تقترح ثلاثة فصول بمجموع 43 ساعة. عند فحصها مقابل جدولَي المقررات
وشجرة المتطلبات ظهرت ستة بنود.</p>
<table class="bx" style="margin-bottom:6mm"><thead><tr><th style="width:58mm">ما في المقترح</th>
<th>الحكم</th><th style="width:52mm">التصحيح</th></tr></thead><tbody>{arows}</tbody></table>
<h3>حصيلة المدقّق الآلي</h3>
<div class="cols">
 <div class="box" style="border-top:2pt solid var(--stamp)">
  <span class="lbl">المقترح كما هو (بداية خريفية)</span>
  <p><strong style="font-size:15pt;color:var(--stamp)">15</strong> مخالفة — أغلبها موسمية:
  مقررات مُجدوَلة في فصول لا تُطرح فيها.</p></div>
 <div class="box" style="border-top:2pt solid var(--fall)">
  <span class="lbl">المقترح بترتيبه المقصود (بداية ربيعية)</span>
  <p><strong style="font-size:15pt;color:var(--fall)">3</strong> مخالفات فقط: تزامن ترفن4260
  مع متطلبيه، وغياب منطر4600.</p></div>
</div>
<p style="margin-top:4mm">أي أن <strong>الخلل الجوهري في المقترح ليس نقطة البداية وحدها</strong> —
بل المشروع الفني والتدريب الميداني. وهذا يفسّر بدقة لماذا لم يُعطَ ضمان بقبوله: الاستمارة رسم
تقريبي بحسن نية، لا خطة مدقَّقة.</p>
<p class="sm" style="color:var(--ink-3)">الاختباران السلبيان مضمَّنان في
<span class="mono">scripts/validate_roadmap.py</span> ويفشلان عمداً — وهو ما يثبت أن المدقّق
يكشف الأخطاء فعلاً بدل الادعاء.</p>""", title="تدقيق مقترح المرشد", tag="صفحة 5")

    # ── 6 · المسار الحرج ──────────────────────────────────────
    doc.sheet(f"""
<p class="lede">ثلاثة مقررات مترابطة، كل واحد مقفل على موسم مختلف، ولا فصل صيفي يختصر بينها.</p>
<figure>{fig_critical_path()}
<figcaption><strong>لماذا أربعة فصول هي الأرضية:</strong> منطر3027 يُطرح ربيعاً حصراً، ومنطر4027
خريفاً حصراً، والتدريب الميداني يشترط اجتيازهما معاً. كل حلقة تنتظر موسمها، فتستهلك السلسلة أربعة
فصول كاملة من خريف 2026 حتى ربيع 2028.</figcaption></figure>
<h3>شرط تسجيل التدريب الميداني — نصّ الخطة</h3>
<div class="box">
<p class="sm">١ · «إكمال جميع المقررات في الخطة الدراسية المعتمدة بنجاح عدا مقرر مشروع التخرج
الذي يتم دراسته كمقرر مصاحب مع مقرر التدريب الميداني».<br>
٢ · «أن يكون المعدل التراكمي للمرشح 2 على الأقل في نهاية الفصل الدراسي الذي يسبق التدريب الميداني».</p>
</div>
<p>الشرط الأول هو ما يجعل الفصل الأخير <strong>مقفلاً</strong>: أي مقرر متأخر لا يؤخّر نفسه فحسب،
بل يعطّل التدريب الميداني ومعه التخرج كله. والشرط الثاني يجعل معدلك — وهو في نطاق 2.00–2.99 —
عاملاً حرجاً في نهاية الفصل السابق للتدريب.</p>
<div class="box ok"><span class="lbl">ما ثبت من جدول الربيع</span>
<p>منطر4600 التدريب الميداني <strong>يُطرح في الفصلين</strong> (خريفاً وربيعاً) — وهذا ما يجعل
التخرج في ربيع 2028 ممكناً فعلاً لا نظرياً. ومنطر3027 له <strong>ثلاث شعب</strong> بسعة 64 مقعداً
ومسجَّل فيها 42، أي أن رأس المسار الحرج ليس مزدحماً.</p></div>""",
        title="المسار الحرج", tag="صفحة 6")

    # ── 7 · اختناق الربيع ─────────────────────────────────────
    exc_rows = "".join(
        f'<tr><td class="mono">{k}</td><td>{v["label"]}</td><td>{v["cost"]}</td><td class="sm">{v["authority"]}</td></tr>'
        for k, v in d["exceptions"].items())
    doc.sheet(f"""
<p class="lede">المقررات الربيعية المتبقية سبعة. وربيع 2028 محجوز للتدريب الميداني الذي يشترط
إنهاء كل شيء قبله — فالسبعة كلها يجب أن تدخل ربيع 2027 وحده.</p>
<figure>{fig_bottleneck()}
<figcaption><strong>الفرق بين الخيارين:</strong> <span class="mono">E1</span> يُخرج مقرراً من الربيع
بطرح ترفن3210 خريفاً. و<span class="mono">E2</span> يُبقي السبعة ويرفع سقف العدد — وهو الأرخص نظامياً
لأن سقف الساعات (18) مستوفى تماماً والمتجاوَز هو العدد فقط.</figcaption></figure>
<h3>سلّم الاستثناءات</h3>
<table class="bx" style="margin-bottom:4mm"><thead><tr><th>الرمز</th><th>الاستثناء</th>
<th>الكلفة</th><th>الجهة</th></tr></thead><tbody>{exc_rows}</tbody></table>
<div class="box ok"><span class="lbl">الاستراتيجية</span>
<p>اطلب <span class="mono">E2</span> و<span class="mono">E1</span> معاً في خطاب واحد. طلب اثنين
يضاعف احتمال القبول بلا كلفة إضافية، وأيّهما مرّ ثبّت التخرج في يونيو 2028. وبعد ثبوت الدوران
المنفصل في القسم، <span class="mono">E2</span> هو الأقرب للقبول.</p></div>""",
        title="اختناق الربيع", tag="صفحة 7")

    # ── 8 · مقارنة الخطط ──────────────────────────────────────
    def cmp_row(k):
        s_ = d["scenarios"][k]
        rec = s_.get("recommended")
        tr = ' style="background:var(--ok-wash)"' if rec else ""
        badge = ' <span class="chip ok">موصى</span>' if rec else ""
        loads = " · ".join(str(credits(d, t["courses"])) for t in s_["terms"])
        grad = s_["graduation"].split("—")[0].strip()
        note = " <span class='chip stamp'>الفصل 14</span>" if k == "D" else ""
        return (f'<tr{tr}><td><strong>{k}</strong> — {s_["title"].split("—")[0].strip()}{badge}</td>'
                f'<td class="mono">{" + ".join(s_["requires_exceptions"]) or "—"}</td>'
                f'<td class="n">{len(s_["terms"])}</td><td class="n">{loads}</td>'
                f'<td>{grad}{note}</td></tr>')
    cmp_rows = "".join(cmp_row(k) for k in ["A", "B", "C", "D"])
    doc.sheet(f"""
<p class="lede">الخطط الأربع على محور زمني واحد. طول الشريط = عدد الفصول، والرقم داخله = عبء
ذلك الفصل بالساعات، واللون = الموسم.</p>
<figure>{fig_gantt(d)}
<figcaption>السيناريوهان <strong>أ</strong> و<strong>ب</strong> ينتهيان عند نفس النقطة — يونيو 2028 —
بطريقين مختلفين واستثناءين مختلفين. و<strong>ج</strong> يشتري تجنّب الاستثناء بفصل إضافي وسبعة أشهر.
و<strong>د</strong> ليس خياراً بل نتيجة: ما يحدث لو رسبتَ في منطر3027.</figcaption></figure>
<table class="bx" style="margin-bottom:5mm"><thead><tr><th style="width:52mm">السيناريو</th>
<th>الاستثناءات</th><th class="n">الفصول</th><th class="n">الأحمال (الأول يميناً)</th><th>التخرج</th></tr></thead>
<tbody>{cmp_rows}</tbody></table>
<div class="cols">
<div class="box" style="border-top:2pt solid var(--stamp)"><span class="lbl">لماذا «د» تحذير لا خطة</span>
<p class="sm">الرسوب في منطر3027 لا يكلّف فصلاً واحداً. إنه يخلق <strong>فصلين مُعطَّلين</strong>
لا يوجد فيهما أي مقرر آخر يُسجَّل قانوناً — لأن كل ما عداهما سيكون منتهياً — فيقع كلاهما تحت الحد
الأدنى (9 ساعات) ويحتاج استثناءً أو تأجيلاً معتمداً. والهبوط يكون على <strong>الفصل الرابع عشر</strong>،
آخر فصل تسمح به اللائحة (10 اعتيادية + 4). لا هامش بعده.</p></div>
<div class="box"><span class="lbl">حدود اللائحة المطبَّقة</span>
<p class="sm">العبء الاعتيادي 15 ساعة والأقصى <strong>18 ساعة في 6 مقررات</strong> (ب-3) ·
الحد الأدنى 9 ساعات إلا في الفصل الأخير · زيادة العبء تتطلب معدلاً ≥ 3.00 (غير متاحة) ·
لا فصل صيفي في القسم · الحد الأقصى للدراسة 14 فصلاً · التخرج بمعدل ≥ 2.00 (د-2).</p></div>
</div>""", title="مقارنة الخطط الأربع", tag="صفحة 8")

    for k in ["A", "B", "C", "D"]:
        scenario_pages(doc, d, k)

    pages_tail(doc, d)


def pages_tail(doc, d):
    C = d["courses"]
    risks = [
      ("hi", "منطر3027 — نقطة الانهيار الوحيدة",
       "ربيعي حصراً، ورأس السلسلة كلها. الرسوب فيه أو الانسحاب منه أو عدم طرحه يؤخّر التخرج سنة "
       "كاملة ويخلق فصلين مُعطَّلين. الخبر الجيد: ثلاث شعب بسعة 64 ومسجَّل 42 — غير مزدحم. "
       "لا تنسحب منه تحت أي ظرف؛ الانسحاب هنا كلفته سنة."),
      ("hi", "رفض الاستثناءين معاً",
       "رفض E2 وE1 يُسقطك إلى السيناريو ج: فصل إضافي وسبعة أشهر. قدّم الطلب مبكراً — قبل فترة "
       "تسجيل خريف 2026 — لا في آخر لحظة."),
      ("mid", "ازدحام مقررات الربيع",
       "ترفن3170 شعبته الوحيدة كانت ممتلئة 20/20، وترفن4111 إحدى شعبتيه ممتلئة (37 من 40)، "
       "وترفن4120 عند 42 من 45. سجّل في اليوم الأول. البديل الجاهز لاختياري (ج) هو ترفن3160 "
       "وفيه متسع (10 من 16)."),
      ("mid", "سعة ترفن4260 المشروع الفني",
       "سبع شعب لكن سعة الشعبة الواحدة ثمانية طلاب فقط، و44 مسجَّلاً من 56 مقعداً. "
       "أضيق مقرر خريفي في خطتك."),
      ("mid", "المعدل التراكمي",
       "شرط التدريب الميداني تراكمي ≥ 2.00 في نهاية الفصل السابق له. مع معدل في نطاق 2.00–2.99، "
       "فصل واحد ضعيف قبل التدريب يُسقط الشرط ويؤخّر التخرج فصلاً كاملاً."),
      ("", "جدول الحد الأدنى للتقدّم (البند د-6)",
       "في السيناريو ج يقترب التراكمي من خانة التحذير عند الفصلين 11 و12. والجدول جامعي عام "
       "وصفوفه الأخيرة تطلب 133 ساعة — أكثر من مجموع درجتك (125) — فهو غير قابل للتطبيق حرفياً "
       "عند الذيل. يجب تثبيت طريقة تطبيقه مع القبول والتسجيل قبل اختيار ذلك السيناريو."),
    ]
    rrows = "".join(f'<div class="risk {c}"><span class="d"></span><div>'
                    f'<p class="t">{t}</p><p>{b}</p></div></div>' for c, t, b in risks)
    checks = [
      "كشف الدرجات الرسمي — تأكيد أن المنجَز 75 ساعة وأن المتبقي هو الخمسون المذكورة بالضبط.",
      "رقم فصلك الدراسي في خريف 2026 — هل هو التاسع؟ يحدّد موقعك من جدول د-6.",
      "متطلب ترفن4120: بلا متطلب («القائمة و») أم ترفن3210 (الجدول الفصلي)؟ الخطة تتناقض مع نفسها هنا، "
      "والفرق بينهما فصل دراسي كامل.",
      "متطلب ترفن2110 — الخطة تحيله إلى نفسه، وهو خطأ مطبعي ظاهر.",
      "هل يُطرح اجمع1005 ربيعاً؟ (مؤكَّد خريفاً؛ وُضع في الخريف في السيناريوهات الأربعة تحوّطاً.)",
      "هل منطر4400 مصاحب إلزامي لمنطر4600 أم يجوز تقديمه على فصل سابق؟",
      "ثبات الموسمية عبر السنوات — الدوران مؤكَّد لعام 2025/2026، ويُفترض تكراره في 2026/2027.",
      "سعة شعب ترفن4260 · ترفن3170 · ترفن4111 لفصولك المستهدفة تحديداً.",
    ]
    doc.sheet(f"""
<h3>المخاطر مرتَّبة بالخطورة</h3>
<div style="margin-bottom:6mm">{rrows}</div>
<h3>ما يجب تثبيته قبل التسجيل</h3>
<p class="sm lede">كل بند أدناه <strong>افتراض</strong> في هذا التحليل، لا حقيقة مثبتة.
البنود التي كانت هنا وحُسمت بجدول الربيع — موسمية منطر3027 وترفن3210 وترفن4120 وطرح
التدريب الميداني ربيعاً — رُفعت من القائمة.</p>
<ol class="ck">{"".join(f"<li><span>{c}</span></li>" for c in checks)}</ol>""",
        title="المخاطر وقائمة التحقق", tag="صفحة المخاطر")

    doc.sheet(f"""
<p class="lede">جاهزة للطباعة والتقديم. عدّل ما تراه ووقّع.</p>
<div class="letter">
<p><strong>إلى:</strong> رئيس قسم التربية الفنية / مساعد عميد كلية التربية للدراسات الجامعية الأولى<br>
<strong>الموضوع:</strong> طلب استثناء لتمكين استكمال الخطة الدراسية في أربعة فصول</p>
<p>تحية طيبة وبعد،</p>
<p>أنا الطالب <strong>{d["meta"]["student"]}</strong>، الرقم الجامعي
<span class="mono">{d["meta"]["student_id"]}</span>، تخصص التربية الفنية، دفعة {d["meta"]["cohort"]}.
تبقّى لي <strong>50 ساعة معتمدة</strong> لاستكمال الخطة، وقد راجعتُ توزيعها على المواسم الدراسية
استناداً إلى جدولَي المقررات لخريف وربيع 2025/2026، فتبيّن ما يلي:</p>
<p>١ · المقررات الربيعية المتبقية <strong>سبعة</strong> بمجموع <strong>18 ساعة معتمدة</strong>.<br>
٢ · لا يمكن تأجيل أيٍّ منها إلى ربيع 2028، لأن ذلك الفصل مخصص للتدريب الميداني الذي يشترط
إنهاء جميع مقررات الخطة قبله.<br>
٣ · عليه، يجب تسجيل السبعة كلها في فصل ربيع 2027، وهو ما يستوفي سقف الساعات (18) تماماً
لكنه يتجاوز سقف عدد المقررات (6) بمقرر واحد.</p>
<p>وعليه ألتمس من سعادتكم الموافقة على <strong>أحد</strong> الخيارين:</p>
<p><strong>الأول:</strong> الموافقة على تسجيلي في <strong>سبعة مقررات (18 ساعة معتمدة)</strong>
في فصل ربيع 2027، علماً بأن سقف الساعات المنصوص عليه في البند (ب-3) من النظام الأكاديمي
مستوفى تماماً، وأن التجاوز منحصر في عدد المقررات.</p>
<p><strong>الثاني:</strong> طرح مقرر <strong>ترفن3210 تاريخ الفن الحديث والمعاصر</strong> (ساعتان)
في فصل الخريف، أو السماح لي بتسجيله فيه — وهو مقرر محاضرة نظرية لا يتطلب ورشة أو استوديو
أو سعة معملية.</p>
<p>وأودّ الإفادة بأن أياً من الخيارين يمكّنني من التخرج في <strong>ربيع 2028</strong> وفق الخطة
المرفقة، بينما يؤدي تعذّرهما إلى تأخير التخرج فصلاً كاملاً إلى يناير 2029.</p>
<p><strong>مرفق:</strong> خطة فصلية تفصيلية موضّح فيها المتطلبات السابقة والموسمية لكل مقرر
(الصفحات 9–{len(doc.pages) - 1} من هذه الوثيقة).</p>
<p>شاكراً لكم حسن تعاونكم،</p>
<div class="sig"><div>توقيع الطالب</div><div>التاريخ</div></div>
</div>
<p class="sm" style="color:var(--ink-3);margin-top:6mm">
<strong>المصادر:</strong> الدرجة والخطة الدراسية لدفعة 2020–2023 · جداول المقررات لخريف وربيع
2025/2026 (ARED · CUTM · EDUC · PSYC · TECH · ARAB+SOCY) · استمارة تدقيق الخطة الدراسية ·
النظام الأكاديمي للدراسات الجامعية الأولى بجامعة السلطان قابوس (البنود ب-1-1 · ب-3 · ج-10 · د-2 · د-6).<br>
<strong>إعادة التوليد:</strong> <span class="mono">python3 scripts/build_pdf.py</span> ·
<strong>التدقيق:</strong> <span class="mono">python3 scripts/validate_roadmap.py</span></p>
<div class="box stamp" style="border-top-width:1pt;margin-top:5mm"><p class="sm">
<strong>تنبيه:</strong> هذه الوثيقة أداة تخطيط وتفاوض، وليست قراراً أكاديمياً. حالة «المنجَز»
مستنتَجة من إفادة الطالب لا من كشف درجات رسمي. لا شيء هنا نافذ قبل اعتماد المرشد الأكاديمي
وعمادة القبول والتسجيل.</p></div>""", title="مسودة خطاب الاستثناء", tag="صفحة الخطاب")


def main():
    d = json.loads(DATA.read_text(encoding="utf-8"))
    doc = build(d)
    HTML_OUT.write_text(doc.html(font_css()), encoding="utf-8")
    print(f"✓ {HTML_OUT.name}  —  {len(doc.pages)} صفحة، {HTML_OUT.stat().st_size // 1024} KB")

    if not pathlib.Path(CHROME).exists():
        sys.exit(f"✘ متصفح Chromium غير موجود عند {CHROME}")
    subprocess.run([CHROME, "--headless", "--disable-gpu", "--no-sandbox",
                    "--no-pdf-header-footer", "--run-all-compositor-stages-before-draw",
                    "--virtual-time-budget=20000",
                    f"--print-to-pdf={PDF_OUT}", HTML_OUT.as_uri()],
                   check=True, capture_output=True)
    print(f"✓ {PDF_OUT.name}  —  {PDF_OUT.stat().st_size // 1024} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
