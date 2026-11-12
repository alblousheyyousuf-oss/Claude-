# المصدر

- **المستودع:** https://github.com/asadeisa/arabic-office-skills/tree/main/arabic-docx
- **النسخة:** commit `e39889978ee084d8aaff80aa1265766eb1ce0d51` (نُزّلت 2026-11-12)
- **الترخيص:** MIT. انظر `LICENSE`.
- **التعديل:** لا تعديل على `SKILL.md` ولا على `scripts/arabic_docx.py`. أُخذ مجلد `arabic-docx` وحده، وتُرك `arabic-pdf` و`arabic-pptx` والاختبارات.
- **الفحص:** قُرئ `arabic_docx.py` (1420 سطراً). لا اتصالات شبكة، ولا `eval` أو `exec`، ولا قراءة مفاتيح. يستعمل `subprocess` في موضعين فقط، كلاهما لتحويل الملف محلياً إلى PDF للمعاينة: LibreOffice (`soffice --headless`)، أو Word عبر PowerShell في Windows. ولا يستعملهما إلا إذا استُدعيت `preview()` أو `docx_to_pdf()` أو `refresh_fields()`.
- **من يستعمله:** `report-docx/scripts/build_report.py` يستورد `ArabicDocx` منه للتقارير العربية، ويبني عليه `LatinDocx` للتقارير الإنجليزية. فإن حُدّثت هذه المهارة من مصدرها، فأعد اختبار `build_report.py`.
