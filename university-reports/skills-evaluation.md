# تقييم المهارات الجاهزة لإعداد التقارير الجامعية

> **التاريخ:** 2026-11-12
> **السؤال:** هل توجد في GitHub مهارات (Skills) جاهزة تساعد في إعداد تقارير جامعية احترافية، بالعربية والإنجليزية؟
> **النطاق:** 23 مستودعاً استُنسخت، فيها 1,851 ملف `SKILL.md`. منها 642 فيها كلمة أكاديمية في الوصف، ثم قائمة قصيرة من 25 مهارة: 12 قُرئت من الداخل، والباقي حُكم عليه من وصفه وبنيته.

---

## الخلاصة في ثلاثة أسطر

1. **لا توجد مهارة تغطي التقرير الجامعي من التكليف إلى ملف Word**، وخاصة بالعربية. الموجود مهارات لأوراق المجلات العلمية (IMRAD، وCONSORT، وLaTeX)، أو لرسائل الجامعات الصينية، أو أدوات متفرقة.
2. **مهارة واحدة تستحق التثبيت كما هي:** `arabic-docx`، لملفات Word العربية. هي أدق ما وجدت في اتجاه النص والخطوط والجداول العربية.
3. **ثماني مهارات فيها أفكار أخذناها**، وكتبناها بلغتنا داخل خمس مهارات جديدة. والباقي مرفوض لأسباب موثقة أدناه.

---

## كيف تحققت

