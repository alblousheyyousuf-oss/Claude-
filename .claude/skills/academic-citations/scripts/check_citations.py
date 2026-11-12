#!/usr/bin/env python3
"""Cross-check in-text citations against the reference list of a Markdown report.

    python3 check_citations.py report.md

Works offline. Detects the style from the reference list:

  author-date (APA, Harvard, Chicago author-date), Arabic or English:
      (Smith, 2020) · (Smith & Lee, 2020, p. 4) · Smith et al. (2021)
      (العتيبي، 2020، ص 15) · (العتيبي والشمري، 2019) · العتيبي (2020)
  numeric (IEEE, Vancouver):  [1] · [2], [5] · [3]–[6] · [1, 4]

Reports
  - citations with no matching reference, and references never cited;
  - duplicate entries, and same author + year without a/b suffixes;
  - author-date lists that are not alphabetical, numeric lists whose numbers
    do not follow the order of first citation;
  - placeholders still in the text ([CITATION NEEDED], [مرجع مطلوب] …).

Heuristic by nature: read every finding before acting on it. MLA (author-page
citations) is not supported.
"""
from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from pathlib import Path

REF_HEAD = re.compile(
    r"^(#{1,4})\s+(?:\d+(?:\.\d+)*\.?\s+)?(references|reference list|bibliography|works cited|"
    r"المراجع|قائمة المراجع|المصادر والمراجع|المصادر|المراجع والمصادر)\s*(\{.*\})?\s*$", re.I)
PLACEHOLDER = re.compile(r"\[(?:CITATION NEEDED|DATA NEEDED[^\]]*|مرجع مطلوب|بيانات مطلوبة[^\]]*|"
                         r"من تجربتك[^\]]*|PLACEHOLDER[^\]]*)\]", re.I)
YEAR_TOKEN = r"(?:\d{4}[a-z]?|n\.d\.|د\.\s?ت\.?|in press|قيد النشر)"
ARABIC = re.compile(r"[؀-ۿ]")


def norm(s):
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c)).casefold()
    s = re.sub("[أإآ]", "ا", s)
    return re.sub(r"[^\w]", "", s)


def sort_key(s):
    s = norm(s)
    return s[2:] if s.startswith("ال") else s          # Arabic: ignore the article


def split_report(text):
    if text.startswith("---"):
        end = re.search(r"^---\s*$", text[3:], re.M)
        if end:
            text = text[3 + end.end():]
    lines = text.splitlines()
    body, refs, in_refs, level = [], [], False, 0
    for no, line in enumerate(lines, 1):
        h = re.match(r"^(#{1,6})\s+", line)
        m = REF_HEAD.match(line.strip())
        if m:
            in_refs, level = True, len(m.group(1))
            refs.append((no, "#SECTION"))
            continue
        if in_refs and h and len(h.group(1)) <= level:
            in_refs = False
        if in_refs:
            if h:
                refs.append((no, "#SECTION"))
            elif line.strip() and not line.strip().startswith("<!--"):
                refs.append((no, re.sub(r"^[-*+]\s+", "", line.strip())))
        else:
            body.append((no, line))
    return body, refs


def ref_key(entry):
    clean = entry.replace("*", "")
    authors = re.split(r"\s*\(", clean, maxsplit=1)[0]
    first = re.split(r"[,،.]", authors)[0].strip()
    y = re.search(rf"\(\s*({YEAR_TOKEN})", clean, re.I)
    return first, (y.group(1) if y else None)


def first_name_token(names):
    names = re.sub(r"\[[^\]]+\]", "", names)                       # [WHO]
    names = re.sub(r"\b(e\.g\.|see|see also|cf\.)\s*", "", names, flags=re.I)
    names = re.sub(r"^(انظر|راجع)\s+", "", names.strip())
    first = re.split(r"\s+(?:&|and|et al\.?)\s*|\s+وآخرون|\s+و(?=[؀-ۿ])|[,،]", names.strip())[0]
    return first.strip()


def body_citations(body):
    """Return [(line, surname, year)] and the group-author aliases [ABBR] -> full name."""
    cites, aliases = [], {}
    text_lines = [(no, re.sub(r"`[^`]*`", "", line)) for no, line in body]
    for no, line in text_lines:
        for full, abbr in re.findall(r"([A-Z][\w .&'-]+?)\s*\[([A-Z]{2,})\]", line):
            aliases[norm(abbr)] = full.strip()
    for no, line in text_lines:
        for group in re.findall(r"\(([^()]*?" + YEAR_TOKEN + r"[^()]*)\)", line, re.I):
            for part in re.split(r"[;؛]", group):
                part = part.strip()
                cited_in = re.search(r"(?:as cited in|نقلاً عن|نقلا عن)\s+(.*)", part, re.I)
                if cited_in:
                    part = cited_in.group(1)
                m = re.match(rf"(.+?)[,،]\s*({YEAR_TOKEN}(?:\s*[,،]\s*{YEAR_TOKEN})*)", part, re.I)
                if not m or re.fullmatch(r"[\d\s–\-]+", m.group(1)):
                    continue
                name = first_name_token(m.group(1))
                if not name or len(name) < 2:
                    continue
                for y in re.findall(YEAR_TOKEN, m.group(2), re.I):
                    cites.append((no, name, y))
        for name, y in re.findall(
                r"([A-Z][\w'’-]+|[؀-ۿ]{3,})(?:\s+(?:et al\.|and [A-Z][\w'’-]+|& [A-Z][\w'’-]+|"
                r"وآخرون|و[؀-ۿ]+))?\s+\((" + YEAR_TOKEN + r")(?:[,،][^)]*)?\)", line, re.I):
            cites.append((no, name, y, "narrative"))
    return cites, aliases


