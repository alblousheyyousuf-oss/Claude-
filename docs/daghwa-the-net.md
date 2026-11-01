# «الشَّبَكة» — الضغوة في ثماني نوافذ ليثوفان تتفاعل مع المارة
**The Net(work) — Daghwa in Eight Responsive Lithophane Windows**

**الموقع:** ممر قسم التربية الفنية، جامعة السلطان قابوس · 8 نوافذ داخلية (شبكة 2×4) · النافذة ≈ 80 × 100 سم
**الموضوع:** الضغوة، الصيد الجماعي للسردين على ساحل شمال الباطنة (شناص، لوى، صحار، صحم)
**القرار:** وافقت اللجنة على **الليثوفان للنوافذ الثماني كلها**، مع **حساسات حركة** تجعل النوافذ تتفاعل مع المارة
**الأدوات:** طابعات القسم ثلاثية الأبعاد · CNC · شرائط LED قابلة للبرمجة · حساسات حضور رادارية

> هذا الملف يحل محل النسخة السابقة من المقترح نفسه (التي كان صفها العلوي أكريليكاً محفوراً). المقترح الأول ذو الاتجاه المختلف باقٍ في [`corridor-windows-art.md`](./corridor-windows-art.md).

---

## 1 · الفكرة

**كلمة «شبكة» تعني شبكة الصيد وتعني الشبكة الرقمية.** والضغوة شبكة بالمعنيين: خيوط تجمع السمك، وناس يجمعهم العمل.

العمل يروي **يوماً واحداً من الضغوة في أربعة فصول**، وكل فصل يُرى مرتين، وكل النوافذ ليثوفان:

| | الصف العلوي A: **عين الآلة** | الصف السفلي B: **عين الإنسان** |
|---|---|---|
| **الصورة** | صورة من الأعلى بطائرة مسيّرة: الهلال على البحر، والسرب، وبساط السمك | صورة بمستوى العين: الأيدي والوجوه والجهد |
| **لون الضوء خلفها** | بارد: أبيض مزرق كضوء الفجر على البحر | دافئ: عنبري كصورة قديمة |
| **المعنى** | المستقبل والبيانات: البحر كما تراه الآلة | الذاكرة: البحر كما يعيشه الناس |

**الصورة تتحمّض حين تقترب.** الليثوفان دون ضوء نقش أبيض صامت. والحساس يشعر بالمار فيضيء النافذة تدريجياً، فتظهر الصورة كما تظهر الصورة الفوتوغرافية في حوض التحميض. الماضي يظهر لمن يقترب منه.

**شبكة البلاطات هي شبكة الصيد.** كل نافذة مكوّنة من بلاطات مطبوعة تُثبَّت في إطار شبكي يقصه الـCNC، وخطوط الإطار الرفيعة تظهر كعيون شبكة فوق الصورة.

---

## 2 · القصة في ثماني لوحات

العمود 1 هو أول ما يراه القادم من الاتجاه الأكثر حركة في الممر (افتراض يُعكس حسب الموقع).

| | **الفصل 1: الليخ** | **الفصل 2: الخروج والإحاطة** | **الفصل 3: السحب (الذروة)** | **الفصل 4: الحصاد والتقاسم** |
|---|---|---|---|---|
| **A: من الأعلى** | **A1** · الليخ مفروداً على الرمل عند خط الماء: صف الفلين الأبيض وصف الرصاص متوازيان، وقارب مسحوب إلى الشاطئ | **A2** · القارب يرسم بالفلين هلالاً حول بقعة داكنة هي السرب، وأثره الأبيض خلفه، وطرفا الشبكة يعودان إلى الشاطئ | **A3** · الهلال يضيق في المياه الضحلة، والماء داخله يغلي بالسمك، وصفّان من الرجال على الرمل يشدّون الطرفين | **A4** · السردين مفروش على الرمل للتجفيف كمستطيل فضي، وحوله سلال وناس |
| **B: بمستوى العين** | **B1** · صياد مسنّ يصلح الشبكة (معاير)، وعيونها تملأ مقدمة الصورة | **B2** · رجال يدفعون القارب المحمّل بالشباك إلى الموج بعد الفجر | **B3** · رجال يشدّون الحبل بأجساد مائلة إلى الخلف وأقدام في الرمل المبلل | **B4** · الفرز والتقاسم: سلال وأيدٍ، وكبير يناول صغيراً سمكة |

