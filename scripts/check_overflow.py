#!/usr/bin/env python3
"""يتحقق أن لا محتوى يتجاوز حدود الصفحة أو يدخل منطقة التذييل.

Chromium لا يُبلِّغ عن تجاوز المحتوى — يقصّه بصمت. هذا الفاحص يقرأ الـPDF
الناتج ويقيس حدود كل كتلة نصية فعلياً.
"""
import sys, pathlib
import pymupdf

FOOT_TOP = 808.0     # نقطة بدء منطقة التذييل (A4 = 842pt)
MARGIN = 2.0


def check(path, foot_top=FOOT_TOP):
    doc = pymupdf.open(path)
    bad = []
    for i, page in enumerate(doc, 1):
        h, w = page.rect.height, page.rect.width
        for b in page.get_text("blocks"):
            x0, y0, x1, y1, text = b[0], b[1], b[2], b[3], b[4]
            if not text.strip():
                continue
            if y1 > h - MARGIN or y0 < MARGIN or x1 > w - MARGIN or x0 < MARGIN:
                bad.append((i, "خارج الصفحة", text.strip()[:60]))
            elif y0 < foot_top < y1:
                bad.append((i, "يعبر خط التذييل", text.strip()[:60]))
    return doc.page_count, bad


def main():
    path = pathlib.Path(sys.argv[1] if len(sys.argv) > 1
                        else "docs/خارطة-طريق-التخرج.pdf")
    foot = float(sys.argv[2]) if len(sys.argv) > 2 else FOOT_TOP
    n, bad = check(path, foot)
    if bad:
        for pg, why, txt in bad:
            print(f"  ✘ صفحة {pg}: {why} — {txt}")
        print(f"✘ {path.name}: {len(bad)} تجاوزاً في {n} صفحة")
        return 1
    print(f"✓ فحص التجاوز: {n} صفحة — سليمة ✔  ({path.name})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
