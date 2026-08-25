#!/usr/bin/env python3
"""يحوّل كشف الدرجات الرسمي إلى docs/data/transcript.json.

هذا هو **مصدر الحقيقة** لحالة المقررات: لا تُكتب حالة أي مقرر يدوياً بعد اليوم،
بل تُشتق من هنا.

التحقق الذاتي: يقارن مجموع الساعات المكتسبة الذي يحسبه بسطر
`TOTAL CREDITS EARNED` المطبوع في الكشف نفسه، ويُخفق إن اختلفا.

الاستخدام:  python3 scripts/parse_transcript.py [مسار_الكشف.pdf]
"""

import json
import pathlib
import re
import sys

import pymupdf

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "data" / "transcript.json"
UPLOADS = pathlib.Path("/root/.claude/uploads/ebee8a34-1b44-59e4-8f54-d4abd6b2f247")
DEFAULT = UPLOADS / "ab2b3f48-RPT_STUD_TRANSCRIPT_Official.rdlc.pdf"

# سلّم التقديرات من مفتاح الكشف نفسه
POINTS = {"A": 4.00, "A-": 3.70, "B+": 3.30, "B": 3.00, "B-": 2.70, "C+": 2.30,
          "C": 2.00, "C-": 1.70, "D+": 1.30, "D": 1.00,
          "F": 0.00, "FW": 0.00, "NP": 0.00, "NPW": 0.00}
NON_GRADE = {"W", "TC", "IP", "OP", "REG", "P"}      # لا تدخل المعدل
PASSING = set(POINTS) - {"F", "FW", "NP", "NPW"}

TERM_AR = {"FALL": "خريف", "SPRING": "ربيع", "SUMMER": "صيف"}


def parse(path):
    doc = pymupdf.open(path)
    text = "\n".join(p.get_text() for p in doc)
    lines = [l.strip() for l in text.split("\n")]

    records, term, i = [], None, 0
    while i < len(lines):
        m = re.match(r"^SEMESTER\s+(\d{4})\s+(FALL|SPRING|SUMMER)$", lines[i])
        if m:
            term = {"year": int(m.group(1)), "season": m.group(2),
                    "ar": f"{TERM_AR[m.group(2)]} {m.group(1)}"}
        if re.fullmatch(r"[A-Z]{4}\d{4}", lines[i]) and i + 3 < len(lines):
            code, title, cr, grade = lines[i], lines[i + 1], lines[i + 2], lines[i + 3]
            if re.fullmatch(r"\d+", cr) and (grade in POINTS or grade in NON_GRADE):
                records.append({"term": term["ar"] if term else "?",
                                "year": term["year"] if term else 0,
                                "season": term["season"] if term else "?",
                                "code": code, "title": title,
                                "credits": int(cr), "grade": grade,
                                "passed": grade in PASSING and int(cr) > 0,
                                "university_elective": bool(
                                    re.search(r"\(U\.?E\.?\)", title))})
                i += 4
                continue
        i += 1

    # سطور المجاميع المطبوعة في الكشف — تُستعمل للتحقق الذاتي
    stated = {}
    for key, pat in [("earned", r"TOTAL CREDITS EARNED\s+([\d.]+)"),
                     ("attempted", r"TOTAL CREDITS ATTEMPTED\s+([\d.]+)"),
                     ("points", r"TOTAL GRADE POINTS\s+([\d.]+)")]:
        m = re.search(pat, text)
        if m:
            stated[key] = float(m.group(1))
    m = re.search(r"CUM\.GPA\s+([\d.]+)(?!.*CUM\.GPA)", text, re.S)
    if m:
        stated["cgpa"] = float(m.group(1))

    student = {}
    for key, pat in [("id", r"STUDENT NO\s*\n?:\s*(\S+)"),
                     ("name", r"NAME\s*\n?:\s*(.+)"),
                     ("major", r"MAJOR\s*\n?:\s*(.+)"),
                     ("advisor", r"ADVISOR\(S\)\s*\n?:\s*(.+)")]:
        m = re.search(pat, text)
        if m:
            student[key] = m.group(1).strip()
    return records, stated, student


def main():
    src = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT
    if not src.exists():
        sys.exit(f"✘ كشف الدرجات غير موجود: {src}")
    records, stated, student = parse(src)

    passed = [r for r in records if r["passed"]]
    earned = sum(r["credits"] for r in passed)
    graded = [r for r in records if r["grade"] in POINTS and r["credits"] > 0]
    attempted = sum(r["credits"] for r in graded)
    points = sum(POINTS[r["grade"]] * r["credits"] for r in graded)

    terms = sorted({(r["year"], r["season"]) for r in records if r["year"]},
                   key=lambda t: (t[0], 0 if t[1] == "SPRING" else 1))
    # الفصول تُرتَّب زمنياً: خريف السنة يسبق ربيع السنة التالية
    terms = sorted({(r["year"], r["season"]) for r in records if r["year"]},
                   key=lambda t: t[0] * 2 + (1 if t[1] == "FALL" else 0))

    print(f"سجلات: {len(records)} · ناجحة: {len(passed)} · فصول مسجَّلة: {len(terms)}")
    print(f"مكتسب محسوب: {earned}  |  الكشف يقول: {stated.get('earned')}")
    print(f"محاوَل محسوب: {attempted}  |  الكشف يقول: {stated.get('attempted')}")
    print(f"نقاط محسوبة: {points:.2f}  |  الكشف يقول: {stated.get('points')}")

    fail = []
    if stated.get("earned") is not None and earned != stated["earned"]:
        fail.append(f"المكتسب {earned} ≠ {stated['earned']}")
    if stated.get("attempted") is not None and attempted != stated["attempted"]:
        fail.append(f"المحاوَل {attempted} ≠ {stated['attempted']}")
    if stated.get("points") is not None and abs(points - stated["points"]) > 0.01:
        fail.append(f"النقاط {points} ≠ {stated['points']}")
    if fail:
        sys.exit("✘ التحقق الذاتي أخفق: " + " · ".join(fail))
    print("✓ التحقق الذاتي: المحسوب يطابق المطبوع في الكشف")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "source": "كشف الدرجات الرسمي — عمادة القبول والتسجيل، 25 أغسطس 2026",
        "student": student,
        "totals": {"earned": earned, "attempted": attempted,
                   "points": round(points, 2),
                   "cgpa": round(points / attempted, 2) if attempted else None,
                   "terms_registered": len(terms),
                   "next_term_index": len(terms) + 1},
        "withdrawals": [r["code"] for r in records if r["grade"] == "W"],
        "failures": [r["code"] for r in records
                     if r["grade"] in ("F", "FW", "NP", "NPW")],
        "records": records,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"✓ {OUT.relative_to(ROOT)} — معدل تراكمي {points / attempted:.2f} · "
          f"الفصل القادم رقم {len(terms) + 1}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
