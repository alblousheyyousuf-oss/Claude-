# APA 7 — دليل التقارير الطلابية

المرجع الرسمي: *Publication Manual of the American Psychological Association* (7th ed., 2020) وموقع apastyle.apa.org. الأمثلة الحقيقية هنا تحقق منها Crossref، والباقي قوالب بين أقواس.

**قاعدة البناء:** المؤلف. (التاريخ). العنوان. المصدر. ← **Author. (Date). Title. Source.**

---

## 1. الاستشهاد داخل النص

| الحالة | بين قوسين (Parenthetical) | سردي (Narrative) |
|---|---|---|
| مؤلف واحد | (LeCun, 2015) | LeCun (2015) |
| مؤلفان | (Smith & Lee, 2020) — `&` داخل القوسين | Smith and Lee (2020) — `and` في السرد |
| 3 فأكثر | (LeCun et al., 2015) **من أول استشهاد** | LeCun et al. (2015) |
| مؤلف مؤسسي باختصار | أول مرة: (World Health Organization [WHO], 2023)، ثم: (WHO, 2023) | World Health Organization (WHO, 2023)، ثم WHO (2023) |
| بلا مؤلف | (*Title of Book*, 2020) أو ("Title of Article," 2020) | — |
| بلا تاريخ | (Smith, n.d.) | Smith (n.d.) |
| عدة أعمال | (Adams, 2017; Brown, 2021) **أبجدياً** وتفصل بينها فاصلة منقوطة | — |
| المؤلف نفسه بسنوات مختلفة | (Smith, 2018, 2020) | — |
| المؤلف نفسه في سنة واحدة | (Smith, 2020a, 2020b)، والحرف يتبع ترتيب العنوان في القائمة | — |
| اقتباس مباشر | (Smith, 2020, p. 25) · (pp. 25–26) · (para. 4) لما لا صفحات له | Smith (2020) stated that "…" (p. 25). |
| مصدر ثانوي | (Piaget, 1952, as cited in Lee, 2020). Lee فقط في القائمة | — |
| تواصل شخصي (مقابلة، بريد) | (A. Khan, personal communication, March 5, 2026). **لا يدخل القائمة** | — |

**الاقتباس الطويل** (40 كلمة فأكثر): فقرة مستقلة مزاحة 1.27 سم، بلا علامات تنصيص، والاستشهاد بعد النقطة الأخيرة.

## 2. قائمة المراجع: التنسيق

- العنوان **References** في الوسط وبخط غامق، في صفحة جديدة.
- مسافة مزدوجة، و**مسافة معلّقة (hanging indent)** قدرها 1.27 سم (0.5 بوصة). `build_report.py` يطبقها تلقائياً تحت عنوان المراجع.
- الترتيب أبجدي بلقب المؤلف الأول، حرفاً حرفاً. «لا شيء يسبق شيئاً»: Brown, J. قبل Browning, A.
- المؤلف نفسه: الأقدم أولاً. وأعماله منفرداً قبل أعماله مع آخرين.
- **المؤلفون:** حتى 20 مؤلفاً يُذكرون كلهم بصيغة `Surname, A. A.`، و`&` قبل الأخير. 21 فأكثر: الأوائل الـ19، ثم `…`، ثم الأخير.
- **العناوين:** عنوان المقال والفصل والكتاب بأحرف الجملة (Sentence case: الحرف الأول، وأول كلمة بعد النقطتين، وأسماء العلم). اسم المجلة بأحرف العنوان (Title Case) ومائل.
- **المائل:** الكتب، والتقارير، وصفحات الويب المستقلة، واسم المجلة ورقم المجلد. أما العدد بين قوسين فليس مائلاً: `*Nature*, *521*(7553)`.
- **DOI** بصيغة رابط: `https://doi.org/10.xxxx`، بلا «Retrieved from»، وبلا نقطة بعده.
- لا يُذكر مكان النشر للكتب (تغيير في APA 7).
- **تاريخ الاسترجاع** فقط للصفحات التي يتغير محتواها عمداً: `Retrieved March 5, 2026, from https://…`

## 3. أمثلة حسب نوع المصدر

**مقال في مجلة، له DOI** (حقيقي):
> LeCun, Y., Bengio, Y., & Hinton, G. (2015). Deep learning. *Nature*, *521*(7553), 436–444. https://doi.org/10.1038/nature14539

**مقال بلا DOI** (من قاعدة بيانات أكاديمية): لا يُذكر رابط القاعدة.
> Surname, A. A. (Year). Title of article. *Journal Name*, *Volume*(Issue), pages.

**كتاب** (حقيقي، والمؤلف مؤسسة هي الناشر نفسه، فلا يُكرر اسم الناشر):
> American Psychological Association. (2020). *Publication manual of the American Psychological Association* (7th ed.). https://doi.org/10.1037/0000165-000

> Surname, A. A. (Year). *Title of book: Subtitle* (2nd ed.). Publisher.

**فصل في كتاب محرَّر:**
> Surname, A. A. (Year). Title of chapter. In E. E. Editor & F. F. Editor (Eds.), *Title of book* (pp. 45–67). Publisher. https://doi.org/…