**ما يربط النوافذ:**
- **خط الأفق** في الصف السفلي وخط الساحل في الصف العلوي يستمران عبر النوافذ الأربع.
- **في كل عمود يرى المار المشهد نفسه مرتين:** من السماء ومن الأرض.
- **الذروة في العمود 3**، عند نقطة القطاع الذهبي لطول الواجهة.

---

## 3 · كيف تعمل النافذة الواحدة

### 3.1 · الطبقات (كلها داخل الغرفة خلف الزجاج)

```
 CORRIDOR │ GLASS │ ROOM SIDE (≈ 7–9 cm deep box on its own stand)
          │       │
 0 mm     │       │ ← lithophane tiles held in a CNC-cut lattice
 nothing  │       │ ← opal acrylic diffuser (3 mm)
 sticks   │       │      4–5 cm air
 out      │       │ ← rows of addressable RGBW LEDs on a white back panel
          │       │
          │  ◄))) │ ← mmWave presence sensor behind the lower window (one per column)
```

- **الليثوفان:** بلاطات بلاستيك أبيض تتفاوت سماكتها بين نحو 0.8 و3 مم. حيث يرق البلاستيك يمر الضوء فيظهر فاتحاً، وحيث يسمك يحجبه فيظهر داكناً، فتتكوّن صورة فوتوغرافية كاملة.
- **الناشر:** لوح أكريليك حليبي يوزع الضوء بالتساوي حتى لا تظهر نقاط الـLED خلف الصورة.
- **الإضاءة:** صفوف من شريط LED عنونة RGBW كل 8–10 سم. «عنونة» تعني أن كل جزء صغير من الشريط يُتحكم فيه وحده، فيمكن أن يتحرك الضوء خلف الصورة. وW تعني قناة بيضاء نقية تعطي الليثوفان أوضح تفاصيله.
- **الصندوق:** إطار يقصه الـCNC من MDF أو خشب رقائقي، مدهون بالأبيض من الداخل، ومثبت على قاعدة مستقلة دون لصق بالزجاج.

### 3.2 · الحساسات

| السؤال | الجواب |
|---|---|
| **أي حساس؟** | **حساس حضور راداري mmWave** بتردد 24 GHz، مثل **HLK-LD2410**. صغير ورخيص، ويكشف الشخص المتحرك والواقف معاً، ويعطي المسافة إليه حتى نحو 6 م |
| **لماذا ليس حساس PIR العادي؟** | **حساس PIR لا يرى عبر الزجاج**، لأن الزجاج يحجب الأشعة تحت الحمراء التي يعتمد عليها. أما الرادار فيعبر الزجاج العادي، فيبقى الحساس داخل الغرفة ولا شيء يُركَّب في الممر |
| **كم حساساً؟** | **4، حساس لكل عمود**، خلف النافذة السفلية على ارتفاع نحو متر. كل حساس يتحكم في نافذتي عموده |
| **ما يجب اختباره** | ① أن الحساس يرى عبر زجاجكم تحديداً، لأن الزجاج المطلي بطبقة معدنية يحجب الرادار. ② ألا تتداخل الحساسات الأربعة: تُضبط حساسيتها وأقصى مسافة لكل منها، وتُجرَّب معاً |

### 3.3 · المتحكم

- **متحكم ESP32 واحد** (لوحة صغيرة بحجم علبة الكبريت) يقرأ الحساسات الأربعة ويشغّل شرائط النوافذ الثماني.
- **البرنامج: ESPHome** (مجاني). يُكتب فيه ملف إعدادات نصي بدل البرمجة، وهو يدعم حساس LD2410 مباشرة، ويقسم الشرائط إلى ثماني نوافذ، ويُعدَّل من الهاتف أو الحاسوب عبر الشبكة.
- **حساس حرارة** (مثل DS18B20) في أسخن صندوق، يخفض الإضاءة تلقائياً إن ارتفعت الحرارة (§6).

