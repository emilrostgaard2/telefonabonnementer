#!/usr/bin/env python3
"""Kvalitetstjek af det byggede site: links, h-tags, meta, schema, billeder, rester af shortcodes."""
import os, re, json, glob, html
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
pages = [p for p in glob.glob(f"{ROOT}/**/index.html", recursive=True) if "/go/" not in p and "/_build/" not in p]
existing = {"/" + os.path.relpath(os.path.dirname(p), ROOT).replace(".", "").strip("/") + "/" for p in pages}
existing = {e.replace("//", "/") for e in existing}
problems = 0
def bad(page, msg):
    global problems; problems += 1; print(f"  ✗ {page}: {msg}")
titles, descs = {}, {}
for p in sorted(pages):
    rel = "/" + os.path.relpath(os.path.dirname(p), ROOT).strip(".").strip("/") + "/"
    rel = rel.replace("//", "/")
    s = open(p, encoding="utf-8").read()
    t = html.unescape(re.search(r"<title>(.*?)</title>", s).group(1)); d = html.unescape(re.search(r'<meta name="description" content="(.*?)">', s).group(1))
    if not 30 <= len(t) <= 62: bad(rel, f"title længde {len(t)}: {t}")
    if not 110 <= len(d) <= 160: bad(rel, f"description længde {len(d)}")
    if t in titles: bad(rel, f"dublet title med {titles[t]}")
    if d in descs: bad(rel, f"dublet description med {descs[d]}")
    titles[t] = rel; descs[d] = rel
    if s.count("<h1") != 1: bad(rel, f"{s.count('<h1')} h1")
    heads = [int(x) for x in re.findall(r"<h([1-6])[ >]", re.sub(r"<footer.*?</footer>", "", s, flags=re.S))]
    for a, b in zip(heads, heads[1:]):
        if b > a + 1: bad(rel, f"h-spring h{a}->h{b}"); break
    if s.count("<h2") < 3 and rel not in ("/kontakt/", "/cookies/"): bad(rel, "få h2")
    for leftover in ("[[", "]]", "{maaned}", "{fra:", "{aar}"):
        if leftover in s: bad(rel, f"rest: {leftover}")
    ids = re.findall(r' id="([^"]+)"', s)
    dup = {i for i in ids if ids.count(i) > 1}
    if dup: bad(rel, f"dublet-id {dup}")
    for a in re.findall(r'href="#([^"]+)"', s):
        if a not in ids: bad(rel, f"anker mangler #{a}")
    for h in set(re.findall(r'href="(/[^"#?]*)"', s)):
        if h.startswith("/go/") or h.startswith("/assets/") or h in ("/favicon.ico", "/favicon.svg", "/apple-touch-icon.png", "/site.webmanifest"): continue
        if h not in existing: bad(rel, f"død intern link {h}")
    for src in set(re.findall(r'src="(/[^"?]+)', s)):
        if not os.path.exists(ROOT + src): bad(rel, f"billede mangler {src}")
    for m in re.findall(r'<script type="application/ld\+json">(.*?)</script>', s, re.S):
        try: json.loads(m)
        except Exception as e: bad(rel, f"schema JSON fejl {e}")
    for img in re.findall(r"<img [^>]*>", s):
        if "alt=" not in img or "width=" not in img: bad(rel, f"img uden alt/width {img[:80]}")
    ext = re.findall(r'<a href="https?://(?!telefonabonnementer)[^"]+"[^>]*>', s)
    for a in ext:
        if "rel=" not in a: bad(rel, f"ekstern link uden rel {a[:90]}")
    size = len(s.encode())
    if size > 260000: bad(rel, f"stor HTML {size//1024} KB")
print(f"{len(pages)} sider tjekket · {problems} problemer")
