# deep-study — ملف المراجع الموحّد

> **هذا هو ملف المعرفة الوحيد الذي ترفعه في مشروع Claude.**
> يدمج المراجع الأربعة للمهارة في ملف واحد ليسهل رفعه من الجوال.
> ارفعه في **Project knowledge** مع موادك الدراسية، والصق كتلة التعليمات من
> `deep-study-project.md` في **Project instructions**.
>
> النسخة المرجعية الأصلية في `.claude/skills/deep-study/` — أي تعديل يُطبَّق هناك
> أولاً ثم يُعاد توليد هذا الملف.

## أقسام هذا الملف

| # | القسم | متى يُقرأ |
|---|---|---|
| 1 | Item Writing | قبل كتابة أي سؤال أو اختبار — بلا استثناء |
| 2 | Subject Modes | عند تحديد نمط المادة، يُقرأ القسم المطابق فقط |
| 3 | Marking | قبل تصحيح أي إجابة مقالية |
| 4 | State Ledger | في ختام كل جلسة |

---

# القسم 1 — Item Writing


Read this before writing any question, at any point. Without these standards, generated
questions drift to the lowest cognitive level with dead distractors — items a smart
person who never took the course could answer. Those teach nothing and measure nothing.

## Contents

1. The four gates
2. Difficulty is not quality
3. Cognitive level
4. Anatomy of a multiple-choice item
5. Distractors — the six sources
6. Cues that give the answer away
7. Constructed-response and essay items
8. Difficulty calibration
9. Disclosure
10. Worked example

---

## 1. The four gates

Run every item through these before showing it. An item that fails any gate is
rebuilt or discarded — never softened past.

| # | Gate | If it fails |
|---|---|---|
| 1 | Could a clever person who **never took this course** answer it correctly? | Trivial item — discard |
| 2 | Can it be solved **by elimination alone**, without knowing the content? | Distractors are dead — rebuild them |
| 3 | Can you write a **clear marking criterion** for it? | Ambiguous — rewrite |
| 4 | Does the difficulty come from the **content** or from the wording? | From wording — simplify the stem |

Gate 1 alone removes most bad questions. Apply it honestly.

## 2. Difficulty is not quality

A hard question is not automatically a good one, and a good question is not necessarily
hard. The real measure is **discrimination**: does this item separate students who have
mastered the material from those who have not?

A hard item that trips up masters and novices alike is a failed item, however impressive
it looks. A moderate item that masters get right and novices get wrong is excellent.
Difficulty is a means to discrimination, not a goal.

**Difficulty must come from the content, not the wording.** If the student is
struggling to work out *what is being asked*, you are measuring reading comprehension.

| Illegitimate difficulty — never use | Legitimate difficulty — use freely |
|---|---|
| Convoluted phrasing, long tangled stems | Applying the concept in a **novel context** not seen in the lecture |
| Marginal trivia from a slide footnote | Distinguishing **two adjacent concepts** that are easily confused |
| Linguistic traps, hidden double negatives | **Synthesis** across two or more units |
| Ambiguity — more than one defensible answer | Selecting the **right tool** among several that look applicable |
| Laborious calculation with no concept behind it | Judging the **strength** of an argument or evidence, not just classifying it |

**The defensibility test** for any hard item: if a sharp student objected that another
option is also correct, could you defend exactly one answer using the course materials?
If not, the item is **ambiguous, not difficult**. Rewrite or discard it.

Ambiguity punishes the strong student hardest: they see the edge cases and hesitate,
while the weak student picks confidently and lands on the key by luck. Ambiguity does
not raise difficulty — it inverts the measurement.

## 3. Cognitive level

Label every item's level explicitly: Remember / Understand / Apply / Analyse / Evaluate.

- University assessment lives at **Apply and above**. Cap Remember-level items at ~30%
  of any set, and use them as warm-up rather than as the target.
- Match the level the course's **past papers** actually test — no higher, no lower.
  Over-shooting wastes their time as surely as under-shooting.
- Use a scenario they have not seen. Reproducing the lecture's own example measures
  memory of the example, not understanding of the concept.

## 4. Anatomy of a multiple-choice item

Three components, each with its own standard.

