# OB-Sim — محاكي إضافات Open Brush

يشغّل ملف إضافة Lua الحقيقي **كما هو**، بنسخة من أوامر Open Brush كُتبت مطابقة لكوده المصدري (v2.32)، ثم يرسم النتيجة ويسجّل فيديو من موضع المستخدم. الهدف أن تُرى النتيجة قبل تجربتها في النظارة.

Runs a real Open Brush Lua plugin unmodified against an emulation of the API written from the Open Brush C# source (v2.32), then renders what Open Brush would draw and records a video from the user's viewpoint.

## الاستعمال
```bash
pip install lupa                     # محرك Lua لبايثون
bash fetch_vendor.sh                 # three.js
python3 obsim_run.py ../BackgroundScript.KummaInk.lua logs/run.json --seconds 92   # [--scale 0.4] [--no-dwb]
node obsim_record.js logs/run.json out.mp4 --fps 24 --from 3 --to 92             # [--stills 10,20] [--bg paper]
```

## ما يحاكيه بدقة (من الكود المصدري)
- `Path:Draw` و`DrawWithBrush`: نقاط التحكم كما في `DrawStrokes.DrawNestedTrList`، بما فيها التنعيم وإسقاط آخر نقطة.
- الفرش المسطحة: اتجاه الشريط من دوران القلم (`ComputeSurfaceFrameNew`)، والعرض من الضغط (`PressuredSize`).
- الطبقات: الوضعية (TRS)، و`SetShaderClipping(start, end)` على مستوى الدفعة (batch) بترتيب الرسم، و`_Dissolve`، والإظهار والإخفاء.
- `Brush.size` قيمة من 0 إلى 1، و`Brush.sizeAbsolute` الحجم الحقيقي، و`Brush.direction = rotation * back`.

## ما لا يحاكيه
أشكال الفرش وأنسجتها تقريبية، والإضاءة والأداء الحقيقي على Quest خارج نطاقه. والنتيجة تقدير قريب، لا لقطة من النظارة.
