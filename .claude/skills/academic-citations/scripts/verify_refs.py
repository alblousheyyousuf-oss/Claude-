#!/usr/bin/env python3
"""Check that each reference in a list exists, using the public Crossref API.

    python3 verify_refs.py references.txt          # one reference per paragraph/line
    python3 verify_refs.py report.md               # reads the References / المراجع section
    python3 verify_refs.py report.md --json out.json

For every reference it reports one of:

    VERIFIED   Crossref has a work whose title, first author and year match.
    CHECK      A close match exists but something differs: possibly a
               "chimeric" reference (real title, wrong authors or year) or a
               slightly altered one. Open the record and compare by hand.
    NOT FOUND  No matching work. Either it does not exist, or Crossref does
               not index it (books without DOIs, websites, local journals).
    MANUAL     Not checkable here: Arabic-script references, web pages and
               entries without a title. Verify in the source itself.

A VERIFIED result means the work exists with that metadata. It does NOT mean
the work supports the sentence citing it; only reading the source shows that.

Only the reference strings are sent to api.crossref.org; nothing else from the
report leaves the machine. Standard library only.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from difflib import SequenceMatcher
from pathlib import Path

API = "https://api.crossref.org/works"
UA = "university-report-skill/1.0 (reference existence check)"
ARABIC = re.compile(r"[؀-ۿ]")
DOI = re.compile(r"10\.\d{4,9}/[^\s\"<>]+", re.I)
YEAR = re.compile(r"\b(1[89]\d{2}|20\d{2})\b")
REF_HEADINGS = re.compile(
    r"^#{1,4}\s+(?:\d+(?:\.\d+)*\.?\s+)?(references|reference list|bibliography|works cited|"
    r"المراجع|قائمة المراجع|المصادر والمراجع|المصادر|المراجع والمصادر)\s*(\{.*\})?\s*$",
    re.I | re.M)


def norm(text):
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"<[^>]+>", " ", text)          # Crossref titles may carry <i> tags
    return re.sub(r"[^\w]+", " ", text.casefold()).strip()


def read_references(path):
    text = Path(path).read_text(encoding="utf-8")
    m = REF_HEADINGS.search(text)
    if m:
        level = len(text[m.start():].split()[0])
        rest = text[m.end():]
        stop = re.search(rf"^#{{1,{level}}}\s+(?!.*(?:المراجع|references))", rest, re.M | re.I)
        text = rest[:stop.start()] if stop else rest
    refs = []
    for block in re.split(r"\n\s*\n", text):
        for line in block.splitlines():
            line = line.strip()
            if not line or line.startswith(("#", "<!--")):
                continue
            line = re.sub(r"^[-*+]\s+|^\d+[.)]\s+", "", line)
            if len(line) > 25:
                refs.append(line)
    return refs


def guess_title(ref):
    """Pull the title out of APA/Harvard/IEEE/MLA-shaped references."""
    clean = ref.replace("*", "")
    m = re.search(r"[“\"‘']([^”\"’']{10,})[”\"’']", clean)            # IEEE, MLA, Harvard
    if m:
        return m.group(1).strip(" ,.")
    m = re.search(r"\(\s*(?:\d{4}[a-z]?|n\.d\.)[^)]*\)\.?\s*(.+?)(?:\.\s|\?\s|$)", clean)  # APA
    if m:
        return m.group(1).strip(" ,.")
    return None


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if e.code == 429 and attempt < 2:
                time.sleep(3 * (attempt + 1))
                continue
            raise
        except urllib.error.URLError:
            if attempt < 2:
                time.sleep(2)
                continue
            raise
    return None


def item_year(item):
    for key in ("published-print", "published-online", "issued", "created"):
        parts = (item.get(key) or {}).get("date-parts") or [[None]]
        if parts and parts[0] and parts[0][0]:
            return int(parts[0][0])
    return None


def describe(item):
    authors = item.get("author") or []
    first = authors[0].get("family", authors[0].get("name", "")) if authors else ""
    title = (item.get("title") or [""])[0]
    venue = (item.get("container-title") or [""])[0]
    return {"title": re.sub(r"<[^>]+>", "", title), "first_author": first,
            "year": item_year(item), "venue": venue, "doi": item.get("DOI", "")}


def score(ref, item):
    found = describe(item)
    title = guess_title(ref)
    t_ref, t_cr = norm(title or ref), norm(found["title"])
    if not t_cr:
        return 0.0, found, {}
    if title:
        title_sim = SequenceMatcher(None, t_ref, t_cr).ratio()
    else:                              # no title parsed: containment in the whole string
        words = t_cr.split()
        title_sim = sum(w in t_ref.split() for w in words) / max(1, len(words))
    years = {int(y) for y in YEAR.findall(ref)}
    year_ok = found["year"] in years or (found["year"] and any(abs(found["year"] - y) == 1 for y in years))
    author_ok = bool(found["first_author"]) and norm(found["first_author"]) in norm(ref)
    return title_sim, found, {"year": bool(year_ok), "author": author_ok}


def classify(ref):
    if ARABIC.search(ref):
        return ("MANUAL", "Arabic-script reference: Crossref coverage is poor; check the "
                "publisher, Dar Almandumah, Al Manhal or the library catalogue", None)
    doi = DOI.search(ref)
    title = guess_title(ref)
    if doi:
        d = doi.group(0).rstrip(".,;)")
        data = fetch(f"{API}/{urllib.parse.quote(d)}")
        if not data:
            return "NOT FOUND", f"DOI {d} does not resolve in Crossref", None
        sim, found, ok = score(ref, data["message"])
        if sim >= 0.85 and ok.get("author") and ok.get("year"):
            return "VERIFIED", "DOI resolves and title/author/year match", found
        return "CHECK", (f"DOI exists but belongs to a work that differs "
                         f"(title {sim:.0%}, author {'ok' if ok.get('author') else 'differs'}, "
                         f"year {'ok' if ok.get('year') else 'differs'})"), found
    if not title and re.search(r"https?://", ref):
        return "MANUAL", "web page without DOI: open the URL and check author, date and title", None
    if not title:
        return "MANUAL", "could not identify a title in this entry", None
    q = urllib.parse.urlencode({"query.bibliographic": ref.replace("*", "")[:300], "rows": 5})
    data = fetch(f"{API}?{q}")
    items = (data or {}).get("message", {}).get("items", [])
    best = max((score(ref, it) for it in items), key=lambda s: s[0], default=(0, None, {}))
    sim, found, ok = best
    if found and sim >= 0.9 and ok.get("author") and ok.get("year"):
        return "VERIFIED", "title, first author and year match a Crossref record", found
    if found and sim >= 0.75:
        return "CHECK", (f"closest record: title {sim:.0%}, author "
                         f"{'ok' if ok.get('author') else 'differs'}, year "
                         f"{'ok' if ok.get('year') else 'differs'}"), found
    if re.search(r"https?://", ref):
        return ("MANUAL", "no Crossref record; it has a URL, so open it and check author, "
                "date and title against the page", found)
    return ("NOT FOUND", "no close Crossref record (books without DOI and local journals "
            "are often missing)", found)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("file", type=Path, help=".md/.txt with a references list")
    ap.add_argument("--json", type=Path, help="also write results as JSON")
    ap.add_argument("--delay", type=float, default=1.0, help="seconds between requests")
    args = ap.parse_args(argv)

    refs = read_references(args.file)
    if not refs:
        sys.exit("no references found (expected a References / المراجع heading or one entry per line)")
    results = []
    for i, ref in enumerate(refs, 1):
        try:
            status, why, found = classify(ref)
        except Exception as exc:          # network failure: never report as verified
            status, why, found = "ERROR", f"lookup failed: {exc}", None
        results.append({"n": i, "status": status, "reason": why, "reference": ref, "match": found})
        short = ref if len(ref) < 90 else ref[:87] + "..."
        print(f"[{i:>2}] {status:<9} {short}")
        print(f"      {why}")
        if found and status != "VERIFIED":
            print(f"      closest: {found['first_author']} ({found['year']}). {found['title']}. "
                  f"{found['venue']} doi:{found['doi']}")
        time.sleep(args.delay)
    counts = {}
    for r in results:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    print("\nsummary: " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())))
    if args.json:
        args.json.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