**ورقة مؤتمر منشورة في وقائع** (حقيقي):
> He, K., Zhang, X., Ren, S., & Sun, J. (2016). Deep residual learning for image recognition. In *Proceedings of the IEEE Conference on Computer Vision and Pattern Recognition* (pp. 770–778). IEEE. https://doi.org/10.1109/CVPR.2016.90

**عرض في مؤتمر (غير منشور):**
> Surname, A. A. (Year, Month Day–Day). *Title of presentation* [Paper presentation]. Conference Name, City, Country. URL

**تقرير حكومي أو مؤسسي:**
> Organization Name. (Year). *Title of report* (Report No. 123). Publisher if different from author. URL

**صفحة ويب:**
> Surname, A. A. (Year, Month Day). *Title of page*. Site Name. URL
> Organization Name. (Year, Month Day). *Title of page*. URL  ← حين يكون المؤلف هو الموقع نفسه

**رسالة جامعية:**
> Surname, A. A. (Year). *Title of thesis* [Master's thesis, University Name]. Database or Archive Name. URL
> Surname, A. A. (Year). *Title of dissertation* [Unpublished doctoral dissertation]. University Name.

**مقال صحفي:**
> Surname, A. A. (Year, Month Day). Title of article. *Newspaper Name*. URL

**فيديو يوتيوب:**
> Channel or Author Name. (Year, Month Day). *Title of video* [Video]. YouTube. URL

**مجموعة بيانات · برنامج:**
> Author. (Year). *Title of dataset* (Version 1.0) [Data set]. Publisher. URL
> Author. (Year). *Title of software* (Version 2.3) [Computer software]. Publisher. URL

**شرائح المحاضرة أو مواد المقرر:**
> Instructor, A. A. (Year). *Title of slides* [PowerPoint slides]. Learning Platform Name (e.g., Blackboard, Moodle). URL

**أداة ذكاء اصطناعي** (بحسب إرشاد APA Style، 2023):
> Anthropic. (2026). *Claude* (Version name) [Large language model]. https://claude.ai
> OpenAI. (2023). *ChatGPT* (Mar 14 version) [Large language model]. https://chat.openai.com/chat

في النص: (Anthropic, 2026). ويُذكر في النص ما طُلب من الأداة، ويمكن وضع المحادثة كاملة في ملحق. **اتبع سياسة المقرر أولاً.** بعض المقررات تريد الإفصاح في فقرة منهجية لا في المراجع.

**مصدر بلغة أخرى غير لغة التقرير:** العنوان بلغته الأصلية، ثم ترجمته بين قوسين مربعين. والمصادر بحروف غير لاتينية تُكتب بالحروف اللاتينية (Romanization) في التقارير الإنجليزية. انظر `arabic-sources.md`.

## 4. التقرير الطلابي بتنسيق APA 7

| العنصر | القاعدة |
|---|---|
| صفحة العنوان | العنوان (غامق، في وسط النصف العلوي)، ثم اسم الطالب، والقسم والجامعة، ورمز المقرر واسمه، واسم المحاضر، وتاريخ التسليم |
| ترقيم الصفحات | أعلى اليمين في كل الصفحات. **لا رأس متكرر (running head)** في التقارير الطلابية |
| الخط | أحد هذه: Times New Roman 12، أو Calibri 11، أو Arial 11، أو Georgia 11، أو Lucida Sans Unicode 10 |
| التباعد والهوامش | مسافة مزدوجة في كل شيء، وهوامش 2.54 سم (1 بوصة) |
| الفقرات | محاذاة يسار بلا ضبط (flush left)، وإزاحة أول سطر 1.27 سم |
| العناوين | المستوى 1: وسط، غامق، Title Case · المستوى 2: يسار، غامق · المستوى 3: يسار، غامق مائل · المستوى 4: مزاح، غامق، ينتهي بنقطة ويكمل النص بعده · المستوى 5: مثله مائلاً |
| المقدمة | لا يُكتب عنوان «Introduction». يُكرر عنوان التقرير في أول الصفحة الأولى من النص |
| الجداول والأشكال | الرقم غامق (**Table 1**)، والعنوان في السطر التالي مائلاً وبأحرف العنوان، **فوق** الجدول **وفوق** الشكل. والملاحظات (Note.) تحتهما |
| الأرقام | بالحروف من zero إلى nine، وبالأرقام من 10 فما فوق. ويُستثنى: القياسات، والإحصاءات، والنسب المئوية، والأعمار، والوقت، والتواريخ، فهي أرقام دائماً |

**في `build_report.py`:** هذه الإعدادات تقترب من APA 7: `line_spacing: 2.0` · `justify: false` · `first_line_indent_cm: 1.27` · `margins_cm: 2.54` · `figure_caption: above` · `number_headings: false`. التفاصيل في `report-docx`.

> **تنبيه:** كثير من الجامعات تطلب «APA للتوثيق فقط» مع تنسيق خاص بها للتقرير (ترقيم العناوين، وغلاف بشعار الجامعة، ومسافة 1.5). فاسأل: هل المطلوب APA للمراجع وحدها أم للتنسيق كله؟