**The stem** carries the full informational load and must be a complete, self-contained
question. Apply the **cover test**: cover the options — if the student cannot tell what
is being asked from the stem alone, the stem is incomplete. Keep the options short.

- Phrase positively. Avoid "which of the following is NOT…" unless necessary; if you
  must, make the negation visually prominent.
- Never use "all of the above" or "none of the above" — both are solvable with partial
  knowledge and corrupt the measurement.
- Four options is enough. A weak fifth option is worse than none.

**The key** must be correct beyond dispute and must carry no signal that reveals it.

**The distractors** are where the item is made or destroyed. See below.

## 5. Distractors — the six sources

> A good distractor is not a wrong option. It is a **real error that a student who has
> not mastered the concept actually makes.**

A distractor nobody chooses is a **dead option**: it lifts the guessing rate from 25% to
33% and weakens the item. Four options with one absurd choice is really a three-option
item.

Draw distractors from these sources:

| # | Source | What it looks like |
|---|---|---|
| 1 | **The student's actual errors** | From their marked assignments and the examiner's comments — the richest source available |
| 2 | **The wrong step in a procedure** | The result you'd get by applying step three incorrectly |
| 3 | **The adjacent concept** | The term routinely confused with this one |
| 4 | **The right rule in the wrong condition** | They know the rule but not *when* it applies |
| 5 | **A correct answer to a nearby question** | True in itself, but not the answer to *this* question |
| 6 | **The memorised slogan applied blindly** | Literal application of a general maxim where it does not hold |

Source 6 is the most diagnostically powerful — it exposes students who memorised phrases
without understanding them.

**Construction requirements:**

- **Homogeneity** — all options from the same category, in the same grammatical form, of
  similar length.
- **No absolutes** (always / never / all / none) — test-wise students eliminate them
  without knowing anything.
- **No overlap** — no option may logically subsume another.
- **Logical ordering** — order options numerically or chronologically, and don't let the
  key's position form a pattern.

## 6. Cues that give the answer away

Scan every finished item for these. Each one lets a student score without knowing the
material, which destroys discrimination:

- **Length cue** — the key is longer or more detailed than the distractors. The most
  common leak by far.
- **Absolutes in distractors** — see above.
- **Word repeat** — a word from the stem appears only in the key.
- **Grammatical mismatch** — only the key agrees grammatically with the stem.
- **Convergence** — the key shares elements with most distractors.
- **"All of the above"** — partial knowledge solves it.

## 7. Constructed-response and essay items

- The **command verb** determines the required structure. Choose it deliberately and
  never blur "explain" / "analyse" / "evaluate" / "compare" / "discuss".
- **Validity test:** if you cannot write a clear marking scheme for the question, the
  question is defective. Rewrite it until it is objectively markable.
- It should require **synthesis across more than one unit**, not recall of a single fact.
- It must be answerable within the time the real exam allocates to it.
- Give the student the marking criteria **after** their attempt, never before.

## 8. Difficulty calibration

Target items that a well-prepared student gets right roughly **50–70%** of the time. An
item everyone answers correctly, and an item nobody answers correctly, both measure
nothing and teach nothing.

## 9. Disclosure

Attach a compact tag to every question:

```
[المستوى المعرفي · الوحدة · ما يقيسه تحديدًا]
```

**The tag must not leak the key.** Name the *ability* being measured, never the concept
that is the answer. "يقيس: التعرّف على Simpson's paradox" hands the item to anyone who
knows the term — exactly the word-repeat cue §6 warns against. Write "يقيس: تفسير انعكاس
اتجاه العلاقة عند التجميع" instead: precise about the skill, silent about the key. If you
cannot describe the ability without naming the answer, move the whole tag to the reveal.

**When you have no course materials** you cannot know the real unit name, and inventing
one is a citation you made up. Write `الوحدة: —` or `(وحدة مفترضة: …)` and say once that
the mapping is yours, not their syllabus.

**After** the student answers — never before — reveal what each distractor represents.
Do not settle for "خطأ". Say which specific misconception that option encodes and why it
looked convincing. This is the entire diagnostic payoff of multiple choice; without it
the format is just a guessing game.