| الخطوة | ما فعلته |
|---|---|
| **البحث** | 7 عمليات بحث على الويب في أسواق المهارات (skills.sh، وclaudemarket، وtessl، وopenskillindex، وskillsdirectory)، وفي قائمة [awesome-academic-skills](https://github.com/O0000-code/awesome-academic-skills) |
| **التنزيل** | استنساخ 23 مستودعاً إلى مجلد معزول، وتتبّع كل مهارة إلى **مستودعها الأصلي**. فشل استنساخ ثلاثة: endigo/claude-skills، وa-green-hand-jack/ml-research-skills، وiamwrm/typst_skill |
| **الفرز** | سكربت يقرأ اسم كل مهارة ووصفها ويبحث فيهما بكلمات: academic، وthesis، وreport، وcitation، وAPA، وIEEE، وdocx، وArabic، وRTL… |
| **القراءة** | 12 مهارة قُرئت من الداخل (كاملةً أو أقسامها الرئيسية)، وهي كل ما ثُبّت أو أُخذت منه فكرة. والمعلَّمة بـ ° في جدول الرفض حُكم عليها من وصفها وبنيتها وترخيصها |
| **الفحص الأمني** | البحث عن اتصالات شبكة، و`subprocess`، و`eval`/`exec`، وطلب مفاتيح. وقُرئ سكربت المهارة المثبّتة كاملاً |
| **الثقة** | ملف الترخيص الفعلي في المستودع (لا ما يقوله السوق)، وتاريخ آخر تحديث، والنجوم |

### المعايير

| المعيار | السؤال |
|---|---|
| **الصلة** (الأهم) | هل تخدم *تقريراً جامعياً لطالب*، أم ورقة لمجلة محكّمة، أم شيئاً آخر؟ |
| **العربية** | هل تتعامل مع التقارير العربية واتجاهها ومراجعها؟ |
| **الجودة** | هل المحتوى دقيق، أم فيه أرقام أو قواعد مخترعة؟ |
| **الأمان والترخيص** | هل يحق لنا تثبيتها في مستودع عام؟ وهل سكربتاتها آمنة؟ |
| **الاستقلالية** | هل تعمل وحدها، أم تحتاج إطاراً كاملاً أو خدمات مدفوعة؟ |

---

## ✅ تُثبَّت كما هي (1)

### `arabic-docx` — من [asadeisa/arabic-office-skills](https://github.com/asadeisa/arabic-office-skills)

| | |
|---|---|
| **الصلة** | ⭐⭐⭐⭐⭐ ملفات Word العربية، والتقارير منها صراحة: فهرس، وتسميات مرقمة، وترقيم صفحات |
| **الجودة** | ⭐⭐⭐⭐⭐ يشرح *لماذا* ينكسر النص العربي في Word، ويعالج كل علّة على حدة: اتجاه الفقرات، والجداول، وخانة الخط العربي، وتقسيم النص المختلط، والأقواس |
| **الأمان** | سكربت Python واحد بلا اتصالات شبكة. `subprocess` فقط لتحويل الملف محلياً إلى PDF عبر LibreOffice أو Word |
| **الترخيص** | MIT |
| **الثقة** | 5 نجوم فقط، لكن فيه اختبارات آلية (CI)، وآخر تحديث 2026-10-23. الجودة تُقاس هنا بالمحتوى لا بالشهرة |

**لماذا هي أساس `report-docx`:** بناء ملف Word عربي صحيح يحتاج نحو عشرة إعدادات في XML، كل منها يفشل بصمت وحده. إعادة كتابتها مخاطرة بلا فائدة، فبنينا عليها ولم نكررها.

---

## 🔧 نأخذ منها أفكاراً ولا نثبّتها (8)

| المهارة | المصدر · الترخيص | الفكرة التي أخذناها | أين | سبب عدم التثبيت |
|---|---|---|---|---|
| **scientific-writing** | [K-Dense-AI/claude-scientific-skills](https://github.com/K-Dense-AI/claude-scientific-skills) · MIT | قائمة «لا تختلق» المفصلة (مراجع، وDOI، وأرقام، وموافقات)، و«التحقق قبل التنسيق»، وحالة «ناقص» الظاهرة بدل نص مقنع | `university-report`، `academic-citations` | مصممة لأوراق المجلات الطبية والعلمية: CONSORT، وPRISMA، وملفات manifest وهاشات للادعاءات. ثقيلة جداً على تقرير طالب |
| **check-citations** | [PHY041/claude-skill-citation-checker](https://github.com/PHY041/claude-skill-citation-checker) · **بلا ملف ترخيص** | تصنيف المراجع المختلقة إلى ثلاثة أنواع (مختلق، ومُركّب، ومحرَّف) والتحقق عبر Crossref | `verify_refs.py` (كتبناه من الصفر) | لا ترخيص في المستودع، ويعمل على ملفات `.bib` فقط (LaTeX). تقارير الطلاب في Word بقوائم نصية |
| **academic-writing** | [David-Saeteros/claude-skills](https://github.com/David-Saeteros/claude-skills) · CC BY 4.0 | «شخّص أولاً ثم عدّل» بعد موافقة الكاتب، وتنسيق التغيير ~~القديم~~ ← **الجديد** *(السبب)*، وعلامة `[CITATION NEEDED]` | وضع التحرير في `academic-writing` | نصفها فحوص متخصصة في علم النفس ومعالجة اللغات (BERT، وBig Five) |
| **write-academic-report** | [phy041/claude-skill-write-academic-report](https://github.com/phy041/claude-skill-write-academic-report) · **بلا ملف ترخيص** | كتابة التقرير الطويل فصلاً فصلاً، مع ثوابت اتساق بين الفصول | `university-report` (مشروع التخرج) | LaTeX فقط، ويحتاج `tectonic`، ووكلاء متوازين. والإطار يقول MIT لكن المستودع بلا ترخيص |
| **humanities-thesis-skill** | [ganzhi-black/humanities-thesis-skill](https://github.com/ganzhi-black/humanities-thesis-skill) · MIT · 880 نجمة | قواعد صارمة ضد الاختلاق، و«فرّق بين ما تعرفه وما لا تعرفه»، وأسئلة الاستلام على جولات | `university-report` | بالصينية، ولرسائل العلوم الإنسانية الصينية ومراجعها (CNKI) |
| **paper-writing** | [vishalsachdev/claude-code-skills](https://github.com/vishalsachdev/claude-code-skills) · MIT | الحوار أولاً: سؤال واحد ثم البناء عليه، لا قائمة أسئلة طويلة. وقائمة فحص الجودة | `university-report` (الاستلام)، `report-review` | عامة لأوراق المجلات والمؤتمرات |
| **copydesk** | [gigio1023/agent-skills](https://github.com/gigio1023/agent-skills) · MIT | «احفظ المعنى قبل التلميع»: لا تحوّل «يجب أن يستعد» إلى «يستعد»، وقراءة النص كأنك لم تحضر النقاش | `academic-writing` | عامة لكل النصوص، ومرتبطة بملف شخصي لكاتب آخر وبالكورية |
| **document-quality-standards** | belumume/claude-skills · **بلا ملف ترخيص** | حلقة «ابنِ ← حوّل إلى صور ← انظر ← أصلح»، فلا يُسلَّم ملف دون النظر إلى صفحاته | `report-docx` §2 | لا ترخيص |

---

## ❌ مرفوضة (16)

° = حُكم عليها من وصفها وبنيتها دون قراءة كاملة.

| المهارة | المصدر | سبب الرفض |
|---|---|---|
| academic-paper° · academic-pipeline° · deep-research° | [Imbad0202/academic-research-skills](https://github.com/Imbad0202/academic-research-skills) (56k نجمة) | **ترخيص CC BY-NC**، غير تجاري، ولا يناسب مستودعاً عاماً قد يُعاد استخدامه. وهو خط من 12–13 وكيلاً لأوراق المجلات، وكل مهارة فيه 7–9 آلاف كلمة |
| docx | anthropics/skills، ونسخ منها في K-Dense | **ترخيص خاص (Proprietary)**، فلا يُنسخ إلى مستودع عام. وهي متاحة أصلاً في جلسات Claude باسم `anthropic-skills:docx`. ولا تعالج العربية |
| citation-management° · literature-review° · peer-review° | K-Dense-AI | تعتمد على PubMed وGoogle Scholar وواجهات بحث خارجية، وموجهة للبحث الطبي والعلمي |
| ml-paper-writing° · nature-polishing° · writing-anti-ai | [Galaxy-Dawn/claude-scholar](https://github.com/Galaxy-Dawn/claude-scholar) | لأوراق مؤتمرات تعلم الآلة ومجلة Nature. وفكرة `writing-anti-ai` موجودة أصلاً بصيغة أدق داخل `arabic-docx` |
| verify-refs° · humanize° · self-review° | [Aperivue/medsci-skills](https://github.com/Aperivue/medsci-skills) | للأوراق الطبية وأبحاث الأشعة (PubMed، وICMJE) |
| rtl-document-translation° | belumume/claude-skills | ترجمة ملفات موجودة، لا إنشاء تقارير. وبلا ترخيص |
| paper-humanizer · aigc-down · deai-academic-zh° | قائمة awesome-academic-skills | **هدفها خداع أدوات كشف الذكاء الاصطناعي** في الرسائل الجامعية. وهذا يتعارض مع النزاهة الأكاديمية، ويعرّض الطالب للعقوبة. أخذنا بدلاً منها «احذف العبارات الفارغة لأنها تُضعف النص»، مع الإفصاح حين تشترطه السياسة |
| physics-lab-report-skill° | [ydh0411](https://github.com/ydh0411/physics-lab-report-skill) · MIT | بالصينية، ولتقارير الفيزياء بـ LaTeX ومعايير جامعة صينية. أخذنا فكرة تحليل الخطأ في تقرير المختبر بصياغتنا |
| proofreading° | [jakobthumm/proofreading](https://github.com/jakobthumm/proofreading) · MIT | 100+ فحص لأوراق LaTeX في الرياضيات والروبوتات |
| thesis-writer° · lit-review° | ibrahim-kukash · bethww · MIT | الأولى رسائل بالإنجليزية فقط مع درجة «إنسانية» للنص، والثانية مراجعة أدبيات فقط، وفكرتها موجودة في `report-types.md` §8 |
| office-academic-skill° · research-writing-skill° | [zLanqing/codex-claude-academic-skills](https://github.com/zLanqing/codex-claude-academic-skills) | بالصينية أولاً، ولأوراق المجلات |
| apsa-style° · proofread° | [christopherkenny/skills](https://github.com/christopherkenny/skills) | لملفات Quarto ونمط APSA في العلوم السياسية |
| academic-writing (journalism)° | [jamditis/claude-skills-journalism](https://github.com/jamditis/claude-skills-journalism) | امتثال بحثي (CRediT، وPlan S، والتسجيل المسبق)، لا كتابة تقارير طلابية |
| مئات النسخ المكررة | [brycewang-stanford/Awesome-Agent-Skills-for-Empirical-Research](https://github.com/brycewang-stanford/Awesome-Agent-Skills-for-Empirical-Research) | قائمة تجميع فيها 1,262 مهارة منسوخة من مستودعات أخرى، وبعضها نسخ متعددة من المهارة نفسها. ما يهم منها تتبعناه إلى مصدره الأصلي |
| arabic-pdf · arabic-pptx | asadeisa/arabic-office-skills | جيدتان، لكن خارج نطاق الحاجة. التقرير يُسلَّم Word أو PDF محوَّلاً من Word |

---

## الفجوة: ما لا تفعله أي مهارة موجودة

| ما يحتاجه تقرير جامعي | موجود؟ |
|---|---|
| ملف Word عربي صحيح الاتجاه | ✅ `arabic-docx` |
| قواعد ضد اختلاق المراجع | ✅ جزئياً، ولأوراق المجلات |
| **قراءة التكليف ومعايير التقييم، وربط المخطط بها** | ❌ لا يوجد |
| **هياكل التقارير الطلابية: مختبر، ودراسة حالة، وتدريب ميداني، ومشروع تخرج…** | ❌ لا يوجد (تقرير التدريب الميداني بالذات غائب تماماً) |
| **تقرير كامل من Markdown إلى Word بغلاف جامعي وفهرس وترقيم، بالعربية والإنجليزية** | ❌ لا يوجد. الموجود LaTeX |
| **التحقق من مراجع نصية، لا ملفات `.bib`** | ❌ لا يوجد |
| **فحص تطابق الاستشهادات مع القائمة، مع المراجع العربية** | ❌ لا يوجد |
| **المراجع العربية: الاختصارات، والترتيب بتجاهل «ال»، وقواعد البيانات العربية** | ❌ لا يوجد |
| **الكتابة الأكاديمية العربية** | ❌ لا يوجد |
| **مراجعة بمعايير المحاضر قبل التسليم** | ❌ لا يوجد للتقارير الطلابية |

---

## البنية المنفّذة في `.claude/skills/`

```
skills/
├── مثبّتة (تنزيل)
│   └── arabic-docx          ← ملفات Word العربية (MIT)
│
└── مبنية (صنعنا)
    ├── university-report    ← المنسق: التكليف ← المخطط ← الأدلة ← الكتابة ← التوثيق ← التنسيق ← المراجعة
    │                          10 هياكل تقارير + تحليل التكليف + قوالب brief/outline/sources
    ├── academic-writing     ← العربية والإنجليزية الأكاديمية + وضع التحرير + عادات النص المولَّد
    ├── academic-citations   ← APA 7 · IEEE · Harvard · MLA · Chicago · المراجع العربية
    │                          verify_refs.py (Crossref) + check_citations.py (التطابق)
    ├── report-docx          ← build_report.py: Markdown → Word بغلاف وفهرس وترقيم وتسميات
    └── report-review        ← تقييم بالمعايير + أعلى ثلاثة إصلاحات + قائمة الفحص النهائية
```

### ملاحظات الترخيص

- **arabic-docx (MIT):** يبقى ملف `LICENSE` معها، ومصدرها في `SOURCE.md`.
- **الأفكار المأخوذة:** أعيدت كتابتها بلغتنا ولم يُنسخ نصها. والمهارات بلا ملف ترخيص (PHY041، وbelumume) أُخذت منها أفكار عامة فقط، لا شيفرة ولا نص.
- **السكربتات الثلاثة** (`build_report.py` و`verify_refs.py` و`check_citations.py`) كُتبت من الصفر في هذا المستودع.
