#!/usr/bin/env python3
"""يستخرج مواعيد المحاضرات من ملفات RPT_CourseSchedule إلى docs/data/meetings.json.

بنية هذه الملفات: الجدول عريض فيُقسَّم على صفحتين متتاليتين — الفردية تحمل الوقت
(القاعة · اليوم · البداية · النهاية) والزوجية تحمل المقرر (الرمز · الساعات · الشعبة).
الصفّان يتقابلان بالترتيب.

التحليل يعتمد على **إحداثيات الكلمات** لا على ترتيب النص، لأن استخراج العربية من
هذه الملفات يأتي معكوساً ومفكَّك الحروف.

الاستخدام:  python3 scripts/extract_schedule.py [مجلد_الملفات]
"""

import json
import pathlib
import re
import sys
from collections import defaultdict

import hashlib

import pymupdf

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "data" / "meetings.json"
UPLOADS = pathlib.Path("/root/.claude/uploads/ebee8a34-1b44-59e4-8f54-d4abd6b2f247")

DAY = re.compile(r"\b(SUN|MON|TUE|WED|THU)\b")
PREFIX = re.compile(r"^([A-Z]{4})(\d{1,3})$")   # الرمز ينكسر بأشكال شتى: ARAB10+19 · HIST101+0
TIME = re.compile(r"\b(\d{2}):(\d{2}):00\b")
HEADER_Y = 125
IDENTICAL_MAX = 5   # سقف التطابق العرضي بين الموسمين قبل اعتباره خطأ تصنيف

# مجلد الرفع يحوي كل ملف جدول مرتين ببادئتين مختلفتين. التصنيف السابق كان
# بقائمة بادئات مكتوبة يدوياً، فكانت النسخة الثانية من كل ملف خريفي تسقط خارج
# القائمة وتُصنَّف ربيعاً — فتُحقن بيانات الخريف في مفاتيح الربيع (160 مقرراً).
# البديل: إسقاط التكرار ببصمة المحتوى، ثم التصنيف بلاحقة التقرير التي تميّز
# المجموعتين: الخريف تقريره من ست صفحات (rdlc … rdlc_5) والربيع من أربع
# (rdlc_6 … rdlc_9).
FALL_SUFFIXES = ("", "_1", "_2", "_3", "_4", "_5")
SUFFIX = re.compile(r"rdlc(_\d+)?\.pdf$")


def season_of(path):
    m = SUFFIX.search(path.name)
    if not m:
        sys.exit(f"✘ لا يمكن تحديد موسم الملف: {path.name}")
    return "fall" if (m.group(1) or "") in FALL_SUFFIXES else "spring"


def dedupe(files):
    """يُبقي نسخة واحدة من كل ملف بحسب بصمة محتواه."""
    seen, out, dropped = {}, [], 0
    for f in sorted(files):
        h = hashlib.md5(f.read_bytes()).hexdigest()
        if h in seen:
            dropped += 1
            continue
        seen[h] = f
        out.append(f)
    return out, dropped

DAY_AR = {"SUN": "الأحد", "MON": "الاثنين", "TUE": "الثلاثاء",
          "WED": "الأربعاء", "THU": "الخميس"}


def body_words(page):
    return [(w[0], (w[1] + w[3]) / 2, w[4]) for w in page.get_text("words")
            if (w[1] + w[3]) / 2 > HEADER_Y]


def time_rows(page):
    """صفوف صفحة الوقت — سطور التكملة تُضمّ إلى الصف الذي قبلها."""
    buckets = defaultdict(list)
    for x, y, t in body_words(page):
        buckets[round(y / 5)].append((x, t))
    rows = []
    for k in sorted(buckets):
        text = " ".join(t for _, t in sorted(buckets[k], reverse=True))
        if DAY.search(text):
            rows.append(text)
        elif rows:
            rows[-1] += " " + text
    return rows


def course_rows(page):
    """صفوف صفحة المقرر — الرمز يُجمع من سطرين عبر الإحداثيات."""
    ws = body_words(page)
    rows = []
    for x, y, t in ws:
        m = PREFIX.match(t)
        if not m:
            continue
        need = 4 - len(m.group(2))                 # كم رقماً ينقص لإتمام الرمز
        tail = [tt for xx, yy, tt in ws
                if re.fullmatch(r"\d{%d}" % need, tt) and abs(xx - x) < 20 and 2 < yy - y < 16
                ] if need else []
        code = m.group(1) + m.group(2) + (tail[0] if tail else "")
        if not re.fullmatch(r"[A-Z]{4}\d{4}", code):
            continue
        line = [tt for _, tt in
                sorted([(xx, tt) for xx, yy, tt in ws if abs(yy - y) < 5], reverse=True)]
        section = ""
        for i, tok in enumerate(line):
            if re.fullmatch(r"\d\.\d", tok) and i + 1 < len(line):
                section = line[i + 1]
                break
        rows.append((code, section or "01"))
    return rows


