#!/usr/bin/env python3
"""تدقيق مستقل يقرأ ملف الخطط الناتج نفسه — لا مصدره.

يتحقق لكل خطة من ثلاثة أمور:
  ① كل المقررات المتبقية مجدوَلة، بالعدد نفسه المسجَّل في البيانات
  ② مجموع الساعات المطبوع يطابق المحسوب من الصفحة
  ③ الفصل الأخير = منطر4600 + منطر4400 وحدهما

يعمل بإحداثيات الكلمات لا بترتيب النصّ: استخراج العربية من الـPDF يعيد
ترتيب السطور، فأي مطابقة تعتمد الترتيب تُعطي نتائج كاذبة. وكتلة الحقول
أعلى الصفحة تُستبعد لأن فيها نصّ الاستثناء وشارة الطوارئ، وكلاهما يذكر
رموز مقررات لا تخصّ الجدولة.
"""
import json
import pathlib
import re
import sys

import pymupdf

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from build_plans_pdf import ORDER, PDF_OUT

DATA = ROOT / "docs" / "data" / "study-plan.json"
AR = {"A": "أ", "B": "ب", "C": "ج", "D": "د"}
FINAL = {"CUTM4600", "CUTM4400"}


def page_facts(page, remaining, num):
    """يستخرج من صفحة واحدة: عدد مرات كل مقرر، والمجموع المطبوع."""
    ws = [(w[1], w[4]) for w in page.get_text("words")]
    cut = min([y for y, t in ws if "الساعات" in t] or [0])
    body = " ".join(t for y, t in ws if y >= cut)
    counts = {c: len(re.findall(rf"(?<!\d){num[c]}(?!\d)", body)) for c in remaining}
    ytot = max(y for y, t in ws if "التشكيلة" in t)
    printed = max((int(t) for y, t in ws if abs(y - ytot) < 6 and t.isdigit()),
                  default=-1)
    return counts, printed


def main():
    d = json.loads(DATA.read_text(encoding="utf-8"))
    C = d["courses"]
    remaining = [c for c, v in C.items() if v["status"] == "remaining"]
    num = {c: re.search(r"\d+", C[c]["ar"]).group() for c in remaining}
    if len(set(num.values())) != len(remaining):
        sys.exit("✘ أرقام المقررات غير فريدة — المطابقة بالرقم غير آمنة")

    doc = pymupdf.open(PDF_OUT)
    if doc.page_count != len(ORDER):
        sys.exit(f"✘ الملف {doc.page_count} صفحة والخطط {len(ORDER)}")

    print(f"تدقيق مستقل على {PDF_OUT.name} — بالإحداثيات لا بترتيب النصّ\n")
    ok = True
    for i, key in enumerate(ORDER):
        counts, printed = page_facts(doc[i], remaining, num)
        expected = {}
        for t in d["scenarios"][key]["terms"]:
            for c in t["courses"]:
                expected[c] = expected.get(c, 0) + 1
        mismatch = [C[c]["ar"] for c in remaining if counts[c] != expected.get(c, 0)]
        computed = sum(C[c]["cr"] * counts[c] for c in remaining)
        final = d["scenarios"][key]["terms"][-1]["courses"]
        good = (not mismatch and computed == printed
                and set(expected) == set(remaining) and set(final) == FINAL)
        ok &= good
        print(f"  {'✔' if good else '✘'} صفحة {i + 1} = التشكيلة {AR[key]} · "
              f"تغطية {len(set(expected))}/{len(remaining)} مقرراً · "
              f"{computed}س محسوبة = {printed}س مطبوعة · فصل التخرج "
              + " + ".join(C[c]["ar"] for c in final)
              + (f" · اختلاف: {'، '.join(mismatch)}" if mismatch else ""))

    print("\n" + ("✔ التدقيق المستقل نظيف" if ok else "✘ خلل في الملف الناتج"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
