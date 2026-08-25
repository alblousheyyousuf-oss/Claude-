#!/usr/bin/env python3
"""يعيد بناء docs/data/study-plan.json من كشف الدرجات، لا من فرضية.

حالة كل مقرر تُشتق من docs/data/transcript.json. ثم تُبنى السيناريوهات الأربعة
على المتبقي الفعلي، ملتزمةً قاعدة عزل التدريب الميداني.

الاستخدام:  python3 scripts/rebuild_plan.py
"""

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
PLAN = ROOT / "docs" / "data" / "study-plan.json"
TRANSCRIPT = ROOT / "docs" / "data" / "transcript.json"

# مقررات الكشف التي تحمل رموزاً مختلفة عن مفاتيح الخطة
ALIAS = {"HIST1010": "ISLM1010"}
# اختياري الجامعة الثلاثة كما وردت في الكشف
UE_SLOTS = ["UNIVELEC1", "UNIVELEC2", "UNIVELEC3"]


def main():
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    tr = json.loads(TRANSCRIPT.read_text(encoding="utf-8"))
    C = plan["courses"]

    passed = {}
    for r in tr["records"]:
        if r["passed"]:
            passed[ALIAS.get(r["code"], r["code"])] = r

    # ── 1 · حالة كل مقرر من الكشف ──
    for code, info in C.items():
        info.pop("grade", None); info.pop("earned_term", None)
        if code in passed:
            r = passed[code]
            info["status"] = "completed"
            info["grade"] = r["grade"]
            info["earned_term"] = r["term"]
        elif code in UE_SLOTS:
            pass                                   # يُملأ أدناه
        else:
            info["status"] = "remaining"

    # اختياري الجامعة: تُسند الشواغر إلى ما ورد في الكشف
    ue = [r for r in tr["records"] if r["passed"] and r["university_elective"]]
    for slot, r in zip(UE_SLOTS, ue):
        C[slot].update({"status": "completed", "ar": r["code"], "name": r["title"],
                        "cr": r["credits"], "grade": r["grade"], "earned_term": r["term"]})

    # اختياري التخصص (أ): استُوفي بـ ترفن3140
    if "ARED3140" in passed:
        C["ARED3140"]["elective_slot"] = "ز1 — اختياري تخصص (أ)"

    # ── 2 · التحقق: المحسوب = الكشف ──
    earned = sum(v["cr"] for v in C.values() if v["status"] == "completed")
    if earned != tr["totals"]["earned"]:
        sys.exit(f"✘ المنجَز المحسوب {earned} ≠ كشف الدرجات {tr['totals']['earned']}")
    remaining = sum(v["cr"] for v in C.values() if v["status"] == "remaining")
    if earned + remaining != plan["meta"]["total_credits"]:
        sys.exit(f"✘ {earned} + {remaining} ≠ {plan['meta']['total_credits']}")
    print(f"✓ منجَز {earned} · متبقٍ {remaining} · المجموع {earned + remaining}")

    # ── 3 · بيانات الطالب من الكشف ──
    plan["meta"].update({
        "cgpa": tr["totals"]["cgpa"],
        "cgpa_band": "2.00-2.99",
        "credits_earned": earned,
        "credits_remaining": remaining,
        "start_term_index": tr["totals"]["next_term_index"],
        "start_term_index_note": (
            f"مشتق من كشف الدرجات: {tr['totals']['terms_registered']} فصلاً مسجَّلاً "
            f"⇒ خريف 2026 هو الفصل رقم {tr['totals']['next_term_index']}"),
        "source_of_truth": "كشف الدرجات الرسمي — 25 أغسطس 2026",
        "withdrawals_used": len(tr["withdrawals"]),
        "withdrawals_allowed": 4,
        "failures": tr["failures"],
    })
    plan["meta"].pop("recommendation_rationale", None)

    # ── 4 · قاعدة عزل التدريب الميداني ──
    plan["regulations"]["field_training_isolation"] = {
        "source": "قرار حديث أفاد به الطالب — أحدث من وثيقة الخطة",
        "rule": ("يُسجَّل التدريب الميداني وحده، ولا يُسمح معه بأي مقرر آخر "
                 "إلا متطلب جامعة واحد اختيارياً"),
        "max_companions": 1,
        "companion_category": "م ج",
        "conflict_note": (
            "وثيقة الخطة تنصّ أن مشروع التخرج «يتم دراسته كمقرر مصاحب مع التدريب الميداني»، "
            "والقرار الجديد يمنع المصاحبة. الجدولة تضع المشروع في الفصل السابق لأنه يُرضي "
            "القراءتين. إن أصرّ القسم على المصاحبة الإلزامية فيعود المشروع لفصل التخرج "
            "ويسقط متطلب الجامعة منه."),
    }
    print("✓ أُضيفت قاعدة عزل التدريب الميداني")
    PLAN.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
