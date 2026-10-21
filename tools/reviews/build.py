#!/usr/bin/env python3
"""Write the review carousel into every page that should carry it.

Source of truth: reviews.json at the repo root. Run from anywhere:
    python3 tools/reviews/build.py

The carousel HTML on each page sits between <!-- reviews:start --> and
<!-- reviews:end --> and is rewritten on every run. Pages that do not yet carry
the carousel CSS and script (the landing pages) get them as marked blocks:
    /* reviews-css:start */ ... /* reviews-css:end */
    <!-- reviews-js:start --> ... <!-- reviews-js:end -->
"""
import glob
import html
import json
import os
import re
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HERE = os.path.join(ROOT, "tools", "reviews")


def read(name):
    with open(os.path.join(HERE, name), encoding="utf-8") as f:
        return f.read().strip()


DATA = json.load(open(os.path.join(ROOT, "reviews.json"), encoding="utf-8"))
CSS, JS, STARS = read("reviews.css"), read("reviews.js"), read("stars.html")
LEGACY_SECTION = re.compile(r'<section class="[^"]*revs-section[^"]*"[^>]*>.*?</section>', re.S)

NAV = (
    '<div class="rv-nav"><button class="rv-btn" id="rv-prev" type="button" aria-label="Previous reviews" aria-controls="rv-rail">'
    '<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path d="M15 5l-8 7 8 7" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/></svg></button>'
    '<button class="rv-btn" id="rv-next" type="button" aria-label="More reviews" aria-controls="rv-rail">'
    '<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path d="M9 5l8 7-8 7" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/></svg></button></div>'
)


def label(iso):
    return date.fromisoformat(iso).strftime("%b %Y")


def card(r, clone=False):
    if r.get("avatar"):
        av = f'<img class="rv-face" src="{r["avatar"]}" alt="" width="40" height="40" loading="lazy" decoding="async">'
    else:
        av = f'<span class="rv-initial" aria-hidden="true">{html.escape(r["author"][0].upper())}</span>'
    return (
        f'<article class="rv-card" tabindex="{-1 if clone else 0}">{STARS}'
        f'<p class="rv-quote">{html.escape(r["text"])}</p><div class="rv-meta">{av}'
        f'<span class="rv-who"><span class="rv-author">{html.escape(r["author"])}</span>'
        f'<span class="rv-sub">{label(r["date"])} / {r["source"]}</span></span></div></article>'
    )


def section(cls):
    revs = DATA["reviews"]
    cards = "".join(card(r) for r in revs)
    clones = "".join(card(r, True) for r in revs)
    more = (f'<p class="rv-more"><a href="{DATA["profile_url"]}" target="_blank" rel="noopener">'
            f'{html.escape(DATA["profile_label"])}</a></p>') if DATA.get("profile_url") else ""
    return (
        f'<section class="{cls}" id="reviews"><div class="wrap"><p class="eyebrow">Reviews</p>'
        '<h2>What boat owners say.</h2><div class="rv-head"><div class="rv-score">'
        f'{STARS}<span class="rv-sub">{html.escape(DATA["rating_label"])}</span></div>{NAV}</div>'
        '<div class="rv-rail" id="rv-rail" tabindex="0" role="region" aria-label="Customer reviews, scroll horizontally">'
        f'{cards}<div class="rv-clones" id="rv-clones" aria-hidden="true" style="display:contents">{clones}</div>'
        f'</div>{more}</div></section>'
    )


def marked(cls):
    return f"<!-- reviews:start -->{section(cls)}<!-- reviews:end -->"


def lp_class(s, pos):
    opens = re.findall(r"<section(?: class=\"([^\"]*)\")?", s[:pos])
    prev = (opens[-1] or "").split() if opens else []
    return "revs-section" if ("condition" in prev or "bg-mist" in prev) else "bg-mist revs-section"


def build():
    n = 0
    for rel in sorted(glob.glob("**/index.html", root_dir=ROOT, recursive=True)):
        p = os.path.join(ROOT, rel)
        s = open(p, encoding="utf-8").read()
        before = s
        m = re.search(r"<!-- reviews:start --><section class=\"([^\"]*)\".*?<!-- reviews:end -->", s, re.S)
        if m:
            s = s[:m.start()] + marked(m.group(1)) + s[m.end():]
        elif LEGACY_SECTION.search(s):
            lm = LEGACY_SECTION.search(s)
            cls = re.match(r'<section class="([^"]*)"', lm.group(0)).group(1)
            s = s[:lm.start()] + marked(cls) + s[lm.end():]
        elif rel.startswith("lp/"):
            pos = s.rindex("<section", 0, s.index("<footer"))
            s = s[:pos] + marked(lp_class(s, pos)) + "\n" + s[pos:]
        else:
            continue
        if "/* Review scroller." not in s:
            s = s.replace("</style>", f"\n/* reviews-css:start */\n{CSS}\n/* reviews-css:end */\n</style>", 1)
        else:
            s = re.sub(r"/\* reviews-css:start \*/.*?/\* reviews-css:end \*/",
                       lambda _: f"/* reviews-css:start */\n{CSS}\n/* reviews-css:end */", s, flags=re.S)
        if "getElementById('rv-rail')" not in s:
            s = s.replace("</body>", f"<!-- reviews-js:start -->\n{JS}\n<!-- reviews-js:end -->\n</body>", 1)
        else:
            s = re.sub(r"<!-- reviews-js:start -->.*?<!-- reviews-js:end -->",
                       lambda _: f"<!-- reviews-js:start -->\n{JS}\n<!-- reviews-js:end -->", s, flags=re.S)
        if s != before:
            open(p, "w", encoding="utf-8").write(s)
        n += 1
    print(f"reviews: {len(DATA['reviews'])} reviews on {n} pages")


if __name__ == "__main__":
    build()
