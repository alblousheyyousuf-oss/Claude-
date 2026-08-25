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
from collections import defaultdict

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

/* ── الاستمارة الرسمية ─────────────────────── */
.form{ border:1.5pt solid var(--ink); padding:6mm; height:100%; display:flex; flex-direction:column }
.form h1{ font-size:14pt; text-align:center; text-decoration:underline;
  text-underline-offset:3pt; color:var(--stamp); margin:0 0 5mm }
.form .fields{ font-size:9pt; line-height:2.1; margin-bottom:4mm }
.form .fields span{ display:inline-block; min-width:34mm }
.form .fields b{ font-weight:600; border-bottom:.5pt dotted var(--ink-3); padding:0 3mm }
.fgrid{ display:grid; grid-template-columns:repeat(3,1fr); border:.8pt solid var(--ink);
  border-inline-start:0; margin-bottom:0 }
.fgrid > div{ border-inline-start:.8pt solid var(--ink); display:flex; flex-direction:column }
.fband{ background:#F3E3E3; text-align:center; font-weight:600; font-size:9pt;
  padding:1.4mm; border-bottom:.8pt solid var(--ink) }
.fsub{ display:grid; grid-template-columns:1fr 22mm; font-size:7.4pt; color:var(--ink-2);
  text-align:center; border-bottom:.5pt solid var(--rule) }
.fsub span{ padding:1mm .5mm }
.fsub span:first-child{ border-inline-start:.5pt solid var(--rule) }
.frow{ display:grid; grid-template-columns:1fr 22mm; font-size:8pt; min-height:6mm }
.frow span{ padding:1.1mm 2mm }
.frow span:last-child{ text-align:center; border-inline-end:.5pt solid var(--rule-2) }
.ftot{ display:grid; grid-template-columns:1fr 22mm; font-size:8.4pt; font-weight:600;
  border-top:.8pt solid var(--ink); margin-top:auto; background:var(--wash) }
.ftot span{ padding:1.4mm 2mm } .ftot span:last-child{ text-align:center }
.fnote{ border:.8pt solid var(--ink); border-top:0; padding:3mm; font-size:8pt; min-height:20mm }
.fnote .lbl{ background:#F3E3E3; display:block; margin:-3mm -3mm 2mm; padding:1.4mm;
  text-align:center; font-weight:600; font-size:9pt; border-bottom:.8pt solid var(--ink) }
.fsig{ display:flex; justify-content:space-around; margin-top:auto; padding-top:8mm; font-size:8.4pt }
.fsig div{ border-top:.5pt dotted var(--ink-3); padding-top:1.5mm; width:52mm; text-align:center }
.ffoot{ text-align:center; font-size:7.4pt; color:var(--ink-2); margin-top:4mm; line-height:1.7 }

/* ── الجدول الأسبوعي ───────────────────────── */
.wk{ margin-bottom:4mm }
.wk-hd{ display:flex; align-items:baseline; gap:3mm; margin-bottom:1.5mm }
.wk-hd .t{ font-family:"Reem Kufi",sans-serif; font-weight:600; font-size:10pt }
.wk-hd .m{ margin-inline-start:auto; font-size:7.8pt; color:var(--ink-2) }
.wk-days{ display:grid; grid-template-columns:14mm repeat(5,1fr); font-size:7.6pt;
  font-weight:600; color:var(--ink-2); text-align:center }
.wk-days span{ padding:1mm 0; border-bottom:.8pt solid var(--rule) }
.wk-body{ display:grid; grid-template-columns:14mm repeat(5,1fr); position:relative }
.wk-times{ position:relative; font-size:6.6pt; color:var(--ink-3) }
.wk-times i{ position:absolute; inset-inline-end:1.5mm; font-style:normal; transform:translateY(-1mm) }
.wk-col{ position:relative; border-inline-start:.5pt solid var(--rule-2) }
.wk-col:last-child{ border-inline-end:.5pt solid var(--rule-2) }
.wk-hr{ position:absolute; inset-inline:0; border-top:.5pt solid var(--rule-2) }
.wk-blk{ position:absolute; inset-inline:.6mm; border:.6pt solid; border-inline-start-width:1.6pt;
  padding:.8mm 1mm; font-size:6.8pt; line-height:1.3; overflow:hidden }
.wk-blk b{ display:block; font-weight:600; font-size:7.2pt }
.wk-blk .s{ display:block; margin-top:.4mm; font-size:6.2pt; opacity:.85 }
.wk-blk.fall{ color:var(--fall); background:var(--fall-wash) }
.wk-blk.spring{ color:var(--spring); background:var(--spring-wash) }
.wk-blk.field{ color:var(--stamp); background:var(--stamp-wash) }
.wk-legend{ font-size:7.4pt; color:var(--ink-2); margin-top:1.5mm; line-height:1.6 }
"""


# ══════════════════════════════════════════════════════════════
# المخططات
# ══════════════════════════════════════════════════════════════
ARROW_DEFS = """<defs><marker id="ah" viewBox="0 0 10 10" refX="9" refY="5"
 markerWidth="7" markerHeight="7" orient="auto-start-reverse">
 <path d="M0,1 L9,5 L0,9 z" fill="currentColor"/></marker></defs>"""


def fig_critical_path():
    return f"""<svg viewBox="0 0 900 330" role="img" aria-label="ترفن2110 وترفن3111 خريفيان يؤديان إلى ترفن4260 المشروع الفني الخريفي، الذي يؤدي إلى التدريب الميداني. المشروع خريفي حصراً فيفرض خريفين متتاليين.">
{ARROW_DEFS}
<rect x="40" y="56" width="800" height="88" class="s-lane-f"/>
<rect x="40" y="214" width="800" height="66" class="s-lane-s"/>
<text x="812" y="48" class="s-lbl s-fall" text-anchor="middle">خريف</text>
<text x="812" y="206" class="s-lbl s-spring" text-anchor="middle">ربيع</text>
<line x1="40" y1="32" x2="860" y2="32" class="s-hair"/>
<text x="740" y="24" class="s-s" text-anchor="middle">خريف 2026</text>
<text x="540" y="24" class="s-s" text-anchor="middle">ربيع 2027</text>
<text x="340" y="24" class="s-s" text-anchor="middle">خريف 2027</text>
<text x="150" y="24" class="s-s" text-anchor="middle">ربيع 2028</text>
<line x1="740" y1="28" x2="740" y2="36" class="s-hair"/><line x1="540" y1="28" x2="540" y2="36" class="s-hair"/>
<line x1="340" y1="28" x2="340" y2="36" class="s-hair"/><line x1="150" y1="28" x2="150" y2="36" class="s-hair"/>

