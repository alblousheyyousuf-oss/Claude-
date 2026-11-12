# IEEE — دليل التقارير الهندسية والتقنية

المرجع الرسمي: *IEEE Reference Guide* (موقع IEEE Author Center). الأقسام أحياناً تعتمد نسخة معدلة منه، فاتبع ما يحدده المقرر.

## 1. داخل النص

- أرقام بين قوسين مربعين: `[1]`، **بترتيب أول ظهور** في التقرير. المرجع الذي يتكرر يأخذ رقمه الأول نفسه.
- عدة مراجع: `[1], [3]` · مدى متصل: `[2]–[5]` · وبعض الأقسام تقبل `[1, 3]`.
- الرقم يقوم مقام الاسم: «as shown in [4]» أو «كما في [4]». ويمكن ذكر المؤلف: «LeCun et al. [1] showed…».
- الصفحة عند الاقتباس: `[3, p. 12]`.
- يوضع الرقم قبل علامة الترقيم: `…results [2].`

## 2. قائمة المراجع

- العنوان **References**. المراجع مرقمة `[1]`، `[2]`… بترتيب الاستشهاد، **لا أبجدياً**.
- المؤلفون: الأحرف الأولى ثم اللقب: `A. B. Surname`. حتى ستة مؤلفين يُذكرون كلهم، مع `and` قبل الأخير. وإن زادوا على ستة: الأول ثم `et al.`
- عنوان المقال أو الورقة بين علامتي تنصيص، والفاصلة **داخل** العلامتين: `“Title of article,”`
- اسم المجلة أو الكتاب أو المؤتمر مائل، والمجلات بالاختصار الرسمي (IEEE Trans. …).
- `vol.` و`no.` و`pp.` بأحرف صغيرة. والشهر مختصر.

## 3. أمثلة

**مقال في مجلة** (حقيقي):
> [1] Y. LeCun, Y. Bengio, and G. Hinton, “Deep learning,” *Nature*, vol. 521, no. 7553, pp. 436–444, May 2015, doi: 10.1038/nature14539.

**ورقة مؤتمر** (حقيقي):
> [2] K. He, X. Zhang, S. Ren, and J. Sun, “Deep residual learning for image recognition,” in *Proc. IEEE Conf. Comput. Vis. Pattern Recognit. (CVPR)*, Las Vegas, NV, USA, 2016, pp. 770–778, doi: 10.1109/CVPR.2016.90.

**كتاب:**
> [3] A. B. Author, *Title of Book*, 2nd ed. City, Country: Publisher, Year.

**فصل في كتاب:**
> [4] A. B. Author, “Title of chapter,” in *Title of Book*, C. D. Editor, Ed. City, Country: Publisher, Year, pp. 45–67.

**صفحة ويب:** صيغتان شائعتان، فاتبع ما يعتمده القسم:
> [5] Organization or A. B. Author. “Title of page.” Website Name. URL (accessed Mon. Day, Year).
> [5] A. B. Author. “Title of page.” Website Name. Accessed: Mon. Day, Year. [Online]. Available: URL

**رسالة جامعية:**
> [6] A. B. Author, “Title of thesis,” M.S. thesis, Dept. Name, Univ. Name, City, Country, Year.

**مواصفة قياسية (Standard):**
> [7] *Title of Standard*, Standard Number, Year.

**برنامج أو مستودع شيفرة:**
> [8] A. B. Author. *Name of Software*. (Version x.y). [Online]. Available: URL

**ورقة بيانات (Datasheet):**
> [9] Company, “Part number: Title,” Datasheet, Year. [Online]. Available: URL

## 4. أخطاء شائعة

- ترتيب القائمة أبجدياً، وهي في IEEE بترتيب الظهور.
- ترقيم يقفز ([1] ثم [3] ثم [2]). `check_citations.py` يكشفه.
- أسماء كاملة بدل الأحرف الأولى، أو `&` بدل `and`.
- خلط IEEE في النص مع APA في القائمة.
