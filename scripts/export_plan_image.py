#!/usr/bin/env python3
"""يصدّر صفحة خطة واحدة من وثيقة الخطط إلى صورة PNG.

واتساب يعرض الصورة داخل المحادثة بلا نقر، بينما الملف يحتاج فتحاً — فمن
أراد ردّاً سريعاً أرسل ما يُرى فوراً.

    python3 scripts/export_plan_image.py [رمز الخطة] [الدقة]
    python3 scripts/export_plan_image.py B 200
"""
import pathlib
import sys

import pymupdf

ROOT = pathlib.Path(__file__).resolve().parent.parent
PDF = ROOT / "docs" / "الخطط-الدراسية-جداول-الفصول.pdf"
AR = {"A": "أ", "B": "ب", "C": "ج", "D": "د"}


def main():
    key = (sys.argv[1] if len(sys.argv) > 1 else "B").upper()
    dpi = int(sys.argv[2]) if len(sys.argv) > 2 else 200
    if key not in AR:
        sys.exit(f"✘ رمز غير معروف: {key} — المتاح {'، '.join(AR)}")
    if not PDF.exists():
        sys.exit(f"✘ الملف غير موجود: {PDF} — شغّل build_plans_pdf.py أولاً")

    # ترتيب الصفحات هو ترتيب ORDER في build_plans_pdf، فيُقرأ منه لا يُفترض
    sys.path.insert(0, str(pathlib.Path(__file__).parent))
    from build_plans_pdf import ORDER
    page = ORDER.index(key)

    doc = pymupdf.open(PDF)
    out = ROOT / "docs" / f"الخطة-{AR[key]}.png"
    pix = doc[page].get_pixmap(dpi=dpi)
    pix.save(out)
    print(f"✓ {out.name} — الخطة {AR[key]} (صفحة {page + 1}) · "
          f"{pix.width}×{pix.height} بكسل · {out.stat().st_size // 1024} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