def parse(path, term):
    doc = pymupdf.open(path)
    found, pairs, matched = [], 0, 0
    for i in range(0, len(doc) - 1, 2):
        times, courses = time_rows(doc[i]), course_rows(doc[i + 1])
        pairs += 1
        if len(times) != len(courses):
            continue
        matched += 1
        for text, (code, section) in zip(times, courses):
            stamps = TIME.findall(text)
            if len(stamps) < 2:
                continue
            a, b = (f"{h}:{m}" for h, m in stamps[:2])
            if a > b:
                a, b = b, a
            room = re.search(r"\b(\d{4}|[أ-ي]\s*\d{1,2}|\d{1,2}[أ-ي])\b", text)
            found.append({"term": term, "code": code, "section": section,
                          "day": DAY.search(text).group(1), "start": a, "end": b,
                          "room": room.group(1).replace(" ", "") if room else ""})
    return found, pairs, matched


def main():
    src = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else UPLOADS
    files = sorted(src.glob("*RPT_CourseSchedule*.pdf"))
    if not files:
        sys.exit(f"✘ لا ملفات جداول في {src}")

    files, dropped = dedupe(files)
    print(f"  ملفات فريدة: {len(files)} · نُسخ مكرَّرة مُسقَطة: {dropped}")

    rows, pairs, matched = [], 0, 0
    for f in files:
        term = season_of(f)
        got, p, m = parse(f, term)
        rows += got
        pairs += p
        matched += m
        print(f"  {f.name[:14]}… {term:6} · أزواج {m}/{p} · لقاءات {len(got)}")

    ratio = matched / pairs if pairs else 0
    print(f"\nالتغطية: {matched}/{pairs} زوج ({ratio:.0%}) · {len(rows)} لقاء")
    if ratio < 0.90:
        sys.exit(f"✘ التغطية {ratio:.0%} دون العتبة 90% — التحليل تدهور")

    data = defaultdict(lambda: defaultdict(list))
    for r in rows:
        key = f'{r["term"]}:{r["code"]}'
        slot = {"day": r["day"], "day_ar": DAY_AR[r["day"]],
                "start": r["start"], "end": r["end"], "room": r["room"]}
        if slot not in data[key][r["section"]]:
            data[key][r["section"]].append(slot)

    # ── فحوص ذاتية على سلامة التصنيف الموسمي ──
    # ① التطابق الحرفي بين موسمَي مقرر: وارد لمقرر يُطرح في الفصلين بنفس الشعبة
    #    والقاعة، لكن تكراره على نطاق واسع بصمةُ خطأ تصنيف (أصاب 160 مقرراً سابقاً).
    codes = {k.split(":", 1)[1] for k in data}
    identical = [c for c in sorted(codes)
                 if f"fall:{c}" in data and f"spring:{c}" in data
                 and json.dumps(data[f"fall:{c}"], sort_keys=True)
                 == json.dumps(data[f"spring:{c}"], sort_keys=True)]
    if len(identical) > IDENTICAL_MAX:
        sys.exit(f"✘ {len(identical)} مقرراً بياناتهما متطابقة بين الموسمين "
                 f"(الحد {IDENTICAL_MAX}) — مؤشر تكرار في التصنيف: "
                 + "، ".join(identical[:8]))
    print(f"  ✓ متطابقو الموسمين: {len(identical)} فقط من {len(codes)}"
          + (f" ({'، '.join(identical)})" if identical else ""))

    # ② الفحص الحاسم: مقرر تشهد ملفات الخطة أنه خريفي حصراً يجب ألّا تكون له
    #    شعب ربيعية — وهذه بالضبط هي الأعراض التي أحدثها الخطأ السابق.
    plan = ROOT / "docs" / "data" / "study-plan.json"
    if plan.exists():
        ev = json.loads(plan.read_text(encoding="utf-8"))["seasonality_evidence"]
        fall_only = set(ev.get("ared_offered_fall_2025", [])) | set(
            ev.get("cutm_offered_fall_2025", []))
        spring_only = set(ev.get("ared_offered_spring_2026", [])) | set(
            ev.get("cutm_offered_spring_2026", []))
        # التسرّب المَرَضي هو أن يظهر مقرر مقفل على موسم في الموسم الآخر
        # **بنفس البيانات حرفياً** — أي منسوخاً لا مطروحاً. أما ظهوره ببيانات
        # مختلفة فيعني أنه يُطرح في الفصلين فعلاً وأن قائمة الشهادة أقدم.
        def copied(c, a, b):
            return (f"{a}:{c}" in data and f"{b}:{c}" in data
                    and json.dumps(data[f"{a}:{c}"], sort_keys=True)
                    == json.dumps(data[f"{b}:{c}"], sort_keys=True))

        leaked = sorted(c for c in (fall_only - spring_only) if copied(c, "fall", "spring"))
        leaked += sorted(c for c in (spring_only - fall_only) if copied(c, "spring", "fall"))
        if leaked:
            sys.exit("✘ تسرّب موسمي: مقررات مقفلة على موسم ونُسخت حرفياً إلى الآخر → "
                     + "، ".join(leaked))
        print(f"  ✓ صفر تسرّب موسمي — {len(fall_only | spring_only)} مقرراً مقفلاً "
              "على موسمه، لا نسخة منها في الموسم المقابل")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(
        {"source": "جداول المقررات — خريف وربيع 2025/2026",
         "note": "مواعيد 2025/2026 — استرشادية لسنة 2026/2027 وتحتاج تثبيتاً عند فتح التسجيل",
         "coverage": {"pairs": pairs, "matched": matched},
         "meetings": {k: dict(v) for k, v in sorted(data.items())}},
        ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"✓ {OUT.relative_to(ROOT)} — {len(data)} مقرر")
    return 0


if __name__ == "__main__":
    sys.exit(main())