---

## 4 · سلوك النوافذ

| الحالة | ماذا يرى المار |
|---|---|
| **الانتظار** (الممر خالٍ) | نقوش بيضاء صامتة خلف الزجاج، مع «تنفس» ضوئي خافت جداً كل بضع ثوانٍ |
| **الاقتراب: التحميض** | كلما اقترب المار من عمود أضاءت نافذتاه تدريجياً، فتظهر الصورة كأنها تتحمّض. الحساس يقيس المسافة، فالضوء يتبع القرب |
| **المرور: الأثر** | النوافذ التي مرّ بها تبقى مضاءة ثم تخبو ببطء خلال ثوانٍ، فيترك المار خلفه أثراً من الضوء، والقصة تتكشف معه فصلاً فصلاً |
| **الوقوف: المشهد الحي** | إن وقف أمام عمود بضع ثوانٍ، يبدأ الضوء خلف صورتيه بالحركة الهادئة (الجدول التالي) |
| **خارج الدوام** | إطفاء بجدول زمني |

**المشهد الحي:** الصورة نفسها ثابتة، وما يتحرك هو الضوء خلفها، لأن الشريط العنونة يضيء أجزاء من الصورة دون غيرها.

| العمود | A (من الأعلى) | B (بمستوى العين) |
|---|---|---|
| 1 | ضوء ينساب ببطء على طول الشبكة المفرودة | توهج دافئ يتنفس حول يدي الصياد |
| 2 | ضوء يتبع مسار القارب على الهلال | الشمس تشرق: يزداد الضوء حول قرص الشمس |
| 3 | ومضات هادئة متفرقة داخل الهلال كأن السمك يلمع | موجة ضوء تتحرك من المنتصف نحو الطرفين بإيقاع الشد |
| 4 | لمعان يمر على بساط السردين | توهج حول يدي الكبير والصغير عند تناول السمكة |

**قواعد السلامة البصرية:** لا وميض، ولا تبدل أسرع من ثانية، ولا أكثر من 3 تغيرات حادة في الثانية (الحد المعتمد لتجنب نوبات الحساسية للضوء).

**إضافات اختيارية:** ضوء يتغير مع وقت اليوم (عنبري صباحاً، محايد ظهراً، ذهبي عصراً)، وصوت موج خافت جداً عند الوقوف، أو رمز QR مسطح يفتح تسجيلات الصيادين.

---

## 5 · الإنتاج

### 5.1 · من الصورة إلى ليثوفان

1. **الصورة:** صورة حقيقية بالأبيض والأسود، عالية التباين، بإضاءة جانبية وخلفية بسيطة.
2. **التقسيم:** قسّم صورة النافذة إلى بلاطات بحجم سرير الطابعة (§5.2)، واجعل خطوط التقسيم تمر حيث لا توجد وجوه أو أيدٍ.
3. **التحويل:** أداة مجانية مثل ItsLitho أو 3dp.rocks تحوّل كل بلاطة إلى ملف طباعة، بسماكة دنيا نحو 0.8 مم وقصوى نحو 3 مم.
4. **الطباعة:** PLA أبيض، وتعبئة 100٪، وطبقات 0.12–0.16 مم.
5. **التركيب:** البلاطات في الإطار الشبكي فوق الناشر، داخل الصندوق.

### 5.2 · عدد البلاطات حسب الطابعات

| سرير الطابعة | تقسيم النافذة | بلاطات النوافذ الثماني |
|---|---|---|
| نحو 25 × 25 سم | 4 × 4 بلاطات (20 × 25 سم) | 128 |
| 30 × 30 سم أو أكبر | 3 × 4 بلاطات (≈ 27 × 25 سم) | 96 |