Showing the student how items are engineered is itself a strong learning move: someone
who understands how questions are built reads an exam paper with the designer's eye
instead of the examinee's.

## 10. Worked example

Illustration only. **Never serve either version to a student as an actual item**, even
when the topic matches what they asked for — its key and its distractor analysis are
published right here, so it measures nothing. Build a fresh scenario every time.

**✗ Poor version**

> ما تعريف الارتباط والسببية؟
> أ) الارتباط لا يعني السببية ✓ · ب) الارتباط يعني السببية دائمًا
> ج) لا يوجد فرق بينهما · د) جميع ما سبق

Fails everything: Remember level; any layperson answers it; dead distractors nobody
would pick; "all of the above"; and the key is simply the memorised slogan.

**✓ Academic version**

> دراسة على 400 موظف وجدت ارتباطًا موجبًا قويًا (r = 0.71) بين عدد ساعات التدريب
> التي تلقّاها الموظف وتقييم أدائه السنوي. أوصى تقرير الموارد البشرية بزيادة ساعات
> التدريب لرفع الأداء. ما **أقوى** اعتراض منهجي على هذا الاستنتاج؟
>
> أ) حجم العينة غير كافٍ لاستخلاص نتيجة موثوقة
> ب) قيمة r مرتفعة بدرجة تشير إلى خطأ في الحساب
> ج) المديرون قد يرشّحون الموظفين الأعلى أداءً أصلًا لبرامج التدريب ✓
> د) الارتباط الموجب لا يثبت وجود أي علاقة بين المتغيرين
>
> `[تقويم · وحدة مناهج البحث · يقيس: تمييز اتجاه السببية وتحيّز الاختيار]`

Distractor analysis, revealed only after the attempt:

| Option | Misconception it encodes | Source |
|---|---|---|
| أ | Reflexive attack on sample size; 400 is ample. Tests whether they assess the *actual* threat | 6 |
| ب | Reads correlation strength as an error signal — doesn't understand what `r` measures | 3 |
| **د** | Over-applies "correlation ≠ causation" into denying association exists at all. **Sharpest distractor** — catches slogan memorisation | 6 |
| ج | **Key** — reverse causality / selection bias | — |

All four are methodological objections (homogeneous), similar in length, the key is not
the longest, no absolutes, and elimination alone does not solve it.

---

# القسم 2 — Subject Modes


Different subjects fail in different ways, so the mastery cycle changes shape. Identify
the mode at Phase 1 and read only the matching section. Many courses are a mix — read
both relevant sections and run them together rather than alternating.

## Contents

1. Quantitative / problem-based
2. Memorisation-heavy
3. Analytical / essay-based
4. Applied / practical
5. The mixed mode (memorisation + analysis) — the hardest and most common

---

## 1. Quantitative / problem-based

*Mathematics, physics, engineering, accounting, statistics.*

The characteristic failure is a student who follows a worked solution, understands every
step, and then cannot start a blank problem. Recognition of a method is not possession
of it.

- **Never show a full solution first.** Give the problem, let them attempt it, and
  intervene only at the step where they stall.
- **Classify every error explicitly:** conceptual (wrong model chosen), procedural
  (right model, wrong execution), or reading (misparsed the question). The remedy is
  completely different for each, and students routinely misdiagnose their own errors as
  "careless" when they are conceptual.
- **Make them state the approach before calculating.** "Which method does this need, and
  why that one?" Most marks are lost in method selection, not arithmetic.
- **Interleave problem types.** Ten problems of the same type in a row teaches pattern
  matching, not selection. Mix types so they must choose the tool each time.
- **Train under time.** Speed is a separate skill from correctness and must be practised
  separately once accuracy is stable.
- After a correct solution, give an **equivalent problem with different numbers** to
  confirm it wasn't a fluke, and a **variant with one condition changed** to test
  whether the concept transferred.

## 2. Memorisation-heavy

*Medicine, biology, law, history, anatomy, classifications.*

The characteristic failure is enormous passive re-reading that produces recognition
without recall.

- **Sort the content into two visible categories:** what must be memorised verbatim
  (definitions, classifications, statutes, dates, criteria, names) and what must be
  understood and reproduced in the student's own words. Mixing these two is the single
  biggest waste of study time in this mode.