<rect x="652" y="62" width="176" height="34" class="s-node s-fall-s"/>
<text x="740" y="83" class="s-t" text-anchor="middle" font-weight="600">ترفن2110 النسيج</text>
<rect x="652" y="104" width="176" height="34" class="s-node s-fall-s"/>
<text x="740" y="125" class="s-t" text-anchor="middle" font-weight="600">ترفن3111 الفن المعاصر</text>

<rect x="252" y="76" width="176" height="48" class="s-node s-fall-s" stroke-width="2"/>
<text x="340" y="96" class="s-t" text-anchor="middle" font-weight="600">ترفن4260</text>
<text x="340" y="112" class="s-s" text-anchor="middle">المشروع الفني · خريفي حصراً</text>

<rect x="62" y="222" width="176" height="48" class="s-node s-stamp-s" stroke-width="2"/>
<text x="150" y="242" class="s-t s-stamp" text-anchor="middle" font-weight="600">منطر4600</text>
<text x="150" y="258" class="s-s" text-anchor="middle">التدريب الميداني · 7 س</text>

<path d="M652,100 L470,100 L432,100" class="s-line" marker-end="url(#ah)"/>
<text x="545" y="92" class="s-s" text-anchor="middle">متطلبان سابقان</text>
<path d="M252,100 L200,100 L200,246 L242,246" class="s-line" marker-end="url(#ah)"/>
<text x="204" y="176" class="s-s" text-anchor="middle">البوابة</text>

<text x="545" y="122" class="s-s s-stamp" text-anchor="middle">لا يُطرح ربيعاً ⇒ الانتظار سنة</text>
<path d="M640,140 C580,168 460,168 420,146" class="s-line s-dash s-stamp-s" opacity=".55"/>
<text x="530" y="300" class="s-s s-stamp" text-anchor="middle">✕ لا فصل صيفي — القسم لا يطرحه</text>
</svg>"""


def fig_bottleneck():
    """ما الذي يشتريه الاستثناء E1: خريفان متتاليان أم خريف واحد."""
    def box(x, y, w, h, cls, label, sub=""):
        t = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" class="s-node {cls}"/>'
        t += f'<text x="{x + w / 2}" y="{y + (18 if sub else h / 2 + 4)}" class="s-t" text-anchor="middle">{label}</text>'
        if sub:
            t += f'<text x="{x + w / 2}" y="{y + 32}" class="s-s" text-anchor="middle">{sub}</text>'
        return t
    return f"""<svg viewBox="0 0 900 250" role="img" aria-label="بلا استثناء يحتاج المشروع الفني خريفاً ثانياً فتصير الخطة أربعة فصول؛ وباستثناء تزامنه مع متطلبيه تُختصر إلى ثلاثة فصول.">
{ARROW_DEFS}
<text x="700" y="22" class="s-lbl" text-anchor="middle">بلا استثناء — أربعة فصول</text>
{box(600, 40, 190, 44, "s-fall-s", "خريف 2026", "ترفن2110 · ترفن3111")}
{box(600, 100, 190, 44, "s-fall-s", "خريف 2027", "ترفن4260 المشروع")}
{box(600, 160, 190, 40, "s-stamp-s", "ربيع 2028 — التدريب")}
<path d="M695,84 L695,96" class="s-line" marker-end="url(#ah)"/>
<path d="M695,144 L695,156" class="s-line" marker-end="url(#ah)"/>
<text x="700" y="222" class="s-t" text-anchor="middle" font-weight="600">التخرج يونيو 2028</text>

<line x1="470" y1="34" x2="470" y2="232" class="s-hair"/>