### 5.3 · تقدير أولي للجهد

| البند | التقدير |
|---|---|
| **البلاستيك** | نحو **14 كغ PLA أبيض** للنوافذ الثماني، لأن المساحة الكلية 6.4 م² بسماكة متوسطة نحو 1.8 مم، والكمية لا تتغير بتغير حجم البلاطات |
| **زمن الطباعة** | نحو **1000 ساعة طابعة**. مع 8 طابعات نحو 120 ساعة لكل طابعة، أي **2–3 أسابيع واقعياً** مع الإعادات والمتابعة |
| **الإضاءة** | نحو 8–10 م من الشريط لكل نافذة (64–80 م إجمالاً). قدرة قصوى نحو 60 واط للنافذة، ونحو 20–25 واط في التشغيل العادي |
| **الـCNC** | 8 صناديق، و8 إطارات شبكية للبلاطات، وحوامل للحساسات |

الأرقام تقديرية، وتُضبط بعد طباعة **بلاطة تجريبية** وقياس زمنها الفعلي.

### 5.4 · ابدأ بنافذة واحدة

نفّذ **نافذة B3 كاملة** (بلاطاتها، وصندوقها، وحساس، والمتحكم) قبل الالتزام بالثماني. اختبر فيها:
- وضوح الصورة وظهور خطوط التقسيم.
- تجانس الإضاءة.
- رؤية الحساس عبر الزجاج.
- الحرارة بعد 4 ساعات تشغيل متواصل.

### 5.5 · قائمة المكونات

| المكوّن | الكمية | ملاحظة |
|---|---|---|
| PLA أبيض | ≈ 14 كغ + احتياط | من دفعة واحدة إن أمكن، لأن درجات الأبيض تختلف بين الدفعات |
| شريط LED عنونة RGBW (مثل SK6812 RGBW) | 64–80 م | يُفضّل 12V لتقليل التيار، بكثافة نحو 30 LED/م |
| أكريليك حليبي (Opal) 3 مم | 8 ألواح ≈ 82 × 102 سم | الناشر |
| MDF أو خشب رقائقي | حسب تصميم الصناديق | للصناديق والإطارات الشبكية |
| حساس HLK-LD2410 | 4 + 1 احتياط | — |
| متحكم ESP32 | 1 + 1 احتياط | — |
| مزودات طاقة 12V | حسب حساب الفني | مع مصاهر وتوزيع للتغذية على طول الشرائط |
| حساس حرارة DS18B20 | 2 | — |
| أسلاك وموصلات وقنوات ألومنيوم للشرائط | — | القنوات تبدد حرارة الشرائط |

---

## 6 · السلامة

- **الحرارة والليثوفان:** PLA يبدأ باللين قرب 55–60 °C. أبقِ البلاطات على بعد 4 سم على الأقل من الـLED، وثبّت الشرائط في قنوات ألومنيوم، واترك فتحات تهوية في الصناديق، ولا تشغّل الأبيض بأقصى شدته لفترات طويلة. حساس الحرارة يخفض الإضاءة تلقائياً فوق نحو 45 °C. وإن كانت الغرفة حارة، فـ PETG الأبيض يتحمل حرارة أعلى.
- **جهة الممر:** لا شيء يُثبَّت عليها. الصناديق والحساسات كلها داخل الغرفة على قواعد مستقلة.
- **الكهرباء:** جهد منخفض، ومزودات الطاقة داخل الغرفة بمصاهر، ودائرة مستقلة بقاطع حماية من التسرب، وتركيب عبر فني معتمد.
- **الحريق:** الكمية الكبيرة من PLA بجوار مسار إخلاء تحتاج استشارة إدارة المرافق، وقد تُطلب خيوط مقاومة للهب.
- **الحساسات:** قدرة إرسال حساسات mmWave منخفضة جداً، أقل بكثير من الهاتف.
- **الغرفة:** تُقفل، ويُحدَّد من يدخلها للصيانة.

---

## 7 · ما تقوله المصادر عن الضغوة

