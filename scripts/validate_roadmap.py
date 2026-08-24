#!/usr/bin/env python3
"""مدقّق خارطة طريق التخرج — قسم التربية الفنية، جامعة السلطان قابوس.

يقرأ docs/data/study-plan.json ويفحص كل سيناريو آلياً مقابل:
  1. التغطية    — كل مقرر متبقٍ مُجدوَل مرة واحدة، والمجموع التراكمي = 125 ساعة.
  2. المتطلبات  — كل متطلب سابق منجَز في فصل *سابق* (لا متزامن).
  3. الموسمية   — كل مقرر مُجدوَل في موسم يُطرح فيه.
  4. العبء      — 9 ≤ الساعات ≤ 18 (الفصل الأخير معفى من الحد الأدنى)، وعدد المقررات ≤ 6.
  5. بوابة 4600 — كل مقررات الخطة منجزة قبل التدريب الميداني عدا مشروع التخرج.
  6. التقدّم    — جدول الحد الأدنى للساعات التراكمية (البند د-6).
  7. المدة      — عدد الفصول ضمن الحد الأقصى (14 فصلاً).

الاستخدام:  python3 scripts/validate_roadmap.py [--json مسار]
الخروج: 0 إذا مرّت كل السيناريوهات المتوقَّع نجاحها وفشل السيناريو السلبي كما هو متوقَّع.
"""

import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DEFAULT_JSON = ROOT / "docs" / "data" / "study-plan.json"


def load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def season_ok(course_season, term_season):
    return course_season in ("both", "?") or course_season == term_season