- **Elaborative interrogation.** After every fact, ask "why is this true?" and "how does
  it differ from the neighbouring case?" A connected fact is retrievable; an isolated
  one evaporates.
- **Mnemonics for lists**, built from the student's own material rather than imposed —
  then test them on both the key *and* its contents, never the key alone.
- **Explicit spaced schedule.** Re-test each block after 1 day, 3 days, 1 week, 2 weeks.
  Fix the dates in the state ledger; without dates, spacing does not happen.
- **Cued recall, not recognition.** Ask them to produce the item from a cue, not to pick
  it from a list.

## 3. Analytical / essay-based

*Management, economics, political science, philosophy, literature, law.*

The characteristic failure is an answer full of correct content that scores in the
middle band, because content was displayed rather than deployed in an argument.

- **Extract the rubric first** — see `marking.md`. Without it you are coaching blind.
- **Train one fixed structure:** clear position → specific evidence → *explanation of
  the link between the evidence and the position* → counter-argument and response →
  conclusion that answers the question in its own words.
- **The third step is where most students fall.** They present evidence and leave the
  reader to infer the connection. Making the link explicit is the single largest
  differentiator in the mark.
- **Teach the command verbs.** "Explain", "analyse", "evaluate", "compare", "discuss"
  demand different structures. An excellent answer to the wrong question scores in the
  middle.
- **Always practise under real time pressure.** Writing without time pressure measures
  nothing that the exam will measure.

## 4. Applied / practical

*Computer science, labs, design, clinical skills.*

The characteristic failure is a student who can describe the procedure fluently and
cannot execute it.

- Assess by **production, not description**. Have them build, run, or perform it.
- Give **graded exercises** where each adds exactly one new demand.
- **Review their artefact** against explicit criteria rather than discussing it in the
  abstract.
- Include **debugging exercises**: give them something broken and have them diagnose it.
  Diagnosis tests understanding far more sharply than construction does.

## 5. The mixed mode (memorisation + analysis)

*The most common combination in university, and the hardest to prepare for.*

Most students treat this as two separate tasks: first memorise, then write. That
sequencing is the reason capable students land on a B.

> **The governing principle: memorised content is ammunition for the argument, not an
> end in itself. An A answer is not the one that recalls the most — it is the one that
> *deploys* recall as evidence inside a structure. A student who memorises without
> knowing where to fire what they know writes an answer that is full and empty at once.**

Run sections 2 and 3 together, plus this binding step:

- **For every fact memorised, ask immediately: "في أي سؤال مقالي تصلح هذه دليلًا؟"**
  Do not mark the fact as mastered until they answer.
- **At the end of every unit, require an evidence bank:** 5–7 memorised items from the
  unit, each paired with a plausible essay question it would serve as evidence in. This
  bank is what they will actually write from in the exam hall.
- Track the bank's growth in the state ledger. A large memorised set with a thin
  evidence bank is the warning sign that they are studying the two halves separately
  again.

---

# القسم 3 — Marking


Read before marking any essay or long-form answer. Marking without an explicit criterion
produces encouragement, not information, and encouragement does not raise a grade.

## 1. Get the rubric before you mark

In order of preference:

1. **The official rubric**, if the student has it.
2. **Reverse-engineered from past papers and model answers** — the most reliable route
   in practice. Read what the model answers actually contain, in what order, at what
   depth, and infer the weighting from it.
3. **Inferred from the mark distribution and command verbs**, if neither exists.

When you infer rather than read a rubric, say so plainly and ask the student to verify
it with their lecturer. An inferred rubric you present as fact can send them in a
confidently wrong direction for weeks.

## 2. Command verbs and their structures

The verb sets the shape of the answer. Marking an "evaluate" answer as if it were
"explain" rewards the wrong thing.

| Verb | What earns marks |
|---|---|
| **اشرح / Explain** | Mechanism and causation — *how* and *why*, not *what* |
| **حلّل / Analyse** | Decomposition into components and the relationships between them |
| **قيّم / Evaluate** | A judgement, with criteria stated, weighing both sides |
| **قارن / Compare** | Explicit dimensions of comparison, applied to both sides symmetrically |
| **ناقش / Discuss** | Multiple positions represented fairly, then a reasoned stance |
| **بررّ / Justify** | One position defended against the strongest objection to it |