- **صيد جماعي قرب الشاطئ، أغلبه للسردين (العومة)**، ويُسمى أيضاً الضاغية والضواغي. [الرؤية، الوطن]
- القارب يطرح الشبكة حول السرب **بشكل هلالي**، فتصير «حلقة دائرية ضخمة من الشباك أطرافها ممدودة إلى الساحل». [الرؤية، وهج الخليج]
- **الرجال يسحبون الحبال من الطرفين بأيديهم**، فيظل السمك حبيس الشبكة حتى يلتقطه الصيادون. [وهج الخليج، الوطن]
- الشبكة **«الليخ»**، وقد يصل طولها إلى **نحو 600 باع**. أجزاؤها: العيون، والفلين، والرصاص أو المساو، والبرامة، وإصلاحها يسمى **«معاير»**. [الرؤية، الوطن]
- «كلما كثر العدد كانت الحصيلة أفضل»، والمشهد ينتهي بـ«تقاسم ما جاء به البحر». [البيان]
- **الموسم من أكتوبر إلى أبريل.** السردين المجفف علف وسماد وطعام، وفي صحم **«لجنة سنن البحر»** تنظم مواعيد الصيد. [عُمان اليومية]

**ما يحتاج زيارة ميدانية:** كيف يُرصد السرب ومن يرصده، وأسماء الأدوار، واسم القارب في الباطنة، والأهازيج إن وُجدت، وطريقة التقاسم.

**الزيارة الميدانية:**
- **المكان والموعد:** فجراً بين أكتوبر وأبريل، في شناص أو لوى أو صحار أو صحم.
- **التصوير:** صور بالأبيض والأسود بإضاءة جانبية لمشاهد الصف السفلي، وصور من الأعلى بطائرة مسيّرة لمشاهد الصف العلوي. **التصوير بالمسيّرة في عُمان يحتاج عادةً تصريحاً من الجهة المختصة**، فتحقق قبل الزيارة أو استعن بمصور مرخّص.
- **الموافقة:** إذن كل من تظهر صورته.

---

## 8 · البرومبتات

صور الذكاء الاصطناعي هنا **للنموذج الأولي فقط** (لاختبار البلاطة والإضاءة)، أما العمل النهائي فبصور حقيقية من الميدان. كل البرومبتات تطلب صوراً بالأبيض والأسود عالية التباين، لأن الليثوفان لا يحمل لوناً، ولونه من الضوء خلفه. البرومبتات تفترض أن العمود 1 على اليمين.

### 8.1 · التكوين الرئيسي
```
Eight backlit lithophane panels in two rows of four, each panel made of square 3D-printed white tiles held in a thin dark grid, telling one day of traditional collective beach-seine sardine fishing on the Omani Batinah coast in four chapters read from right to left: mending the long net, launching the boat and encircling the fish with a crescent of floats, hauling the net ashore from both ends, drying and sharing the catch, the top row shows each chapter as an aerial drone view glowing in cool blue-white light, the bottom row shows the same chapter at eye level glowing in warm amber light, monochrome photographic images revealed by light from behind, art installation in a dark room --ar 5:3 --style raw --s 150 --no text, letters, numbers, color photograph
```

### 8.2 · الصف العلوي: صور من الأعلى
```
A1 — Aerial drone photograph looking straight down at dawn on the Omani Batinah coast: a very long fishing net laid out straight on pale sand along the waterline, a row of white floats and a row of dark sinkers running parallel, a small boat pulled up on the beach, a few fishermen as small figures, gentle surf lines, black and white documentary photograph, high contrast, crisp detail, suitable for conversion into a 3D-printed lithophane --ar 4:5 --style raw --s 80 --no text, color
```
```
A2 — Aerial drone photograph looking straight down: a small fishing boat drawing a wide crescent of white floats around a dark school of sardines just off the beach, the boat's white wake curving behind it, both ends of the net leading back to the shore, black and white documentary photograph, high contrast, crisp detail, suitable for conversion into a 3D-printed lithophane --ar 4:5 --style raw --s 80 --no text, color
```
```
A3 — Aerial drone photograph looking straight down: a crescent of white floats tightening in shallow water, the water inside churning white with thousands of flashing sardines, two lines of fishermen on the sand hauling the ropes from both ends, black and white documentary photograph, high contrast, crisp detail, suitable for conversion into a 3D-printed lithophane --ar 4:5 --style raw --s 80 --no text, color
```
```
A4 — Aerial drone photograph looking straight down: silver sardines spread out to dry on the sand forming a large shimmering rectangle, round baskets and a few people around it, long morning shadows, black and white documentary photograph, high contrast, crisp detail, suitable for conversion into a 3D-printed lithophane --ar 4:5 --style raw --s 80 --no text, color
```