def validate(name, scen, data):
    """يعيد (قائمة المخالفات، قائمة الملاحظات) لسيناريو واحد."""
    courses = data["courses"]
    reg = data["regulations"]
    rt = reg["regular_term"]
    progress = reg["min_progress_table"]["rows"]
    max_terms = reg["max_duration"]["max_terms"]

    violations, notes = [], []

    done = {c for c, v in courses.items() if v["status"] == "completed"}
    earned = sum(courses[c]["cr"] for c in done)
    remaining = {c for c, v in courses.items() if v["status"] == "remaining"}

    scheduled = []
    for term in scen["terms"]:
        scheduled.extend(term["courses"])

    # --- 1. التغطية ---
    missing = remaining - set(scheduled)
    if missing:
        violations.append(
            "تغطية: مقررات متبقية غير مُجدوَلة → " + "، ".join(sorted(missing))
        )
    dupes = {c for c in scheduled if scheduled.count(c) > 1}
    allowed_repeats = {c for t in scen["terms"] for c in t.get("failed", [])}
    for c in sorted(dupes - allowed_repeats):
        violations.append(f"تغطية: {c} مُجدوَل أكثر من مرة بلا رسوب معلن")

    # --- المرور على الفصول ---
    for term in scen["terms"]:
        label = term["name"]
        tcourses = term["courses"]
        credits = sum(courses[c]["cr"] for c in tcourses)
        failed = set(term.get("failed", []))

        # --- 4. العبء ---
        if tcourses:
            if credits > rt["max_credits"]:
                violations.append(
                    f"{label}: العبء {credits} ساعة يتجاوز السقف {rt['max_credits']}"
                )
            if credits < rt["min_credits"] and not term.get("final"):
                if term.get("under_min_ack"):
                    notes.append(
                        f"{label}: العبء {credits} ساعة دون الحد الأدنى {rt['min_credits']} — "
                        f"{term['under_min_ack']}؛ يستلزم استثناءً أو تأجيلاً معتمداً"
                    )
                else:
                    violations.append(
                        f"{label}: العبء {credits} ساعة دون الحد الأدنى {rt['min_credits']}"
                        " (وليس الفصل الأخير)"
                    )
            if len(tcourses) > rt["max_courses"]:
                if term.get("exception"):
                    notes.append(
                        f"{label}: {len(tcourses)} مقررات ({credits} ساعة) — يتجاوز سقف "
                        f"{rt['max_courses']} مقررات باستثناء معلن {term['exception']}"
                    )
                else:
                    violations.append(
                        f"{label}: {len(tcourses)} مقررات تتجاوز سقف {rt['max_courses']} بلا استثناء معلن"
                    )
        else:
            notes.append(f"{label}: فصل بلا تسجيل — {term.get('note', '')}".rstrip())

        for c in tcourses:
            info = courses[c]

            # --- 3. الموسمية ---
            if not season_ok(info["season"], term["season"]):
                if c in term.get("waive_season", []):
                    notes.append(
                        f"{label}: {info['ar']} {info['name']} — موسمه ({info['season']}) "
                        f"ويُطلب طرحه هنا باستثناء معلن {term.get('exception', 'E1')}"
                    )
                else:
                    violations.append(
                        f"{label}: {info['ar']} {info['name']} يُطرح "
                        f"({info['season']}) ولا يُطرح في هذا الفصل ({term['season']})"
                    )

            # --- 2. المتطلبات السابقة ---
            waived = {tuple(w) for w in term.get("waive_prereq", [])}
            for p in info.get("prereq", []):
                if p in done:
                    continue
                where = "متزامن في نفس الفصل" if p in tcourses else "غير منجَز"
                if (c, p) in waived:
                    notes.append(
                        f"{label}: {info['ar']} {info['name']} — المتطلب السابق "
                        f"{courses[p]['ar']} {where}، مرفوع باستثناء معلن "
                        f"{term.get('waive_prereq_exception', '?')}"
                        + (" (المتطلب متنازع عليه أصلاً بين صفحتي الخطة)"
                           if info.get("prereq_disputed") else "")
                    )
                else:
                    violations.append(
                        f"{label}: {info['ar']} {info['name']} — المتطلب السابق "
                        f"{courses[p]['ar']} {where}"
                    )

            # --- 5. بوابة التدريب الميداني ---
            if info.get("gate") == "all_except_CUTM4400":
                outstanding = (remaining - done - set(tcourses)) - {"CUTM4400"}
                if outstanding:
                    violations.append(
                        f"{label}: بوابة التدريب الميداني — مقررات لم تُنجَز بعد → "
                        + "، ".join(sorted(outstanding))
                    )
                blocking = [c for c in tcourses if c not in ("CUTM4600", "CUTM4400")]
                if blocking:
                    violations.append(
                        f"{label}: بوابة التدريب الميداني — مقررات مُجدوَلة معه → "
                        + "، ".join(sorted(blocking))
                    )

        passed = [c for c in tcourses if c not in failed]
        done |= set(passed)
        earned += sum(courses[c]["cr"] for c in passed)

        # --- 6. جدول الحد الأدنى للتقدّم (د-6) ---
        idx = str(term["index"])
        if idx in progress and tcourses:
            need, fail_at = progress[idx]
            if need > data["meta"]["total_credits"]:
                # الجدول جامعي عام: صفوفه الأخيرة تطلب ساعات تفوق مجموع هذه الدرجة (125)،
                # فلا يمكن تطبيقها حرفياً هنا. تُتجاوز بدل إطلاق إنذار كاذب.
                pass
            elif earned <= fail_at:
                notes.append(
                    f"تحذير د-6 — {label} (الفصل {idx}): التراكمي {earned} ساعة ≤ {fail_at}؛ "
                    f"الجدول يطلب {need} ساعة. يجب تثبيت رقم الفصل وطريقة تطبيق الجدول "
                    f"مع عمادة القبول والتسجيل قبل اعتماد هذا السيناريو"
                )

    # --- 1ب. المجموع النهائي ---
    if earned != data["meta"]["total_credits"] and not scen.get("expect_fail"):
        violations.append(
            f"المجموع النهائي {earned} ساعة ≠ {data['meta']['total_credits']} ساعة"
        )

    # --- 7. المدة ---
    last = max(t["index"] for t in scen["terms"])
    if last > max_terms:
        violations.append(f"المدة: ينتهي في الفصل {last} ويتجاوز الحد الأقصى {max_terms}")
    elif last == max_terms:
        notes.append(f"المدة: ينتهي في الفصل {last} — آخر فصل مسموح، بلا أي هامش")

    return violations, notes, earned


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=str(DEFAULT_JSON))
    args = ap.parse_args()
    data = load(args.json)

    print("مدقّق خارطة طريق التخرج — التربية الفنية / جامعة السلطان قابوس")
    print("=" * 78)
    meta = data["meta"]
    print(f"الطالب: {meta['student']} ({meta['student_id']})   الدفعة: {meta['cohort']}")
    print(f"نقطة الانطلاق: {meta['start_term']} — الفصل رقم {meta['start_term_index']}")
    print("=" * 78)

    exit_code = 0
    for name, scen in data["scenarios"].items():
        violations, notes, earned = validate(name, scen, data)
        expect_fail = scen.get("expect_fail", False)
        ok = not violations

        if expect_fail:
            status = "فشل كما هو متوقَّع ✔" if violations else "مرّ رغم أنه كان يُفترض أن يفشل ✘"
            if not violations:
                exit_code = 1
        else:
            status = "مطابق ✔" if ok else "مخالف ✘"
            if violations:
                exit_code = 1

        print(f"\n[{name}] {scen['title']}")
        print(f"    الحالة: {status}")
        print(f"    التخرج: {scen['graduation']}")
        print(f"    الاستثناءات المطلوبة: {'، '.join(scen['requires_exceptions']) or 'لا شيء'}")
        loads = "  ".join(
            f"{t['name'].split()[1]}={sum(data['courses'][c]['cr'] for c in t['courses'])}"
            for t in scen["terms"]
        )
        print(f"    الأحمال: {loads}   (المجموع التراكمي {earned})")
        for v in violations:
            print(f"    ✘ {v}")
        for n in notes:
            print(f"    ⚠ {n}")

    print("\n" + "=" * 78)
    print("النتيجة: كل السيناريوهات سلكت المسار المتوقَّع ✔" if exit_code == 0
          else "النتيجة: توجد مخالفات ✘")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
