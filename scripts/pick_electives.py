#!/usr/bin/env python3
"""يختار مقرر كل خانة اختياري تخصص بما يجعل جدول الفصل خالياً من التعارض.

خطة القسم تنصّ «يختار الطالب أحد المقررات التالية» — فالاختياري **خانة** لا مقرراً
بعينه، وبدائل الخانة الواحدة تختلف أياماً وأوقاتاً. هذا السكربت يجرّب كل التركيبات
لكل سيناريو ويثبّت التركيبة التي تُنتج فصولاً بلا تداخل زمني، مفضّلاً الأخفّ ازدحاماً.

الاستخدام:  python3 scripts/pick_electives.py
"""

import importlib.util
import itertools
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
PLAN = ROOT / "docs" / "data" / "study-plan.json"

SLOTS = {
    "ELEC_B": {"label": "اختياري تخصص (ب)",
               "options": ["ARED3250", "ARED3240", "ARED3150"]},
    "ELEC_C": {"label": "اختياري تخصص (ج)",
               "options": ["ARED3170", "ARED3160"]},
    "ELEC_D": {"label": "اختياري تخصص (د)",
               "options": ["ARED4140", "ARED4130", "ARED4150"]},
}


def load_builder():
    spec = importlib.util.spec_from_file_location("bp", ROOT / "scripts" / "build_pdf.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    bp = load_builder()
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    meetings = bp.load_meetings()
    C = plan["courses"]

    # الخانة تُعرَف بعضوية المقرر في قائمة بدائلها، لا بحالته
    slot_of = {opt: slot for slot, v in SLOTS.items() for opt in v["options"]}
    scens = [k for k, v in plan["scenarios"].items() if not v.get("expect_fail")]

    # مواضع الخانات في كل سيناريو
    where = {}
    for key in scens:
        for ti, term in enumerate(plan["scenarios"][key]["terms"]):
            for pi, code in enumerate(term["courses"]):
                slot = slot_of.get(code)
                if slot and C[code]["status"] != "completed":
                    where.setdefault(key, {})[slot] = (ti, pi)

    slots = sorted({s for m in where.values() for s in m})
    if not slots:
        print("  لا خانات اختياري متبقية")
        return 0

    # اختيار **عالمي واحد** يصلح للسيناريوهات كلها — لا يتفرّع بينها
    best, best_cost = None, None
    for combo in itertools.product(*[SLOTS[s]["options"] for s in slots]):
        pick = dict(zip(slots, combo))
        ok, cost = True, 0
        for key in scens:
            scen = plan["scenarios"][key]
            trial = [list(t["courses"]) for t in scen["terms"]]
            for slot, (ti, pi) in where.get(key, {}).items():
                trial[ti][pi] = pick[slot]
            for term, courses in zip(scen["terms"], trial):
                if not courses:
                    continue
                res = bp.solve_term(meetings, term["season"], courses)
                if not res["ok"]:
                    ok = False
                    break
                cost += len(res["forced"])
            if not ok:
                break
        if ok and (best_cost is None or cost < best_cost):
            best, best_cost = pick, cost

    if best is None:
        print("  ✘ لا تركيبة اختياريات تُنتج فصولاً بلا تعارض في كل السيناريوهات")
        return 1

    for slot, chosen in best.items():
        for opt in SLOTS[slot]["options"]:
            if C[opt]["status"] != "completed":
                C[opt]["status"] = "remaining" if opt == chosen else "alternative"
        print(f"  ✓ {SLOTS[slot]['label']}: {C[chosen]['ar']} {C[chosen]['name'].split('—')[0].strip()}")
    for key in scens:
        for slot, (ti, pi) in where.get(key, {}).items():
            plan["scenarios"][key]["terms"][ti]["courses"][pi] = best[slot]
    print(f"  اختيار عالمي واحد يصلح للسيناريوهات الأربعة · مقررات مقفلة إجمالاً: {best_cost}")

    # الخانات وبدائلها تُحفظ لعرضها في الوثيقة
    plan["elective_slots"] = {
        s: {"label": v["label"], "options": v["options"],
            "credits": C[v["options"][0]]["cr"]} for s, v in SLOTS.items()}
    plan["elective_slots"]["ELEC_A"] = {
        "label": "اختياري تخصص (أ)", "credits": 3, "satisfied_by": "ARED3140",
        "options": ["ARED3230", "ARED3130", "ARED3140"]}

    PLAN.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("✓ تُثبّتت اختيارات الخانات في الخطة")
    return 0


if __name__ == "__main__":
    sys.exit(main())