<text x="240" y="22" class="s-lbl" text-anchor="middle">بالاستثناء E1 — ثلاثة فصول</text>
{box(140, 40, 190, 64, "s-fall-s", "خريف 2026", "ترفن2110 · ترفن3111 · ترفن4260 معاً")}
{box(140, 120, 190, 40, "s-spring-s", "ربيع 2027")}
{box(140, 176, 190, 40, "s-stamp-s", "خريف 2027 — التدريب")}
<path d="M235,104 L235,116" class="s-line" marker-end="url(#ah)"/>
<path d="M235,160 L235,172" class="s-line" marker-end="url(#ah)"/>
<text x="240" y="238" class="s-t" text-anchor="middle" font-weight="600" fill="var(--ok)">التخرج يناير 2028</text>
<text x="405" y="128" class="s-s s-stamp" text-anchor="middle">يوفّر</text>
<text x="405" y="144" class="s-s s-stamp" text-anchor="middle">فصلاً</text>
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
                         ("ز3 — اختياري (ج)", "ARED3170"), ("ز4 — اختياري (د)", "ARED4130")])
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
              "لاغٍ", "ok", "الخمسة **مُنجَزة فعلاً** في ربيع 2026 حسب كشف الدرجات",
              "سبقه الطالب — لم تعد هذه الكتلة قائمة"),
             ("ترفن4260 المشروع الفني مع ترفن2110 وترفن3111 في الفصل نفسه",
              "مخالفة", "stamp", "كلاهما من متطلباته السبعة",
              "هذا بالضبط ما يطلبه الاستثناء E1 صراحةً بدل ضمناً"),
             ("منطر4600 التدريب الميداني — 7 ساعات",
              "غائب", "stamp", "لا ذكر له في الاستمارة", "فصل مستقل مخصص له"),
             ("عربي1060 اللغة العربية",
              "غائب", "stamp", "راسب فيه (F) والاستمارة لا تذكره",
              "إعادة إلزامية — متطلب جامعة"),
             ("منطر4400 مشروع التخرج مصاحباً للتدريب",
              "لاغٍ", "fall", "القرار الجديد يمنع مصاحبة أي مقرر للتدريب",
              "يُقدَّم إلى الفصل السابق"),
             ("ترتيب ربيع ← خريف ← ربيع",
              "سليم", "ok", "صحيح موسمياً", "المنطق صحيح، لكن قاعدته تجاوزها الزمن")]
    arows = "".join(
        f'<tr><td>{a}</td><td><span class="chip {cls}">{v}</span> {why}</td><td>{fix}</td></tr>'
        for a, v, cls, why, fix in audit)
    doc.sheet(f"""
<p class="lede">الاستمارة كُتبت <strong>قبل</strong> فصل ربيع 2026، فبعض ما تقترحه صار مُنجَزاً
فعلاً. وما بقي منها فيه ثلاث مخالفات حقيقية. تُعرض هنا لأنها ما زالت الوثيقة المتداولة مع القسم.</p>
<table class="bx" style="margin-bottom:6mm"><thead><tr><th style="width:58mm">ما في المقترح</th>
<th>الحكم</th><th style="width:52mm">التصحيح</th></tr></thead><tbody>{arows}</tbody></table>
<h3>حصيلة المدقّق الآلي</h3>
<div class="cols">
 <div class="box" style="border-top:2pt solid var(--stamp)">
  <span class="lbl">المقترح مقابل كشف الدرجات</span>
  <p><strong style="font-size:15pt;color:var(--stamp)">15</strong> مخالفة — أغلبها لأن المقترح
  يجدول مقررات <strong>سبق أن نجح فيها الطالب</strong>، ويُفوّت عربي1060 والتدريب الميداني.</p></div>
 <div class="box" style="border-top:2pt solid var(--ok)">
  <span class="lbl">ما بقي صالحاً منه</span>
  <p>حدْسه الموسمي كان سليماً. والخلل الجوهري الوحيد الباقي هو <strong>تزامن المشروع الفني
  مع متطلبيه</strong> — وهو ما تحوّل الآن إلى استثناء يُطلب صراحةً لا خطأ يُرتكب ضمناً.</p></div>
</div>
<p class="sm" style="color:var(--ink-3)">الاختباران السلبيان مضمَّنان في
<span class="mono">scripts/validate_roadmap.py</span> ويفشلان عمداً — وهو ما يثبت أن المدقّق
يكشف الأخطاء فعلاً بدل الادعاء.</p>""", title="تدقيق مقترح المرشد", tag="صفحة 5")

    # ── 6 · المسار الحرج ──────────────────────────────────────
    doc.sheet(f"""
<p class="lede">بعد كشف الدرجات انتقل المسار الحرج بالكامل. سلسلة `منطر3027 ← منطر4027` انكسرت لأن أولهما مُنجَز. وحلّت محلها سلسلة أضيق: <strong>المشروع الفني ومتطلباه — ثلاثتها خريفية</strong>.</p>
<figure>{fig_critical_path()}
<figcaption><strong>لماذا يفرض المشروع الفني خريفين:</strong> `ترفن4260` لا يُطرح إلا خريفاً،
ومتطلباه `ترفن2110` و`ترفن3111` خريفيان أيضاً. فإن أُخذا في خريف 2026 لم يَحِن دور المشروع
إلا خريف 2027 — سنة كاملة انتظاراً. وهذا وحده هو ما يجعل الخطة أربعة فصول بدل ثلاثة.</figcaption></figure>
<h3>شرط تسجيل التدريب الميداني — نصّ الخطة</h3>
<div class="box">
<p class="sm">١ · «إكمال جميع المقررات في الخطة الدراسية المعتمدة بنجاح عدا مقرر مشروع التخرج
الذي يتم دراسته كمقرر مصاحب مع مقرر التدريب الميداني».<br>
٢ · «أن يكون المعدل التراكمي للمرشح 2 على الأقل في نهاية الفصل الدراسي الذي يسبق التدريب الميداني».</p>
</div>
<p>الشرط الأول هو ما يجعل الفصل الأخير <strong>مقفلاً</strong>: أي مقرر متأخر لا يؤخّر نفسه فحسب،
بل يعطّل التدريب الميداني ومعه التخرج كله. والشرط الثاني يجعل معدلك — وهو في نطاق 2.00–2.99 —
عاملاً حرجاً في نهاية الفصل السابق للتدريب.</p>
<div class="box stamp"><span class="lbl">قرار جديد: عزل التدريب الميداني</span>
<p>أفاد الطالب بقرار أحدث من وثيقة الخطة: <strong>يُسجَّل التدريب الميداني وحده، ولا يُسمح معه
إلا متطلب جامعة واحد اختيارياً.</strong> وعليه نُقل `منطر4400` مشروع التخرج إلى الفصل السابق —
وهو ترتيب يُرضي القراءتين: القرار الجديد لا يُنتهك، وبوابة التدريب تُستوفى من باب أولى.
والتدريب يشغل <strong>الأيام الخمسة 08:00–13:50</strong>، فالمرافق يجب أن يكون شعبة مسائية —
وقد ثبت وجود <strong>ثلاث شعب مسائية</strong> لـ`اجمع1005`، وهي المثبتة في الجدول الأسبوعي.</p></div>""",
        title="المسار الحرج", tag="صفحة 6")

    # ── 7 · اختناق الربيع ─────────────────────────────────────
    exc_rows = "".join(
        f'<tr><td class="mono">{k}</td><td>{v["label"]}</td><td>{v["cost"]}</td><td class="sm">{v["authority"]}</td></tr>'
        for k, v in d["exceptions"].items())
    doc.sheet(f"""
<p class="lede">لم يعد ثمّة اختناق يفرض استثناءً. السؤال صار اختيارياً بالكامل:
<strong>هل تطلب استثناءً يختصر فصلاً، أم تمضي بلا أي طلب إداري؟</strong></p>
<figure>{fig_bottleneck()}
<figcaption><strong>ما يشتريه الاستثناء:</strong> تزامن `ترفن4260` مع متطلبيه يجمع الخريفين
في واحد فيختصر فصلاً كاملاً. ويشتري معه <strong>هامش تعافٍ</strong>: لو رسبتَ في المشروع الفني
وهو في خريف 2026، تُعيده خريف 2027 ويبقى التخرج يونيو 2028. أما لو كان في خريف 2027 (بلا استثناء)
فالإعادة تنتظر خريف 2028 والتخرج ينزلق إلى يونيو 2029.</figcaption></figure>
<h3>سلّم الاستثناءات</h3>
<table class="bx" style="margin-bottom:4mm"><thead><tr><th>الرمز</th><th>الاستثناء</th>
<th>الكلفة</th><th>الجهة</th></tr></thead><tbody>{exc_rows}</tbody></table>
<div class="box ok"><span class="lbl">المقايضة صراحةً</span>
<p><strong>مع الاستثناء:</strong> فصل أقصر وهامش تعافٍ — لكنك تدرس مقرر المشروع قبل أن تدرس
النسيج والفن المعاصر، وهما مادته الخام، فيرتفع احتمال التعثّر فيه.<br>
<strong>بلا الاستثناء:</strong> تدرس المشروع بعد أن تُتقن متطلبيه، بأحمال مريحة وبلا أي طلب
إداري — مقابل فصل إضافي. <strong>القرار لك، والخطتان معروضتان كاملتين.</strong></p></div>""",
        title="الاستثناء: ما يشتريه وما يكلّفه", tag="صفحة 7")

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

    # القسم الثاني: استمارة رسمية لكل خطة، ثم جداولها الأسبوعية
    meetings = load_meetings()
    tr = load_transcript()
    if tr:
        page_transcript_audit(doc, d, tr)
        page_whats_changed(doc, d, tr)
    doc.sheet("""
<p class="lede">القسم الأول من هذه الوثيقة يحلّل الخطط. وهذا القسم يحوّلها إلى ورق عملي:
<strong>استمارة تدقيق رسمية مملوءة</strong> لكل خطة جاهزة للتوقيع، ثم <strong>جدول أسبوعي
لكل فصل</strong> في كل خطة.</p>
<h3>ما تضيفه الجداول الأسبوعية</h3>
<p>الخطط حتى الآن فُحصت ضد الساعات والمتطلبات السابقة والموسمية. الجداول الأسبوعية تفحصها ضد
بُعد رابع لم يُختبر: <strong>الساعة والدقيقة</strong>. لكل فصل بُحث آلياً عن إسناد شعبة لكل مقرر
بحيث لا يتعارض مقرران، والنتيجة أن <strong>الفصول التسعة عشر في الخطط الأربع كلها خالية من
التعارض</strong>.</p>
<div class="box ok"><span class="lbl">أثر ذلك على طلب الاستثناء</span>
<p>فصل ربيع 2027 في السيناريو أ — سبعة مقررات و18 ساعة — <strong>يتوزّع على أربعة أيام
والخميس فيه فارغ</strong>. هذه حجّة مادية أمام رئيس القسم: لا تطلب استثناءً على ورق، بل تعرض
جدولاً أسبوعياً فعلياً يعمل. والتوزيع شبه إجباري لأن أربعة من السبعة لها شعبة واحدة فقط.</p></div>
<div class="box" style="border-top:2pt solid var(--fall)">
<span class="lbl">تعارض حقيقي جرى تفاديه</span>
<p><strong>ترفن4140</strong> مقفل على الأحد صباحاً، و<strong>منطر4027</strong> شعبتاه 01 و02 على
الأحد صباحاً أيضاً. لولا هذا الفحص لاصطدمتَ بذلك يوم التسجيل. الحل: الشعبة 03 (الثلاثاء) —
وهو ما اختاره الحلّال تلقائياً.</p></div>
<div class="box stamp" style="border-top-width:1pt"><span class="lbl">حدود هذه المواعيد</span>
<p class="sm">المواعيد مستخرَجة من جدولَي <strong>خريف وربيع 2025/2026</strong> الرسميين
(1803 لقاء، تغطية 98%). القسم يعيد نشر جداوله كل عام وقد تتغيّر الأوقات والقاعات وأعداد الشعب.
اعتبرها <strong>نمطاً متوقَّعاً لا التزاماً</strong>، وثبّتها عند فتح التسجيل.
ومقرر <strong>اجمع1005</strong> لم تُستخرج مواعيده (ملف قسم الاجتماع تعذّر تحليله) وله عشر شعب
فيُختار منها ما يناسب الفراغ.</p></div>""",
        title="القسم الثاني · الاستمارات والجداول الأسبوعية", tag="مدخل")
    for k in ["A", "B", "C", "D"]:
        page_form(doc, d, k)
    for k in ["A", "B", "C", "D"]:
        pages_weekly(doc, d, k, meetings)


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
      "هل يقبل القسم تقديم منطر4400 مشروع التخرج على فصل التدريب الميداني؟ "
      "الخطة تصفه بأنه «مصاحب»، والقرار الجديد يمنع المصاحبة — والترتيب المعتمد هنا "
      "(المشروع قبل التدريب) يُرضي القراءتين، لكن يلزم تثبيته كتابةً.",
      "هل يُقبل متطلب جامعة واحد مع التدريب الميداني فعلاً، وبأي شعبة؟ "
      "المثبت هنا اجمع1005 بشعبة مسائية (الأربعاء 14:15–16:05).",
      "هل توجد درجة دنيا للمتطلب السابق؟ ترفن3210 مُنجَز بتقدير D وهو متطلب ترفن4120.",
      "متطلب ترفن4120: بلا متطلب («القائمة و») أم ترفن3210 (الجدول الفصلي)؟ "
      "لم يعد مؤثراً لأن ترفن3210 منجَز — لكن التوثيق يبقى متناقضاً.",
      "متطلب ترفن2110 — الخطة تحيله إلى نفسه، وهو خطأ مطبعي ظاهر.",
      "هل تُحتسب إعادة عربي1060 بديلاً عن الرسوب في المعدل التراكمي أم يُجمع التقديران؟ "
      "يؤثر مباشرة في هامش الـ2.00 المطلوب للتدريب الميداني.",
      "ثبات الدوران الموسمي في 2026/2027 — مؤكَّد لعام 2025/2026 ويُفترض تكراره.",
      "سعة شعب ترفن4260 (8 لكل شعبة) وترفن3250 وترفن4130 لفصولك المستهدفة.",
    ]
    doc.sheet(f"""
<h3>المخاطر مرتَّبة بالخطورة</h3>
<div style="margin-bottom:6mm">{rrows}</div>
<h3>ما يجب تثبيته قبل التسجيل</h3>
<p class="sm lede">حالة المقررات لم تعد افتراضاً — كشف الدرجات حسمها. وما بقي هنا أسئلة
إجرائية للقسم، أهمّها الأولان لأنهما يمسّان بنية فصل التخرج.</p>
<ol class="ck">{"".join(f"<li><span>{c}</span></li>" for c in checks)}</ol>""",
        title="المخاطر وقائمة التحقق", tag="صفحة المخاطر")

    doc.sheet(f"""
<p class="lede">هذا الخطاب لازم <strong>فقط</strong> إن اخترتَ المسار الأسرع (يناير 2028). الخطة الموصى بها لا تحتاج أي طلب إداري.</p>
<div class="letter">
<p><strong>إلى:</strong> رئيس قسم التربية الفنية / مساعد عميد كلية التربية للدراسات الجامعية الأولى<br>
<strong>الموضوع:</strong> طلب استثناء لتسجيل مقرر المشروع الفني متزامناً مع متطلبيه</p>
<p>تحية طيبة وبعد،</p>
<p>أنا الطالب <strong>{d["meta"]["student"]}</strong>، الرقم الجامعي
<span class="mono">{d["meta"]["student_id"]}</span>، تخصص التربية الفنية، دفعة {d["meta"]["cohort"]}.
أنهيتُ <strong>{d["meta"]["credits_earned"]} ساعة معتمدة</strong> من أصل 125 وفق كشف الدرجات
الرسمي، وتبقّى لي <strong>{d["meta"]["credits_remaining"]} ساعة</strong>.</p>
<p>وقد راجعتُ توزيع المتبقي على المواسم فتبيّن ما يلي:</p>
<p>١ · مقرر <strong>ترفن4260 المشروع الفني</strong> لا يُطرح إلا في فصل الخريف.<br>
٢ · متطلباه السابقان <strong>ترفن2110</strong> و<strong>ترفن3111</strong> خريفيان أيضاً.<br>
٣ · وعليه، إن درستُ المتطلبين في خريف 2026 لم يَحِن دور المشروع إلا في خريف 2027، فيمتدّ
برنامجي إلى أربعة فصول وأتخرّج في يونيو 2028.</p>
<p>وألتمس من سعادتكم الموافقة على <strong>تسجيل ترفن4260 متزامناً مع ترفن2110 وترفن3111 في
فصل خريف 2026</strong>، وهو ما يمكّنني من التخرج في <strong>يناير 2028</strong> — أي أبكر بفصل
دراسي كامل.</p>
<p>وأودّ الإفادة بأن مواعيد المقررات الستة المقترحة لذلك الفصل <strong>لا تتعارض زمنياً</strong>،
والجدول الأسبوعي مرفق. كما أن تقديم المشروع يمنحني هامشاً لإعادته في خريف 2027 لو تعثّرتُ فيه،
بينما تأخيره يجعل أي تعثّر يكلّفني سنة كاملة.</p>
<p><strong>المرفقات:</strong> كشف الدرجات الرسمي · خطة فصلية تفصيلية بالمتطلبات السابقة والموسمية ·
استمارة تدقيق الخطة الدراسية مملوءة · جدول أسبوعي لكل فصل يثبت خلوّه من التعارض.</p>
<p>وفي حال تعذّر الاستثناء، فإني ماضٍ في الخطة البديلة (أربعة فصول، تخرّج يونيو 2028) وهي
<strong>لا تتطلب أي استثناء</strong>.</p>
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



# ══════════════════════════════════════════════════════════════
# المواعيد وحلّال التعارض
# ══════════════════════════════════════════════════════════════
MEETINGS_PATH = ROOT / "docs" / "data" / "meetings.json"
DAYS = ["SUN", "MON", "TUE", "WED", "THU"]
DAY_AR = {"SUN": "الأحد", "MON": "الاثنين", "TUE": "الثلاثاء",
          "WED": "الأربعاء", "THU": "الخميس"}


TRANSCRIPT_PATH = ROOT / "docs" / "data" / "transcript.json"


def load_transcript():
    if not TRANSCRIPT_PATH.exists():
        return None
    return json.loads(TRANSCRIPT_PATH.read_text(encoding="utf-8"))


def load_meetings():
    if not MEETINGS_PATH.exists():
        return {}
    return json.loads(MEETINGS_PATH.read_text(encoding="utf-8"))["meetings"]


def _mins(hhmm):
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def _clash(a, b):
    return a["day"] == b["day"] and _mins(a["start"]) < _mins(b["end"]) \
        and _mins(b["start"]) < _mins(a["end"])


def candidates(meetings, term_season, code):
    """شعب المقرر بعد إسقاط المكرّرة زمنياً — أقلّ بحثاً وأوضح عرضاً."""
    secs = meetings.get(f"{term_season}:{code}", {})
    seen, out = set(), []
    for sec in sorted(secs):
        slots = sorted(secs[sec], key=lambda m: (DAYS.index(m["day"]), m["start"]))
        sig = tuple((m["day"], m["start"], m["end"]) for m in slots)
        if sig and sig not in seen:
            seen.add(sig)
            out.append((sec, slots))
    return out


def solve_term(meetings, season, codes):
    """يبحث عن إسناد شعبة لكل مقرر بلا تعارض زمني.

    يعيد dict فيه: assignment · flexible (مقررات بلا مواعيد) · forced (بلا بديل)
    · ok · conflicts (عند التعذّر).
    """
    pool = {c: candidates(meetings, season, c) for c in codes}
    flexible = [c for c, v in pool.items() if not v]
    fixed = [c for c in codes if pool[c]]
    fixed.sort(key=lambda c: len(pool[c]))          # الأكثر تقييداً أولاً

    assign, chosen = {}, []

    def place(i):
        if i == len(fixed):
            return True
        code = fixed[i]
        for sec, slots in pool[code]:
            if any(_clash(s, t) for s in slots for _, t in chosen):
                continue
            assign[code] = (sec, slots)
            chosen.extend((code, s) for s in slots)
            if place(i + 1):
                return True
            del assign[code]
            del chosen[len(chosen) - len(slots):]
        return False

    ok = place(0)
    if not ok:
        clashes = []
        for a in range(len(fixed)):
            for b in range(a + 1, len(fixed)):
                ca, cb = fixed[a], fixed[b]
                if all(_clash(s, t) for _, sa in [pool[ca][0]] for s in sa
                       for _, sb in [pool[cb][0]] for t in sb):
                    clashes.append((ca, cb))
        return {"ok": False, "assignment": {}, "flexible": flexible,
                "forced": [], "conflicts": clashes}

    forced = [c for c in fixed if len(pool[c]) == 1]
    return {"ok": True, "assignment": assign, "flexible": flexible,
            "forced": forced, "conflicts": [],
            "alternatives": {c: len(pool[c]) for c in fixed}}


# ══════════════════════════════════════════════════════════════
# صفحات الاستمارة الرسمية والجداول الأسبوعية
# ══════════════════════════════════════════════════════════════
AR_KEY = {"A": "أ", "B": "ب", "C": "ج", "D": "د"}


def form_cell(d, term):
    """خلية فصل واحد في شبكة الاستمارة."""
    C = d["courses"]
    rows = "".join(
        f'<div class="frow"><span>{C[c]["ar"]} {C[c]["name"].split("—")[0].strip()}</span>'
        f'<span>{C[c]["cr"]}</span></div>' for c in term["courses"])
    if not term["courses"]:
        rows = f'<div class="frow"><span style="color:var(--stamp)">{term.get("note","—")}</span><span>—</span></div>'
    return (f'<div><div class="fband">{term["name"]}</div>'
            f'<div class="fsub"><span>رمز المقرر واسمه</span><span>عدد الساعات</span></div>'
            f'{rows}<div class="ftot"><span>مجموع الساعات</span>'
            f'<span>{credits(d, term["courses"])}</span></div></div>')



BUCKET_LABELS = {"م ج": ("متطلبات الجامعة", 6), "ا ج": ("اختياري الجامعة", 6),
                 "م ت": ("متطلبات التخصص", 102), "ا ت": ("اختياري التخصص", 11)}


def page_transcript_audit(doc, d, tr):
    """البرهان: الأوعية الأربعة ومطابقتها لكشف الدرجات."""
    C = d["courses"]
    rows = ""
    for cat, (label, need) in BUCKET_LABELS.items():
        done = sum(v["cr"] for v in C.values()
                   if v["cat"] == cat and v["status"] == "completed")
        rows += (f'<tr><td>{label}</td><td class="n">{need}</td>'
                 f'<td class="n"><strong>{done}</strong></td>'
                 f'<td class="n">{need - done}</td></tr>')
    t = tr["totals"]
    fails = "، ".join(tr["failures"]) or "لا شيء"
    wd = "، ".join(tr["withdrawals"]) or "لا شيء"

    by_term = {}
    for r in tr["records"]:
        by_term.setdefault(r["term"], []).append(r)
    order = sorted(by_term, key=lambda x: (int(x.split()[-1]), 0 if "ربيع" in x else 1))
    terms_html = ""
    for term in order:
        recs = by_term[term]
        cells = "".join(
            f'<tr><td class="c">{r["code"]}</td><td>{r["title"][:26]}</td>'
            f'<td class="n">{r["credits"]}</td>'
            f'<td class="n" style="color:{"var(--stamp)" if not r["passed"] and r["credits"] else "inherit"}">'
            f'{r["grade"]}</td></tr>' for r in recs)
        got = sum(r["credits"] for r in recs if r["passed"])
        terms_html += (f'<div style="break-inside:avoid"><p class="sm" style="font-weight:600;'
                       f'margin:0 0 1mm">{term} — {got} ساعة مكتسبة</p>'
                       f'<table class="bx" style="margin-bottom:3mm">{cells}</table></div>')

    doc.sheet(f"""
<p class="lede">هذه الصفحة هي <strong>البرهان</strong>: كل ساعة في الخطة محسوبة من كشف الدرجات
الرسمي، لا من أي فرضية. والمجموع يُغلق على رقم الكشف نفسه.</p>
<div class="cols">
<table class="bx"><thead><tr><th>الوعاء</th><th class="n">المطلوب</th>
<th class="n">المنجَز</th><th class="n">المتبقي</th></tr></thead>
<tbody>{rows}
<tr style="background:var(--wash);font-weight:600"><td>المجموع</td>
<td class="n">125</td><td class="n">{t["earned"]}</td><td class="n">{125 - t["earned"]}</td></tr>
</tbody></table>
<div class="box ok"><span class="lbl">المطابقة</span>
<p class="sm">المحسوب من الخطة: <strong>{t["earned"]} ساعة</strong><br>
المطبوع في الكشف: <strong>TOTAL CREDITS EARNED {t["earned"]}.00</strong><br>
الساعات المُحاوَلة: {t["attempted"]} · نقاط التقدير: {t["points"]} ·
المعدل التراكمي <strong>{t["cgpa"]}</strong><br>
✓ الرقمان متطابقان — والمدقّق الآلي يُخفق تلقائياً لو اختلفا.</p></div>
</div>
<div class="cols" style="margin-bottom:4mm">
<div class="box" style="border-top:2pt solid var(--stamp)"><span class="lbl">رسوب</span>
<p class="sm"><span class="mono">{fails}</span> — إعادة إلزامية، وهو متطلب جامعة.</p></div>
<div class="box" style="border-top:2pt solid var(--fall)"><span class="lbl">انسحابات</span>
<p class="sm"><span class="mono">{wd}</span> — استُهلك {len(tr["withdrawals"])} من 4 مسموحة.</p></div>
</div>
<p class="sm" style="color:var(--ink-3)">سجل المقررات كاملاً — {len(tr["records"])} تسجيلاً
في {t["terms_registered"]} فصلاً — في الصفحة التالية.</p>""",
        title="تدقيق كشف الدرجات", tag="البرهان")

    doc.sheet(f"""
<p class="lede">كل تسجيل في السجل الأكاديمي، فصلاً بفصل. التقديرات الحمراء لم تُحتسب ضمن
الساعات المكتسبة: <span class="mono">W</span> انسحاب · <span class="mono">F</span> رسوب ·
<span class="mono">TC</span> ساعات محوَّلة بصفر ساعة (البرنامج التأسيسي).</p>
<div style="column-count:3;column-gap:5mm;font-size:7.2pt">{terms_html}</div>""",
        title="السجل الأكاديمي الكامل", tag=f"{len(tr['records'])} تسجيلاً")


def page_whats_changed(doc, d, tr):
    changes = [
      ("المنجَز والمتبقي", "75 منجَزة · 50 متبقية",
       f"<strong>{tr['totals']['earned']} منجَزة · {125 - tr['totals']['earned']} متبقية</strong>"),
      ("منطر3027 طرق تدريس (1)", "متبقٍ — وكان رأس المسار الحرج",
       "<strong>مُنجَز</strong> ربيع 2026 · C+ ⇒ المسار الحرج القديم زال"),
      ("عربي1060 اللغة العربية", "محسوب منجَزاً",
       "<strong>راسب فيه (F)</strong> خريف 2023 ⇒ إعادة إلزامية"),
      ("ترفن2130 · 3140 · 3210 · 4111", "أربعة مقررات متبقية",
       "<strong>الأربعة مُنجَزة</strong> ربيع 2026"),
      ("اختناق الربيع", "7 مقررات ربيعية في فصل واحد ⇒ استثناء لا مفرّ منه",
       "<strong>زال</strong> — لم يبقَ ربيعياً سوى مقررين (5 ساعات)"),
      ("متطلب ترفن4120", "نزاع قد يكلّف فصلاً كاملاً",
       "<strong>زال</strong> — متطلبه ترفن3210 مُنجَز (D)"),
    ]
    rows = "".join(f'<tr><td>{a}</td><td style="color:var(--ink-3)">{b}</td><td>{c}</td></tr>'
                   for a, b, c in changes)
    doc.sheet(f"""
<p class="lede">النسخة السابقة من هذه الوثيقة بُنيت على إفادة شفهية: «أنهيتُ كل الخطة عدا ما ورد
في استمارة التدقيق». الإفادة أغلقت الحساب رياضياً فبدت صحيحة — لكنها كانت
<strong>مخطئة بإحدى عشرة ساعة</strong>. كشف الدرجات الرسمي صحّحها.</p>
<div class="box stamp"><span class="lbl">لماذا تُذكر هذه الصفحة أصلاً</span>
<p>إن كنتَ قد عرضتَ النسخة السابقة على مرشدك أو رئيس القسم، فهذه الصفحة تبيّن ما تغيّر
ولماذا. إخفاء التصحيح أسوأ من إعلانه.</p></div>
<h3>التصحيحات الستة</h3>
<table class="bx" style="margin-bottom:5mm"><thead><tr>
<th style="width:42mm">البند</th><th style="width:58mm">ما كان مفترضاً</th>
<th>الحقيقة من كشف الدرجات</th></tr></thead><tbody>{rows}</tbody></table>
<div class="cols">
<div class="box ok"><span class="lbl">النتيجة الصافية — لصالحك</span>
<p class="sm">وضعك <strong>أفضل</strong> مما كان مقدَّراً: 11 ساعة إضافية منجَزة، والمسار الحرج
القديم زال، والاختناق الذي كان يفرض استثناءً لا مفرّ منه اختفى.
<strong>خطة يونيو 2028 صارت ممكنة بصفر استثناءات.</strong></p></div>
<div class="box" style="border-top:2pt solid var(--stamp)"><span class="lbl">وما ليس لصالحك</span>
<p class="sm">`عربي1060` راسب ويجب إعادته، والمعدل التراكمي <strong>{tr['totals']['cgpa']}</strong>
يعلو عتبة التدريب الميداني (2.00) بهامش {tr['totals']['cgpa'] - 2:.2f} فقط. وخانة اختياري
التخصص (أ) استُهلكت بانسحاب ثم بديل.</p></div>
</div>""", title="ما تغيّر بعد كشف الدرجات", tag="شفافية")


def page_form(doc, d, key):
    s, m = d["scenarios"][key], d["meta"]
    grad_year = "2028" if key in ("A", "B") else "2029"
    exc = " و".join(s["requires_exceptions"]) or "لا يوجد"
    terms = s["terms"]
    bands = [terms[i:i + 3] for i in range(0, len(terms), 3)]
    grid = "".join('<div class="fgrid">' + "".join(form_cell(d, t) for t in band)
                   + ("<div></div>" * (3 - len(band))) + "</div>" for band in bands)
    note = (f'الخطة مبنية على السيناريو <b>{AR_KEY[key]}</b> — {s["title"].split("—")[0].strip()}. '
            f'الاستثناء المطلوب: <b>{exc}</b>. '
            + ("الجدول الأسبوعي المرفق يثبت خلوّ الفصول من التعارض الزمني."
               if s.get("recommended") else
               "يُنظر إليه بديلاً إن تعذّر السيناريو الموصى به."))
    doc.sheet(f"""
<div class="form">
  <h1>استمارة ملخص تدقيق الخطة الدراسية</h1>
  <div class="fields">
    <span>اسم الطالب</span>: <b>{m["student"]}</b><br>
    <span>الرقم الجامعي</span>: <b>{m["student_id"]}</b><br>
    <span>التخصص</span>: <b>التربية الفنية</b><br>
    <span>الدفعة</span>: <b>{m["cohort"]}</b><br>
    <span>توقع التخرج</span>: <b>{grad_year}</b><br>
    <span>اسم المرشد الأكاديمي</span>: <b>{m["advisor"].replace("(رئيس القسم والمرشد الأكاديمي)", "").strip()}</b>
  </div>
  {grid}
  <div class="fnote"><span class="lbl">ملاحظات المرشد الأكاديمي</span>{note}</div>
  <div class="fsig"><div>توقيع الطالب</div><div>توقيع المرشد الأكاديمي</div></div>
  <p class="ffoot">بتوقيع الطالب على هذه الاستمارة فإنه يؤكد قيامه بمراجعة الخطة مع مرشده الأكاديمي
  ويعزم على الالتزام بما جاء بها حتى يتخرج في الوقت المحدد<br>
  مكتب مساعد العميد للدراسات الجامعية — كلية التربية</p>
</div>""")


DAY_START, DAY_END, MM_PER_MIN = 8 * 60, 18 * 60 + 30, 0.155


def merge_slots(slots):
    """يدمج لقاءات اليوم الواحد المتلاصقة (فجوة ≤ 15 دقيقة) في كتلة واحدة."""
    by_day = defaultdict(list)
    for s in slots:
        by_day[s["day"]].append(s)
    out = []
    for day, group in by_day.items():
        group.sort(key=lambda s: _mins(s["start"]))
        cur = dict(group[0])
        for nxt in group[1:]:
            if _mins(nxt["start"]) - _mins(cur["end"]) <= 15:
                cur["end"] = max(cur["end"], nxt["end"])
            else:
                out.append(cur)
                cur = dict(nxt)
        out.append(cur)
    return out


def weekly_block(d, key, term, res):
    """شبكة أسبوعية لفصل واحد."""
    C = d["courses"]
    height = (DAY_END - DAY_START) * MM_PER_MIN
    hours = "".join(
        f'<i style="top:{(h * 60 - DAY_START) * MM_PER_MIN:.1f}mm">{h}:00</i>'
        for h in range(8, 19))
    lines = "".join(
        f'<div class="wk-hr" style="top:{(h * 60 - DAY_START) * MM_PER_MIN:.1f}mm"></div>'
        for h in range(9, 19))
    cols = []
    for day in DAYS:
        blocks = ""
        for code, (sec, slots) in res["assignment"].items():
            for sl in merge_slots(slots):
                if sl["day"] != day:
                    continue
                top = (_mins(sl["start"]) - DAY_START) * MM_PER_MIN
                hgt = (_mins(sl["end"]) - _mins(sl["start"])) * MM_PER_MIN
                cls = "field" if code == "CUTM4600" else term["season"]
                name = C[code]["name"].split("—")[0].strip()
                # الكتل القصيرة لا تتسع للاسم كاملاً — يُقلَّص حتى لا يُقصّ سطر الوقت
                if hgt < 13:
                    name = ""
                elif hgt < 19:
                    name = name[:20] + ("…" if len(name) > 20 else "")
                blocks += (f'<div class="wk-blk {cls}" style="top:{top:.1f}mm;height:{hgt:.1f}mm">'
                           f'<b>{C[code]["ar"]}</b>{name}'
                           f'<span class="s">ش{sec} · {sl["start"]}–{sl["end"]}</span></div>')
        cols.append(f'<div class="wk-col">{lines}{blocks}</div>')

    busy = {sl["day"] for _, slots in res["assignment"].values() for sl in slots}
    free = [DAY_AR[x] for x in DAYS if x not in busy]
    flex = [C[c]["ar"] for c in res["flexible"]]
    legend = []
    if free:
        legend.append("أيام فارغة: " + " · ".join(free))
    if res["forced"]:
        legend.append("مقفلة على شعبة واحدة: " + " · ".join(C[c]["ar"] for c in res["forced"]))
    if flex:
        legend.append("بلا وقت في بيانات 2025/2026 (يُختار عند التسجيل): " + " · ".join(flex))
    if not legend:
        legend.append("كل المقررات لها بدائل شعب — مرونة كاملة في الترتيب")

    return (f'<div class="wk"><div class="wk-hd"><span class="chip {term["season"]}">'
            f'{SEASON_AR[term["season"]]}</span><span class="t">{term["name"]}</span>'
            f'<span class="m">{credits(d, term["courses"])} ساعة · {len(term["courses"])} مقررات · '
            f'{"بلا تعارض ✓" if res["ok"] else "تعارض ✗"}</span></div>'
            f'<div class="wk-days"><span></span>'
            + "".join(f"<span>{DAY_AR[x]}</span>" for x in DAYS) + '</div>'
            f'<div class="wk-body" style="height:{height:.1f}mm">'
            f'<div class="wk-times">{hours}</div>{"".join(cols)}</div>'
            f'<p class="wk-legend">{" · ".join(legend)}</p></div>')


def pages_weekly(doc, d, key, meetings):
    s = d["scenarios"][key]
    blocks = []
    for t in s["terms"]:
        if not t["courses"]:
            continue
        res = solve_term(meetings, t["season"], t["courses"])
        blocks.append(weekly_block(d, key, t, res))
    intro = (f'<p class="lede">السيناريو <strong>{AR_KEY[key]}</strong> — '
             f'{s["title"].split("—")[0].strip()}. المواعيد من جدولَي 2025/2026 '
             f'<strong>استرشادية</strong>، والشعب مختارة آلياً بحيث لا يتعارض مقرران في الفصل الواحد.</p>')
    for i in range(0, len(blocks), 2):
        doc.sheet((intro if i == 0 else "") + "".join(blocks[i:i + 2]),
                  title=f"الجدول الأسبوعي · السيناريو {AR_KEY[key]}",
                  tag="تتمة" if i else f"{len(blocks)} فصول")

if __name__ == "__main__":
    sys.exit(main())