An excellent answer to the wrong verb scores in the middle band. Check the verb before
anything else, and teach the student to do the same.

## 3. The answer structure to train

1. **Position** — a clear, direct claim that answers the question asked.
2. **Evidence** — specific, from their memorised material; named, dated, cited as their
   course does it.
3. **The link** — an explicit sentence explaining *why this evidence supports this
   position*.
4. **Counter-argument and response** — the strongest objection, and why the position
   survives it.
5. **Conclusion** — answers the question in its own words, adding no new material.

**Step 3 is where most marks are lost.** Students place evidence next to a claim and
leave the examiner to infer the connection. Examiners do not award inferred reasoning.
When marking, check for this step specifically — its absence is usually the single
largest recoverable loss on the page.

## 4. How to mark

Mark **criterion by criterion**, never as a global impression. For each criterion give
the estimated mark and the specific reason for it.

```
| المعيار | الوزن | تقديرك | السبب المحدد |
```

Then close with two things:

- **الجملة الواحدة**: the single sentence that, if added, would raise the mark more than
  any other change. One sentence, specific, insertable — not a general suggestion.
- **الدرجة التقديرية** with the band it falls in and what separates it from the band above.

## 5. Feedback rules

- **Be accurate, not kind.** A weak answer must be named as weak, with the reason.
  Comfortable feedback costs the student marks they could have recovered.
- **Distinguish "wrong" from "correct but unrewarded".** Much lost credit is content
  that is true but does not answer the question asked. The remedy is completely
  different from the remedy for an error.
- **Point to the recoverable marks first.** Rank feedback by how many marks it would
  recover per unit of effort, not by where the errors appear on the page.
- **Never rewrite the answer for them.** Show what is missing and where; let them write
  it. Rewriting produces a good essay and no learning, and it is not theirs to submit.

---

# القسم 4 — State Ledger


Output this at the end of every session, filled in. You do not remember between
conversations — this ledger is what turns disconnected sessions into one continuous
course. Without it, spaced review and error tracking cannot happen at all.

Tell the student to keep it and paste it back at the start of the next session. If the
skill is running inside a project where files persist, save it there instead and update
it in place.

Emit it exactly in this shape, in Arabic:

```
═══ سجل الحالة ═══
المقرر:
التاريخ:

■ الوحدات
  مُتقنة:
  قيد العمل:
  لم تُبدأ:

■ الأخطاء المتكررة  (تُعاد في الجلسة القادمة)
  1.
  2.

■ المراجعة المتباعدة المستحقة  (بالتاريخ)
  | الوحدة | آخر اختبار | المراجعة القادمة |

■ بنك الأدلة
  عدد المعلومات المربوطة بأسئلة مقالية:
  الوحدات التي بنكها ما زال فارغًا:

■ فجوة المعايرة
  (ثقة مرتفعة على إجابات خاطئة / ثقة منخفضة على إجابات صحيحة / دقيقة)

■ الدرجة التقديرية لو كان الامتحان غدًا:
  السبب:

■ مهمة ما قبل الجلسة القادمة:

■ ابدأ الجلسة القادمة بـ:
═══════════════════
```

## Notes on filling it

- **الأخطاء المتكررة** — only errors that appeared more than once, or once with high
  confidence. A single low-confidence slip is not a pattern.
- **المراجعة المتباعدة** — real dates, not intervals. "بعد أسبوع" does not get done;
  "الأحد 14 سبتمبر" does.
- **بنك الأدلة** — flag units whose bank is still empty. That is the signal the student
  has slipped back into memorising and analysing as two separate activities.
- **فجوة المعايرة** — the most important line for a student who keeps underperforming
  relative to how prepared they feel. High confidence on wrong answers is the pattern to
  name explicitly and repeatedly.
- **الدرجة التقديرية** — give a real estimate with its reason, even when it is
  uncomfortable. A student who does not know where they stand cannot allocate their
  remaining time.