### 8.3 · الصف السفلي: صور بمستوى العين
```
B1 — Close-up of the weathered hands of an elderly Omani fisherman mending a large nylon fishing net on the beach, the net mesh filling the frame, black and white documentary photograph, high contrast, strong side light, fine texture, simple uncluttered background, suitable for conversion into a 3D-printed lithophane --ar 4:5 --style raw --s 80 --no text, color
```
```
B2 — Omani fishermen pushing a small fishing boat loaded with nets into gentle waves just after dawn, figures backlit by the rising sun, spray and motion, black and white documentary photograph, high contrast, simple background, suitable for conversion into a 3D-printed lithophane --ar 4:5 --style raw --s 80 --no text, color
```
```
B3 — Two long lines of Omani fishermen in traditional wizar waist wraps hauling thick ropes on the beach, leaning back with effort, bare feet in wet sand, rhythm and tension, the rope crossing the frame horizontally at the center, black and white documentary photograph, high contrast, strong side light, suitable for conversion into a 3D-printed lithophane --ar 4:5 --style raw --s 80 --no text, color
```
```
B4 — Fishermen, elders and children sorting and sharing a catch of sardines in round baskets on the beach, hands and faces, a warm community moment, black and white documentary photograph, high contrast, simple background, suitable for conversion into a 3D-printed lithophane --ar 4:5 --style raw --s 80 --no text, color
```

### 8.4 · صورة المحاكاة للجنة
```
Photorealistic architectural visualization of a modern university corridor in Muscat, Oman, along one wall a grid of eight internal glass windows in two rows of four, each about 80 cm wide and 1 m tall, behind the clear flat glass eight backlit lithophane panels made of square 3D-printed white tiles in a thin grid: the top row glows cool blue-white with aerial views of a crescent fishing net on the sea, the bottom row glows warm amber with scenes of fishermen hauling ropes, one student stands close to a window that glows brightly while the windows further away are dim and pale, eye-level perspective along the corridor, interior design magazine photography --ar 16:9 --style raw --s 100 --no text, signage
```

صيغ ChatGPT / DALL·E لكل برومبت موجودة في صفحة اللجنة، مع زر يبدّل بين الأداتين.

---

## المصادر

- البيان 2018: «ضغوة البحر.. أهازيج الموج على إيقاع الصيد الجماعي» — https://www.albayan.ae/five-senses/mirrors/2018-07-15-1.3315239
- البيان 2023: «الصيد بالضغوة مهنة الأجداد والأحفاد» — https://www.albayan.ae/uae/news/2023-12-11-1.4781187
- وهج الخليج: «صيد وفير بطريقة الضغوة لصيادي شمال الباطنة» — https://www.wa-gulf.com/906330
- الرؤية: «غزل الليخ.. حرفة يدوية تقليدية» — https://alroya.om/post/157920/
- الوطن: «صناعة الشباك البحرية "غزل الليخ"» — https://alwatan.om/details/102798
- عُمان اليومية: «الصيد التقليدي الضواغي في ولاية صحم» — https://www.omandaily.om/article/1169702
- عُمان اليومية: «صيد السردين.. موروث تقليدي ومورد اقتصادي بمحافظة ظفار» — https://www.omandaily.om/article/1169599