def check_author_date(body, refs, out):
    entries = [(no, e) for no, e in refs if e != "#SECTION"]
    keys, authors = {}, []
    for no, e in entries:
        first, year = ref_key(e)
        k = (norm(first.split()[0]) if first else "", year)
        keys.setdefault(k, []).append((no, e))
        authors.append((norm(re.split(r"\s*\(", e.replace("*", ""), maxsplit=1)[0]), year, k))
    first_words = {k[0] for k in keys}
    cites, aliases = body_citations(body)
    cited = set()
    missing = []
    for c in cites:
        no, name, year = c[0], c[1], c[2]
        narrative = len(c) > 3
        nk = norm(name)
        if nk in aliases:
            name = aliases[nk]
        nk = norm(name.split()[0])
        k = (nk, year)
        if k not in keys:            # "… Psychological Association (2020)": a later word of the name
            k = next((key for a, y, key in authors if y == year and norm(name) in a), k)
        if k in keys:
            cited.add(k)
        elif narrative and nk not in first_words and (ARABIC.search(name) or not name[0].isupper()):
            continue                 # an Arabic word before a year, not a name
        else:
            missing.append((no, name, year))
    out.append(("Citations with no matching reference", [f"line {no}: {n} ({y})" for no, n, y in missing]))
    out.append(("References never cited in the text",
                [f"line {e[0][0]}: {e[0][1][:90]}" for k, e in keys.items() if k not in cited]))
    out.append(("Duplicate references (same first author and year)",
                [f"lines {', '.join(str(x[0]) for x in e)}: {e[0][1][:70]}" for k, e in keys.items()
                 if len(e) > 1]))
    # alphabetical order within each sub-section
    disorder, prev, section = [], None, 0
    for no, e in refs:
        if e == "#SECTION":
            prev, section = None, section + 1
            continue
        k = sort_key(ref_key(e)[0])
        if prev and k < prev[0]:
            disorder.append(f"line {no}: «{e[:40]}» should come before line {prev[1]}")
        prev = (k, no)
    out.append(("Reference list not alphabetical", disorder))


def check_numeric(body, refs, out):
    numbers = {}
    for no, e in refs:
        m = re.match(r"\[(\d+)\]", e)
        if m:
            numbers.setdefault(int(m.group(1)), []).append(no)
    order, cited = [], set()
    for no, line in body:
        line = re.sub(r"\[(\d+)\]\s*[–-]\s*\[(\d+)\]",
                      lambda m: "[" + ",".join(map(str, range(int(m.group(1)), int(m.group(2)) + 1))) + "]",
                      line)
        for grp in re.findall(r"\[(\d+(?:\s*[–,-]\s*\d+)*)\]", line):
            for part in re.split(r"\s*,\s*", grp):
                if re.search(r"[–-]", part):
                    a, b = map(int, re.split(r"\s*[–-]\s*", part))
                    nums = range(a, b + 1)
                else:
                    nums = [int(part)]
                for n in nums:
                    if n not in cited:
                        order.append((no, n))
                    cited.add(n)
    out.append(("Citations with no matching reference",
                [f"line {no}: [{n}]" for no, n in order if n not in numbers]))
    out.append(("References never cited in the text",
                [f"line {numbers[n][0]}: [{n}]" for n in sorted(numbers) if n not in cited]))
    out.append(("Duplicate reference numbers", [f"[{n}] on lines {v}" for n, v in numbers.items() if len(v) > 1]))
    expected = [n for _, n in order if n in numbers]
    out.append(("Numbers not in order of first citation (IEEE numbers by first appearance)",
                [f"first citations appear as {expected[:15]}"] if expected != sorted(expected) else []))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("report", type=Path)
    args = ap.parse_args(argv)
    text = args.report.read_text(encoding="utf-8")
    body, refs = split_report(text)
    entries = [e for _, e in refs if e != "#SECTION"]
    if not entries:
        sys.exit("no reference list found under a References / المراجع heading")
    numeric = sum(bool(re.match(r"\[\d+\]", e)) for e in entries) > len(entries) / 2
    out = []
    (check_numeric if numeric else check_author_date)(body, refs, out)
    holders = [f"line {no}: {m}" for no, line in body for m in PLACEHOLDER.findall(line)]
    out.append(("Placeholders still in the text (must be resolved before submission)", holders))

    print(f"style: {'numeric' if numeric else 'author-date'} · references: {len(entries)}")
    problems = 0
    for title, items in out:
        mark = "OK " if not items else "!! "
        print(f"\n{mark}{title}: {len(items)}")
        for it in items[:40]:
            print(f"    {it}")
        problems += len(items)
    print(f"\n{'clean' if not problems else f'{problems} finding(s) to review'}")


if __name__ == "__main__":
    main()
