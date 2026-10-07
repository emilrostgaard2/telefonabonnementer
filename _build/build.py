#!/usr/bin/env python3
"""Statisk site-generator for telefonabonnementer.dk.
Kør:  python3 _build/build.py      (fra repo-roden eller fra _build)
Output skrives til repo-roden (ved siden af _build/).
"""
import json, re, os, html, shutil, datetime, hashlib, glob
from urllib.parse import quote

B = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(B)
ROOT = os.environ.get("OUT_DIR") or os.path.join(REPO, "public")  # færdigt site bygges hertil
SITE = "https://telefonabonnementer.dk"
BRAND = "Telefonabonnementer.dk"
KEEP = {"_build", ".github", ".git", "README.md", ".gitignore", "LICENSE"}

MONTHS = ["januar","februar","marts","april","maj","juni","juli","august","september","oktober","november","december"]
TODAY = datetime.date.today()
if os.environ.get("BUILD_DATE"):
    TODAY = datetime.date.fromisoformat(os.environ["BUILD_DATE"])

PROV = json.load(open(f"{B}/data/providers.json", encoding="utf-8"))
PROV = {k: v for k, v in PROV.items() if not k.startswith("_")}
PD = json.load(open(f"{B}/data/plans.json", encoding="utf-8"))
PLANS = PD["plans"]
CHECKED = datetime.date.fromisoformat(PD["checked"])
MODIFIED = max(CHECKED, datetime.date.fromisoformat(PD.get("content_updated", PD["checked"])))  # vises som "Opdateret" – ændres kun når priser/indhold faktisk ændres
ENDS = {p["id"]: p["ends"] for p in PLANS if p.get("ends")}
NETKEY = {"TDC NET": "tdc", "3 (Hi3G)": "3"}

def netkey(p): return NETKEY.get(PROV[p]["network"], "tt")
def netshort(p): return {"tdc": "TDC NET", "3": "3's net", "tt": "TT-netværket"}[netkey(p)]
def dk_date(d): return f"{d.day}. {MONTHS[d.month-1]} {d.year}"
def dk_short(d): return f"{d.day}. {MONTHS[d.month-1][:3]}. {d.year}"
MAANED = f"{MONTHS[TODAY.month-1]} {TODAY.year}"
E = html.escape

# ---------- plan helpers ----------
def is_kid(p): return p["name"].startswith("Børn")
def plans_for(tag, kids=None):
    if kids is None: kids = tag == "boern" or tag.startswith("udbyder-")
    return [p for p in _plans_for(tag) if kids or not is_kid(p)]
def _plans_for(tag):
    if tag in ("alle", ""): return list(PLANS)
    if tag.startswith("udbyder-"):
        pid = tag[8:]
        pid = {"lyca-mobile": "lyca"}.get(pid, pid)
        return [p for p in PLANS if p["p"] == pid]
    if tag == "5g": return [p for p in PLANS if p["g5"]]
    if tag == "fri-tale": return [p for p in PLANS if p["talk"] == "fri"]
    return [p for p in PLANS if tag in p["tags"]]

def fra(tag):
    ps = plans_for(tag, kids=(tag == "boern"))
    if tag == "tilbud" and ps: return min(p.get("intro", p["price"]) if p.get("intro") else p["price"] for p in ps)
    return min(p["price"] for p in ps) if ps else min(p["price"] for p in PLANS)

def gbv(p): return 100000 if p["gb"] is None else p["gb"]
def gbtxt(p): return "Fri data" if p["gb"] is None else f'{p["gb"]:,} GB'.replace(",", ".")
def talktxt(p): return "Fri tale" if p["talk"] == "fri" else f'{p["talk"]} tale'
def kr(n): return f"{n:,} kr.".replace(",", ".")
def go(pid): return f"/go/{pid}/"
def logo(pid, h=26, cls="", lazy=True):
    v = PROV[pid]
    w, hh = LOGO_SIZE.get(v["logo"], (120, 32))
    width = round(w * h / hh)
    return f'<img src="/img/logos/{v["logo"]}.webp" alt="{E(v["name"])} logo" width="{width}" height="{h}"{" loading=\"lazy\"" if lazy else ""} decoding="async"{(" class=%s" % cls) if cls else ""}>'
LOGO_SIZE = {}

def ppg(p):
    return None if p["gb"] is None else p["price"] / p["gb"]

def go_a(pid, label="Se tilbud", cls="btn btn-go"):
    v = PROV[pid]
    rel = "nofollow noopener" if v.get("noaffiliate") else "sponsored nofollow noopener"
    return f'<a class="{cls}" href="{go(pid)}" rel="{rel}" target="_blank" data-p="{pid}" aria-label="{E(label)} hos {E(v["name"])} (åbner i nyt vindue)">{E(label)}</a>'

def intro_html(p):
    if not p.get("intro_txt"): return ""
    out = f'<small class="intro">{E(p["intro_txt"])}</small>'
    if p["id"] in ENDS:
        out += f'<small class="ends" data-ends="{ENDS[p["id"]]}"></small>'
    return out

# ---------- shortcodes ----------
def sc_table(arg, opts):
    tag = arg.strip()
    ps = plans_for(tag)
    sort = opts.get("sort", "price")
    if sort == "gb": ps.sort(key=lambda p: (-gbv(p), p["price"]))
    elif sort == "eu": ps.sort(key=lambda p: (-(p["eu"] or 0), p["price"]))
    else: ps.sort(key=lambda p: (p["price"], -gbv(p)))
    limit = int(opts.get("limit", 0)) or None
    show = 8
    if limit: ps = ps[:limit]
    title = opts.get("titel") or TABLE_TITLES.get(tag) or ("Sammenligning" if not tag.startswith("udbyder-") else f'Alle {PROV[plans_for(tag)[0]["p"]]["name"]}-abonnementer')
    rows = []
    for i, p in enumerate(ps):
        v = PROV[p["p"]]
        best = ' class="best"' if i == 0 and sort == "price" and not tag.startswith("udbyder-") else ""
        extra = ' extra' if i >= show and len(ps) > show + 2 else ''
        cls = (best[:-1] + extra + '"') if best else (f' class="{extra.strip()}"' if extra else "")
        badge = '<span class="badge">Billigst</span>' if best else ""
        sub = f'{talktxt(p)} · {netshort(p["p"])} · ' + ('<span class=yes>5G</span>' if p["g5"] else '4G') + (f' · {E(p["extra"])}' if p.get("extra") else "")
        specs = f'<b>{gbtxt(p)}</b> · EU-data {(str(p["eu"]) + " GB") if p["eu"] else "–"}'
        rows.append(
            f'<tr{cls} data-price="{p["price"]}" data-gb="{gbv(p)}" data-eu="{p["eu"] or 0}" data-net="{netkey(p["p"])}" data-fri="{1 if p["talk"]=="fri" else 0}" data-g5="{1 if p["g5"] else 0}">'
            f'<td class="c-prov">{logo(p["p"])}</td>'
            f'<td class="c-name">{badge}<strong>{E(v["name"])} {E(p["name"])}</strong><small>{sub}</small></td>'
            f'<td class="c-num" data-l="Data"><b>{gbtxt(p)}</b></td>'
            f'<td class="c-num" data-l="EU-data">{(str(p["eu"])+" GB") if p["eu"] else "–"}</td>'
            f'<td class="c-specs">{specs}</td>'
            f'<td class="c-price"><b>{kr(p["price"])}</b><small>pr. md.</small>{intro_html(p)}</td>'
            f'<td class="c-cta">{go_a(p["p"])}</td></tr>')
    more = ""
    coll = ""
    if len(ps) > show + 2:
        coll = " collapsed"
        more = f'<button class="cmp-more" type="button" data-more="Vis alle {len(ps)} abonnementer ↓">Vis alle {len(ps)} abonnementer ↓</button>'
    return (f'<div class="cmp{coll}" data-limit="{show if coll else 999}"><div class="cmp-top"><p class="cmp-title">{E(title)}</p><span class="cmp-meta">Priser tjekket {dk_short(CHECKED)}</span></div>'
            f'<table class="plans"><caption class="sr-only">{E(title)} – normalpris pr. måned, tjekket {dk_date(CHECKED)}</caption><thead><tr><th scope="col">Udbyder</th><th scope="col">Abonnement</th><th scope="col" data-sort="gb">Data</th><th scope="col" data-sort="eu">EU-data</th><th scope="col" class="c-specs">Indhold</th><th scope="col" data-sort="price">Pris/md.</th><th scope="col"><span class="sr-only">Bestil</span></th></tr></thead><tbody>'
            + "".join(rows) + f'</tbody></table>{more}<div class="cmp-foot">Normalpris pr. måned inkl. moms. Grønne priser er introtilbud. Alle abonnementer er uden binding. Se <a href="/metode/">vores metode</a>.</div></div>')

TABLE_TITLES = {"billig": "Billigste mobilabonnementer lige nu", "fri-tale": "Mobilabonnementer med fri tale", "fri-data": "Mobilabonnementer med fri data",
    "store-data": "Abonnementer med meget data", "kun-tale": "Små abonnementer med lidt data", "senior": "Gode abonnementer til seniorer",
    "boern": "Abonnementer til børn", "unge": "Mest data for pengene til unge", "udland": "Mest data i udlandet", "tilbud": "Aktuelle tilbud og kampagner",
    "streaming": "Abonnementer med streaming", "forudbetalt": "Forudbetalte pakker og abonnementer", "5g": "Mobilabonnementer med 5G", "alle": "Alle mobilabonnementer"}

def sc_top3(arg, opts):
    ps = plans_for(arg.strip()) or PLANS
    cheapest = min(ps, key=lambda p: p["price"])
    rest = [p for p in ps if p["id"] != cheapest["id"]]
    def value(p):  # GB pr. krone, fri data = 1500 GB
        return (1500 if p["gb"] is None else p["gb"]) / p["price"]
    most = max(rest, key=value) if rest else cheapest
    rest2 = [p for p in rest if p["id"] != most["id"]] or rest or [cheapest]
    topscore = max(rest2, key=lambda p: (PROV[p["p"]]["score"], -p["price"]))
    picks = [("Billigst", cheapest, ""), ("Bedst i test", topscore, " win"), ("Mest data for pengene", most, "")]
    return '<div class="top3">' + "".join(card(b, p, c) for b, p, c in picks) + "</div>"

def card(badge, p, cls=""):
    v = PROV[p["p"]]
    slug = "lyca-mobile" if p["p"] == "lyca" else p["p"]
    return (f'<div class="pick{cls} rv"><span class="badge{" coral" if badge=="Billigst" else ""}">{E(badge)}</span>{logo(p["p"], 30)}'
            f'<p class="h3" style="font-weight:800;font-size:1.06rem;margin:0 0 10px">{E(v["name"])} {E(p["name"])}</p>'
            f'<ul><li><span>Data</span><b>{gbtxt(p)}</b></li><li><span>EU-data</span><b>{(str(p["eu"])+" GB") if p["eu"] else "–"}</b></li><li><span>Tale</span><b>{talktxt(p)}</b></li><li><span>Net</span><b>{netshort(p["p"])}{" · 5G" if p["g5"] else ""}</b></li><li><span>Vores karakter</span><b>{str(v["score"]).replace(".", ",")}/10</b></li></ul>'
            f'<div class="price"><b>{p["price"]}</b><small>kr./md.</small></div>' + (f'<p class="intro">{E(p["intro_txt"])}</p>' if p.get("intro_txt") else "")
            + go_a(p["p"], f'Gå til {v["name"]}') + f'<a class="rev" href="/udbydere/{slug}/">Læs vores {E(v["name"])}-anmeldelse</a></div>')

def sc_cta(arg, opts):
    pid = arg.strip(); pid = {"lyca-mobile": "lyca"}.get(pid, pid)
    v = PROV[pid]
    return (f'<div class="ctabox rv"><div class="lg">{logo(pid, 28)}</div><p><strong>{E(v["name"])} – fra {kr(fra("udbyder-"+pid))}/md.</strong>{E(v["short"])}</p>{go_a(pid, "Se priser hos " + v["name"])}</div>')

def sc_pcard(arg, opts, self_page=False):
    pid = arg.strip(); pid = {"lyca-mobile": "lyca"}.get(pid, pid)
    v = PROV[pid]; s = v["scores"]
    slug = "lyca-mobile" if pid == "lyca" else pid
    bars = "".join(f'<div class="bar"><div><span>{n}</span><span>{str(s[k]).replace(".", ",")}</span></div><i><em data-w="{s[k]*10}"></em></i></div>'
                   for k, n in [("pris", "Pris (40 %)"), ("net", "Net og dækning (25 %)"), ("fleksibilitet", "Fleksibilitet og vilkår (20 %)"), ("service", "Service (15 %)")])
    ps = plans_for("udbyder-" + pid)
    fd = [p for p in ps if p["gb"] is None]
    facts = [("Mobilnet", v["network"]), ("Ejer", v["owner"]), ("Billigste abonnement", kr(min(p["price"] for p in ps)) + "/md."),
             ("Fri data", (kr(min(p["price"] for p in fd)) + "/md.") if fd else "Tilbydes ikke"), ("5G", "Ja" if any(p["g5"] for p in ps) else "Primært 4G"),
             ("eSIM", "Ja" if v["esim"] else "Nej"), ("Binding", "Ingen")] + ([("Grundlagt", str(v["founded"]))] if v.get("founded") else [])
    pros = "".join(f"<li>{E(x)}</li>" for x in v["pros"]); cons = "".join(f"<li>{E(x)}</li>" for x in v["cons"])
    rev = "" if self_page else f'<a class="btn btn-ghost btn-sm" href="/udbydere/{slug}/">Læs hele anmeldelsen</a>'
    return (f'<div class="pcard"><div class="pcard-head"><div class="ring" style="--v:{v["score"]*10}" role="img" aria-label="Samlet karakter {v["score"]} ud af 10"><span>{str(v["score"]).replace(".", ",")}<small>/ 10</small></span></div>'
            f'<div class="pcard-id">{logo(pid, 34, lazy=False)}<p>{E(v["short"])}</p></div>{go_a(pid, "Se priser")}</div>'
            f'<div class="pcard-body"><div class="bars">{bars}</div><dl class="facts">' + "".join(f"<div><dt>{a}</dt><dd>{E(b)}</dd></div>" for a, b in facts) + '</dl></div>'
            f'<div class="proscons"><div class="pros"><p class="pc-h">Fordele</p><ul>{pros}</ul></div><div class="cons"><p class="pc-h">Ulemper</p><ul>{cons}</ul></div></div>'
            f'<div class="pcard-foot"><span style="font-size:.85rem;color:var(--muted)">Karakter efter <a href="/metode/">vores metode</a> · Priser tjekket {dk_short(CHECKED)}</span>{rev}</div></div>')

def sc_tool(arg, opts):
    t = arg.strip()
    if t == "filter":
        return f'<div class="tool" data-tool="filter"><p class="tool-t">Sammenlign alle {len(PLANS)} abonnementer</p></div>' + sc_table("alle", {"titel": "Alle abonnementer – sorteret efter pris"})
    noscript = {"databeregner": "Databeregneren kræver JavaScript. Tommelfingerregel: 1 time HD-video ≈ 3 GB, 1 time musik ≈ 0,07 GB.",
                "sparberegner": "Sparberegneren kræver JavaScript.", "roaming": "Beregneren kræver JavaScript. Formel: 2 × (pris ekskl. moms ÷ 1,30 € pr. GB).",
                "quiz": "Quizzen kræver JavaScript – se tabellerne ovenfor."}.get(t, "")
    return f'<div class="tool" data-tool="{t}"><noscript><p>{noscript}</p></noscript></div>'

def sc_simo(arg, opts):
    return f'<div class="simo-tip rv">{simo_svg(72, wave=False)}<div class="bubble"><b>Simos tip</b>{arg.strip()}</div></div>'

SHORT = {"tabel": sc_table, "top3": sc_top3, "cta": sc_cta, "udbyderkort": sc_pcard, "vaerktoej": sc_tool, "simo": sc_simo}

def render_shortcodes(body, page):
    def rep(m):
        name, raw = m.group(1), m.group(2)
        if name == "simo":
            return SHORT[name](raw, {})
        parts = raw.split("|")
        opts = {}
        for x in parts[1:]:
            if "=" in x:
                k, v = x.split("=", 1); opts[k.strip()] = v.strip()
        if name == "udbyderkort":
            return sc_pcard(parts[0], opts, self_page=page.get("provider") == parts[0].strip() or page.get("provider") == {"lyca-mobile": "lyca"}.get(parts[0].strip(), parts[0].strip()))
        return SHORT[name](parts[0], opts)
    body = re.sub(r'(?:<p>\s*)?\[\[([a-z0-9]+):(.*?)\]\](?:\s*</p>)?', rep, body, flags=re.S)
    return body

# ---------- mascot ----------
def simo_svg(w=220, wave=True, cls="simo", title=True):
    h = round(w * 150 / 120)
    arm = ('<g class="s-arm"><path d="M98 80c10-6 15-16 15-26" stroke="#0A1628" stroke-width="10" stroke-linecap="round" fill="none"/><path d="M98 80c10-6 15-16 15-26" stroke="#C6F04B" stroke-width="4.5" stroke-linecap="round" fill="none"/><circle cx="113" cy="52" r="7" fill="#C6F04B" stroke="#0A1628" stroke-width="4"/></g>'
           if wave else '<path d="M98 84c8 2 13 8 14 16" stroke="#0A1628" stroke-width="10" stroke-linecap="round" fill="none"/><path d="M98 84c8 2 13 8 14 16" stroke="#C6F04B" stroke-width="4.5" stroke-linecap="round" fill="none"/>')
    t = '<title>Simo – telefonabonnementer.dk\'s maskot</title>' if title else ''
    return (f'<svg class="{cls}" width="{w}" height="{h}" viewBox="-4 -6 128 156" role="img" aria-label="Simo, sitets maskot">{t}'
            '<g class="s-body">'
            '<path class="s-sig" d="M46 10a20 20 0 0 1 28 0" stroke="#C6F04B" stroke-width="4" stroke-linecap="round" fill="none"/>'
            '<path class="s-sig b" d="M38 3a32 32 0 0 1 44 0" stroke="#C6F04B" stroke-width="4" stroke-linecap="round" fill="none"/>'
            '<path d="M60 18v14" stroke="#0A1628" stroke-width="8" stroke-linecap="round"/><path d="M60 18v14" stroke="#C6F04B" stroke-width="3" stroke-linecap="round"/><circle cx="60" cy="17" r="6" fill="#FF6A47" stroke="#0A1628" stroke-width="3.5"/>'
            '<path d="M18 82c-8 2-12 9-12 16" stroke="#0A1628" stroke-width="10" stroke-linecap="round" fill="none"/><path d="M18 82c-8 2-12 9-12 16" stroke="#C6F04B" stroke-width="4.5" stroke-linecap="round" fill="none"/>'
            + arm +
            '<ellipse cx="44" cy="142" rx="11" ry="6" fill="#FF6A47" stroke="#0A1628" stroke-width="3.5"/><ellipse cx="76" cy="142" rx="11" ry="6" fill="#FF6A47" stroke="#0A1628" stroke-width="3.5"/>'
            '<path d="M26 32h52l20 20v78a10 10 0 0 1-10 10H26a10 10 0 0 1-10-10V42a10 10 0 0 1 10-10z" fill="#C6F04B" stroke="#0A1628" stroke-width="5" stroke-linejoin="round"/>'
            '<path d="M78 32v12a8 8 0 0 0 8 8h12" fill="#B2DD2F" stroke="#0A1628" stroke-width="5" stroke-linejoin="round"/>'
            '<g class="s-eyes"><ellipse cx="45" cy="64" rx="8" ry="10" fill="#fff" stroke="#0A1628" stroke-width="3.5"/><ellipse cx="73" cy="64" rx="8" ry="10" fill="#fff" stroke="#0A1628" stroke-width="3.5"/>'
            '<circle cx="47" cy="66" r="4.2" fill="#0A1628"/><circle cx="75" cy="66" r="4.2" fill="#0A1628"/><circle cx="48.5" cy="64" r="1.4" fill="#fff"/><circle cx="76.5" cy="64" r="1.4" fill="#fff"/></g>'
            '<circle cx="34" cy="80" r="5" fill="#FF6A47" opacity=".55"/><circle cx="85" cy="80" r="5" fill="#FF6A47" opacity=".55"/>'
            '<path d="M50 80q9 9 18 0" stroke="#0A1628" stroke-width="4" stroke-linecap="round" fill="none"/>'
            '<rect x="38" y="96" width="44" height="32" rx="7" fill="#FFC23D" stroke="#0A1628" stroke-width="4"/>'
            '<path d="M38 107h12m20 0h12M38 117h12m20 0h12M60 96v10m0 12v10M50 106h20v12H50z" stroke="#0A1628" stroke-width="3" fill="none"/>'
            '</g></svg>')

ICON_SVG = ('<svg viewBox="0 0 40 40" aria-hidden="true"><rect width="40" height="40" rx="11" fill="#0A1628"/>'
            '<rect x="9" y="23" width="5" height="8" rx="1.5" fill="#C6F04B"/><rect x="17.5" y="17" width="5" height="14" rx="1.5" fill="#C6F04B"/>'
            '<rect x="26" y="10" width="5" height="21" rx="1.5" fill="#C6F04B"/></svg>')
def logo_html(): return f'<a class="logo" href="/" aria-label="{BRAND} – forside">{ICON_SVG}<span>telefon<b>abonnementer</b><small>.dk</small></span></a>'

SVG_I = {
    "cal": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/></svg>',
    "chk": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" aria-hidden="true"><path d="M20 6 9 17l-5-5"/></svg>',
    "clk": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>',
    "shield": '<svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="m9 12 2 2 4-4"/></svg>',
}

# ---------- content parsing ----------
def parse(path):
    raw = open(path, encoding="utf-8").read()
    m = re.match(r"\s*---\s*\n(.*?)\n---\s*\n(.*)", raw, re.S)
    fm, rest = m.group(1), m.group(2)
    meta = {}
    for line in fm.splitlines():
        if ":" in line and not line.startswith(" "):
            k, v = line.split(":", 1); meta[k.strip()] = v.strip()
    body, faq, src = rest, [], []
    if "===KILDER===" in body:
        body, s = body.split("===KILDER===", 1)
        for line in s.strip().splitlines():
            if "|" in line:
                t, u = line.rsplit("|", 1); src.append((t.strip(" -"), u.strip()))
    if "===FAQ===" in body:
        body, f = body.split("===FAQ===", 1)
        cur = None
        for line in f.strip().splitlines():
            if line.startswith("Q:"):
                cur = [line[2:].strip(), ""]; faq.append(cur)
            elif line.startswith("A:") and cur: cur[1] = line[2:].strip()
            elif cur and line.strip(): cur[1] += " " + line.strip()
    meta["body"], meta["faq"], meta["src"] = body.strip(), faq, src
    meta["related"] = [x.strip().strip("/") for x in meta.get("related", "").split(",") if x.strip()]
    return meta

def ph(s):
    s = s.replace("{maaned}", MAANED).replace("{aar}", str(TODAY.year)).replace("{mdkort}", f"{MONTHS[TODAY.month-1][:3]}. {TODAY.year}").replace("{tjekket}", dk_short(CHECKED))
    s = re.sub(r"\{fra:([a-z0-9\-]+)\}", lambda m: str(fra(m.group(1))), s)
    PI = {p["id"]: p for p in PLANS}
    def _pl(m):
        k, i = m.group(1), m.group(2)
        p = PI.get(i)
        if not p: return m.group(0)
        if k == "pris": return str(p["price"])
        if k == "intro": return str(p.get("intro") if p.get("intro") is not None else p["price"])
        if k == "introtekst": return p.get("intro_txt") or f'{p["price"]} kr./md.'
        if k == "gb": return gbtxt(p)
        if k == "eu": return str(p["eu"] or "–")
        if k == "navn": return f'{PROV[p["p"]]["name"]} {p["name"]}'
        return m.group(0)
    s = re.sub(r"\{(pris|intro|introtekst|gb|eu|navn):([a-z0-9\-]+)\}", _pl, s)
    s = s.replace("{antal}", str(len(PLANS))).replace("{antal_udbydere}", str(len(PROV)))
    return s

def slugify(t):
    t = re.sub(r"<[^>]+>", "", t).lower()
    for a, b in (("æ", "ae"), ("ø", "oe"), ("å", "aa"), ("é", "e"), ("ü", "u")): t = t.replace(a, b)
    t = re.sub(r"[^a-z0-9]+", "-", t).strip("-")
    return t[:60].rstrip("-")

def strip_tags(s): return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s)).strip()
def words(s): return len(re.findall(r"[A-Za-zÆØÅæøåéü0-9][\wÆØÅæøåéü\-.,/%]*", strip_tags(s)))

# ---------- navigation ----------
TYPES = [("billigste-mobilabonnement", "Billigste mobilabonnement", "billig"), ("mobilabonnement-fri-data", "Fri data", "fri-data"),
         ("fri-tale", "Fri tale", "fri-tale"), ("5g-mobilabonnement", "5G-abonnement", "5g"), ("mobilabonnement-tilbud", "Tilbud lige nu", "tilbud"),
         ("mobilabonnement-boern", "Til børn", "boern"), ("mobilabonnement-unge", "Til unge og studerende", "unge"),
         ("mobilabonnement-pensionister", "Til pensionister", "senior"), ("familieabonnement", "Familieabonnement", None),
         ("mobilabonnement-udlandet", "Udlandet og EU-data", "udland"), ("mobilabonnement-streaming", "Med streaming", "streaming"),
         ("mobilt-bredbaand", "Mobilt bredbånd", "store-data"), ("taletidskort", "Taletidskort og forudbetalt", "forudbetalt"),
         ("mobilabonnement-uden-data", "Uden data / kun tale", "kun-tale"), ("mobilabonnement-uden-binding", "Uden binding", "billig"),
         ("esim", "eSIM", None), ("erhvervsabonnement", "Erhvervsabonnement", None)]
TYPE_ICON = {"billigste-mobilabonnement": "💸", "mobilabonnement-fri-data": "♾️", "fri-tale": "📞", "5g-mobilabonnement": "⚡", "mobilabonnement-tilbud": "🏷️",
             "mobilabonnement-boern": "🧒", "mobilabonnement-unge": "🎧", "mobilabonnement-pensionister": "👵", "familieabonnement": "👨‍👩‍👧",
             "mobilabonnement-udlandet": "✈️", "mobilabonnement-streaming": "🎬", "mobilt-bredbaand": "📶", "taletidskort": "💳",
             "mobilabonnement-uden-data": "☎️", "mobilabonnement-uden-binding": "🔓", "esim": "📲", "erhvervsabonnement": "💼"}
MENU_TYPES = TYPES[:10]
PSLUG = {"telmore": "telmore", "lebara": "lebara", "lyca": "lyca-mobile", "oister": "oister", "yousee": "yousee", "flexii": "flexii", "greentel": "greentel", "duka": "duka", "cbb": "cbb", "eesy": "eesy"}
GUIDES = [("guides/skift-mobilabonnement", "Skift mobilabonnement"), ("guides/hvor-meget-data", "Hvor meget data skal jeg bruge?"),
          ("guides/bedste-mobilnet", "Bedste mobilnet i Danmark"), ("guides/opsig-mobilabonnement", "Opsig dit mobilabonnement"),
          ("guides/mobilpriser-statistik", "Mobilpriser i tal (statistik)")]
ABOUT = [("om-os", "Om os"), ("metode", "Sådan tester vi"), ("forfatter/emil-rostgaard-clausen", "Redaktør: Emil R. Clausen"),
         ("redaktionel-politik", "Redaktionel politik"), ("annoncoeroplysning", "Annoncøroplysning"), ("kontakt", "Kontakt")]

def header():
    def dd(label, items, allurl, alllabel):
        lis = "".join(f'<li><a href="/{u}/">{E(t)}{(" <small>" + E(x) + "</small>") if x else ""}</a></li>' for u, t, x in items)
        if allurl: lis += f'<li><a class="all" href="/{allurl}/">{E(alllabel)} →</a></li>'
        return f'<li><button class="dd" type="button" aria-expanded="false">{E(label)}</button><ul class="menu">{lis}</ul></li>'
    types = [(u, t, f"fra {fra(tag)} kr." if tag else "") for u, t, tag in MENU_TYPES]
    provs = [(f"udbydere/{PSLUG[k]}", PROV[k]["name"], f"fra {fra('udbyder-'+k)} kr.") for k in PSLUG]
    guides = [(u, t, "") for u, t in GUIDES]
    about = [(u, t, "") for u, t in ABOUT]
    return (f'<header class="top"><div class="wrap">{logo_html()}<button class="burger" type="button" aria-label="Menu" aria-expanded="false" aria-controls="nav"><span></span></button>'
            f'<nav class="nav" id="nav" aria-label="Hovedmenu"><ul>'
            + dd("Abonnementer", types, "abonnementer", "Alle abonnementstyper") + dd("Udbydere", provs, "udbydere", "Sammenlign alle udbydere")
            + dd("Guides", guides, "guides", "Alle guides") + dd("Om os", about, None, "")
            + '</ul><div class="nav-cta"><button class="btn btn-go btn-sm" type="button" data-quiz>Find mit abonnement</button></div></nav></div></header>')

def ticker():
    adult = [p for p in PLANS if not is_kid(p)]
    ids = []
    def add(p):
        if p and p["id"] not in ids: ids.append(p["id"])
    add(min((p for p in adult if p["talk"] == "fri"), key=lambda p: p["price"], default=None))
    for p in sorted((p for p in adult if p.get("intro") and "streaming" not in p["tags"]), key=lambda p: p["intro"]): add(p)
    add(min((p for p in adult if p["gb"] is None), key=lambda p: p.get("intro") or p["price"], default=None))
    add(min((p for p in adult if (p["gb"] or 0) >= 1000), key=lambda p: p["price"], default=None))
    add(min(adult, key=lambda p: p["price"]))
    ids = ids[:10]
    items = []
    for i in ids:
        p = next((x for x in PLANS if x["id"] == i), None)
        if not p: continue
        v = PROV[p["p"]]
        offer = f'<b>{E(p["intro_txt"])}</b> (derefter {p["price"]} kr.)' if p.get("intro") else f'<b>{p["price"]} kr./md.</b>'
        rel = "nofollow noopener" if v.get("noaffiliate") else "sponsored nofollow noopener"
        items.append(f'<a href="{go(p["p"])}" rel="{rel}" target="_blank" >{E(v["name"])} {E(p["name"])}: {offer}</a>')
    track = "".join(f"<span><span class=dot></span>{x}</span>" for x in items)
    hidden = track.replace('target="_blank"', 'target="_blank" tabindex="-1"')
    return f'<div class="ticker" role="region" aria-label="Aktuelle tilbud"><div class="ticker-track"><span class="tk">{track}</span><span class="tk" aria-hidden="true">{hidden}</span></div></div>'

def footer():
    col = lambda title, items: f'<div><h3>{title}</h3><ul>' + "".join(f'<li><a href="/{u}/">{E(t)}</a></li>' for u, t in items) + "</ul></div>"
    return (f'<footer class="foot"><div class="wrap"><div class="foot-grid"><div>{logo_html()}'
            f'<p class="disc">Uafhængig sammenligning af {len(PLANS)} telefonabonnementer fra {len(PROV)} danske mobilselskaber. Priser tjekket {dk_date(CHECKED)}. Vi kan modtage provision, når du køber via vores links – det påvirker aldrig rækkefølge eller karakterer. <a href="/annoncoeroplysning/">Læs mere</a>.</p>'
            '<address><strong style="color:#fff">Emro Media</strong><br>Lundbyesgade 13, 8000 Aarhus C<br><a href="mailto:kontakt@forsikringspakken.dk">kontakt@forsikringspakken.dk</a><br>'
            'CVR <a href="https://datacvr.virk.dk/enhed/virksomhed/46727533" rel="noopener" target="_blank">46727533</a></address></div>'
            + col("Abonnementer", [(u, t) for u, t, _ in TYPES] + [("abonnementer", "Alle typer")])
            + col("Udbydere", [(f"udbydere/{PSLUG[k]}", PROV[k]["name"]) for k in PSLUG] + [("udbydere", "Sammenlign udbydere")])
            + col("Guides og om os", GUIDES + [("om-os", "Om os"), ("metode", "Metode"), ("kontakt", "Kontakt")])
            + f'</div><div class="foot-bottom"><span>© {TODAY.year} Emro Media · {BRAND}</span><span><a href="/privatlivspolitik/">Privatlivspolitik</a> · <a href="/cookies/">Cookies</a> · <a href="/redaktionel-politik/">Redaktionel politik</a> · <a href="/annoncoeroplysning/">Annoncøroplysning</a> · <a href="https://www.linkedin.com/in/emil-rostgaard-702809195/" rel="noopener me" target="_blank">LinkedIn</a></span></div></div></footer>')

# ---------- schema ----------
AUTHOR_URL = f"{SITE}/forfatter/emil-rostgaard-clausen/"
def org():
    return {"@type": "Organization", "@id": f"{SITE}/#org", "name": BRAND, "legalName": "Emro Media", "url": SITE + "/",
            "logo": {"@type": "ImageObject", "url": f"{SITE}/img/logo-512.png", "width": 512, "height": 512},
            "email": "kontakt@forsikringspakken.dk", "taxID": "46727533", "vatID": "DK46727533",
            "address": {"@type": "PostalAddress", "streetAddress": "Lundbyesgade 13", "postalCode": "8000", "addressLocality": "Aarhus C", "addressCountry": "DK"},
            "founder": {"@id": f"{AUTHOR_URL}#person"}, "sameAs": ["https://datacvr.virk.dk/enhed/virksomhed/46727533"]}
def person():
    return {"@type": "Person", "@id": f"{AUTHOR_URL}#person", "name": "Emil Rostgaard Clausen", "url": AUTHOR_URL, "jobTitle": "Redaktør og stifter",
            "image": f"{SITE}/img/emil-rostgaard-clausen-400.webp", "worksFor": {"@id": f"{SITE}/#org"},
            "sameAs": ["https://www.linkedin.com/in/emil-rostgaard-702809195/"],
            "knowsAbout": ["Mobilabonnementer", "Teleprodukter", "Forbrugerøkonomi", "Prissammenligning", "Mobilnetværk i Danmark", "EU-roaming"]}

def schema(page, url, crumbs):
    g = [org(), {"@type": "WebSite", "@id": f"{SITE}/#site", "url": SITE + "/", "name": BRAND, "inLanguage": "da-DK", "publisher": {"@id": f"{SITE}/#org"}}]
    if page.get("_author_page") or page["slug"] in ("forfatter/emil-rostgaard-clausen",):
        g.append(person())
    else:
        g.append(person())
    g.append({"@type": "BreadcrumbList", "@id": url + "#crumbs", "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": n, "item": SITE + u} for i, (n, u) in enumerate(crumbs)]})
    wp_type = "ProfilePage" if page["slug"].startswith("forfatter/") else ("AboutPage" if page["slug"] == "om-os" else ("ContactPage" if page["slug"] == "kontakt" else "WebPage"))
    wp = {"@type": wp_type, "@id": url + "#webpage", "url": url, "name": page["_title"], "description": page["_desc"], "inLanguage": "da-DK",
          "isPartOf": {"@id": f"{SITE}/#site"}, "breadcrumb": {"@id": url + "#crumbs"}, "primaryImageOfPage": {"@type": "ImageObject", "url": page["_og"]},
          "datePublished": "2026-10-07", "dateModified": MODIFIED.isoformat(), "speakable": {"@type": "SpeakableSpecification", "cssSelector": ["h1", ".answer-box p"]}}
    if wp_type == "ProfilePage": wp["mainEntity"] = {"@id": f"{AUTHOR_URL}#person"}
    g.append(wp)
    if page.get("section") != "om" or page["slug"] == "metode":
        art = {"@type": "Article", "@id": url + "#article", "headline": page["_h1"], "description": page["_desc"], "image": [page["_og"]],
               "datePublished": "2026-10-07T08:00:00+02:00", "dateModified": MODIFIED.isoformat() + "T08:00:00+02:00",
               "author": {"@id": f"{AUTHOR_URL}#person"}, "publisher": {"@id": f"{SITE}/#org"}, "mainEntityOfPage": {"@id": url + "#webpage"},
               "inLanguage": "da-DK", "wordCount": page.get("_wc", 0), "articleSection": {"typer": "Abonnementer", "udbydere": "Udbydere", "guides": "Guides", "home": "Sammenligning"}.get(page.get("section"), "Om os")}
        if page["src"]: art["citation"] = [{"@type": "CreativeWork", "name": t, "url": u} for t, u in page["src"]]
        g.append(art)
    if page.get("provider"):
        pid = page["provider"]; v = PROV[pid]
        g.append({"@type": "Review", "@id": url + "#review", "name": f'{v["name"]} anmeldelse', "author": {"@id": f"{AUTHOR_URL}#person"}, "publisher": {"@id": f"{SITE}/#org"},
                  "datePublished": "2026-10-07", "reviewRating": {"@type": "Rating", "ratingValue": v["score"], "bestRating": 10, "worstRating": 1},
                  "itemReviewed": {"@type": "Organization", "name": v["name"], "url": v["site"], "sameAs": [v["site"].split("/", 3)[0] + "//" + v["site"].split("/", 3)[2]]}, "reviewBody": v["short"],
                  "positiveNotes": {"@type": "ItemList", "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": x} for i, x in enumerate(v["pros"])]},
                  "negativeNotes": {"@type": "ItemList", "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": x} for i, x in enumerate(v["cons"])]}})
    if page.get("_tags"):
        ps = sorted(plans_for(page["_tags"][0]), key=lambda p: p["price"])[:10]
        g.append({"@type": "ItemList", "@id": url + "#list", "name": TABLE_TITLES.get(page["_tags"][0], page["_h1"]), "itemListOrder": "https://schema.org/ItemListOrderAscending",
                  "numberOfItems": len(ps), "itemListElement": [{"@type": "ListItem", "position": i + 1, "url": f'{SITE}/udbydere/{PSLUG[p["p"]]}/', "name": f'{PROV[p["p"]]["name"]} {p["name"]} – {p["price"]} kr./md.'} for i, p in enumerate(ps)]})
    if page["faq"]:
        g.append({"@type": "FAQPage", "@id": url + "#faq", "mainEntity": [{"@type": "Question", "name": strip_tags(q), "acceptedAnswer": {"@type": "Answer", "text": strip_tags(a)}} for q, a in page["faq"]]})
    return json.dumps({"@context": "https://schema.org", "@graph": g}, ensure_ascii=False, separators=(",", ":"))

# ---------- page pieces ----------
AUTHOR_IMG = '<img src="/img/emil-rostgaard-clausen.webp" alt="Emil Rostgaard Clausen" width="96" height="96" loading="lazy" decoding="async">'
def author_box():
    return (f'<aside class="author" aria-label="Om forfatteren">{AUTHOR_IMG}<div><div class="lbl">Skrevet og faktatjekket af</div><p class="nm" style="font-weight:800">Emil Rostgaard Clausen</p>'
            '<p>Redaktør og stifter af telefonabonnementer.dk. Emil gennemgår priser, vilkår og netværksdata hos de danske mobilselskaber og opdaterer siden, når priserne ændrer sig. Alle tal er kontrolleret mod udbydernes egne prissider og officielle kilder som Digitaliseringsstyrelsen og Danmarks Statistik.</p>'
            '<div class="links"><a href="/forfatter/emil-rostgaard-clausen/">Om Emil</a><a href="/metode/">Sådan tester vi</a><a href="https://www.linkedin.com/in/emil-rostgaard-702809195/" rel="noopener me" target="_blank">LinkedIn</a><a href="/redaktionel-politik/">Redaktionel politik</a></div></div></aside>')

def _tips():
    adult = [p for p in PLANS if not is_kid(p)]
    f = min((p for p in adult if p["talk"] == "fri"), key=lambda p: p["price"])
    fd = min((p for p in adult if p["gb"] is None), key=lambda p: p.get("intro") or p["price"])
    return [f"Hej! Jeg er <b>Simo</b> 👋 Alle priser er tjekket {dk_short(CHECKED)}.",
            f"Fri tale + {gbtxt(f)} koster kun <b>{f['price']} kr.</b> hos {PROV[f['p']]['name']}.",
            "Nummerflytning er <b>gratis</b> og tager max 2 hverdage.", "Alle abonnementer her er <b>uden binding</b>.",
            f"Fri data fra <b>{fd.get('intro') or fd['price']} kr.</b> hos {PROV[fd['p']]['name']}" + (f" ({fd['intro_txt'].split(' ', 2)[-1]})." if fd.get('intro') else ".")]
HERO_TIPS = _tips()

def hero(page, crumbs, home=False):
    cr = ""
    if not home:
        cr = '<nav class="crumbs" aria-label="Brødkrumme"><ol>' + "".join(
            (f'<li><a href="{u}">{E(n)}</a></li>' if i < len(crumbs) - 1 else f'<li aria-current="page">{E(n)}</li>') for i, (n, u) in enumerate(crumbs)) + "</ol></nav>"
    mins = max(1, round(page.get("_wc", 800) / 220))
    by = (f'<div class="byline"><div class="who"><img src="/img/emil-rostgaard-clausen.webp" alt="" width="42" height="42" decoding="async"><span>Af <a href="/forfatter/emil-rostgaard-clausen/">Emil Rostgaard Clausen</a></span></div>'
          f'<span class="meta-i">{SVG_I["cal"]}Opdateret <time datetime="{MODIFIED.isoformat()}">{dk_date(MODIFIED)}</time></span>'
          f'<a class="meta-i check" href="/redaktionel-politik/">{SVG_I["chk"]}Faktatjekket</a><span class="meta-i">{SVG_I["clk"]}{mins} min. læsning</span></div>')
    chips = ""
    if home:
        chips = ('<div class="chips" style="margin-top:22px">' + "".join(f'<a class="chip" href="/{u}/">{TYPE_ICON[u]} {E(t)}</a>' for u, t, _ in TYPES[:6]) + "</div>"
                 + f'<div class="trust"><span>{SVG_I["shield"]}100 % uafhængig sammenligning</span><span>{SVG_I["shield"]}{len(PLANS)} abonnementer · {len(PROV)} selskaber</span><span>{SVG_I["shield"]}Priser tjekket {dk_short(CHECKED)}</span><span>{SVG_I["shield"]}Kilder fra Digitaliseringsstyrelsen og DST</span></div>')
    mascot = (f'<div class="hero-mascot"><div class="hero-bubble" data-tips=\'{E(json.dumps(HERO_TIPS, ensure_ascii=False))}\'>{HERO_TIPS[0]}</div>{simo_svg(220)}</div>')
    return (f'<header class="hero"><div class="wrap">{cr}<div class="hero-grid"><div><div class="kicker">{E(page["_kicker"])}</div><h1>{E(page["_h1"])}</h1>'
            f'<p class="lead">{page["_lead"]}</p>{by}{chips}</div>{mascot}</div></div></header>')

def quick_picks(page):
    if page.get("section") in ("om", "home", "hub") or page["slug"] == "guides": return ""
    tag = page["_tags"][0] if page.get("_tags") else "fri-tale"
    if page.get("provider"):
        ps = sorted(plans_for("udbyder-" + page["provider"], kids=False), key=lambda p: p["price"])
        fri = [p for p in ps if p["talk"] == "fri"] or ps
        pick = [fri[0], fri[len(fri)//2], fri[-1]] if len(fri) >= 3 else fri
        seen = set(); out = [p for p in pick if not (p["id"] in seen or seen.add(p["id"]))]
    else:
        ps = sorted(plans_for(tag), key=lambda p: p["price"])
        seen, out = set(), []
        for p in ps:
            if p["p"] in seen: continue
            seen.add(p["p"]); out.append(p)
            if len(out) == 3: break
    items = "".join(f'<li>{logo(p["p"], 22, lazy=False)}<span class="qn"><b>{E(PROV[p["p"]]["name"])}</b> {E(p["name"])}<small>{gbtxt(p)} · {talktxt(p)}{" · 5G" if p["g5"] else ""}</small></span><span class="qp">{p["price"]} kr.<small>/md.</small></span>{go_a(p["p"], "Se tilbud", "btn btn-go btn-sm")}</li>' for p in out)
    return f'<div class="qpicks"><p class="qh">{"Populære abonnementer" if page.get("provider") else "Billigst i kategorien lige nu"}</p><ol>{items}</ol></div>'

def answer_box(page, home=False):
    if not page.get("_answer"): return ""
    extra = quick_picks(page)
    return (f'<div class="answer"><div class="answer-box" role="note"><div class="lbl">Kort svar</div><p>{page["_answer"]}</p><p class="src">Kilde: udbydernes prissider, tjekket {dk_short(CHECKED)} · <a href="/metode/">Sådan sammenligner vi</a></p>{extra}</div></div>')

def fix_h4(body):
    """h4 i fordele/ulemper -> p; h4 der følger direkte efter h2 uden h3 -> h3."""
    body = re.sub(r'<div class="(pros|cons)">\s*<h4>(.*?)</h4>', r'<div class="\1"><p class="pc-h">\2</p>', body)
    out, last = [], 1
    for tok in re.split(r'(<h[2-4][^>]*>.*?</h[2-4]>)', body, flags=re.S):
        m = re.match(r'<h([2-4])', tok)
        if m:
            lvl = int(m.group(1))
            if lvl == 4 and last < 3:
                tok = re.sub(r'^<h4', '<h3', tok); tok = re.sub(r'</h4>$', '</h3>', tok); lvl = 3
            last = lvl
        out.append(tok)
    return "".join(out)

def add_ids(body):
    toc, used = [], set()
    def rep(m):
        attrs, inner = m.group(1), m.group(2)
        if 'id="' in attrs:
            i = re.search(r'id="([^"]+)"', attrs).group(1)
        else:
            i = slugify(inner) or "afsnit"
            while i in used: i += "-2"
            attrs += f' id="{i}"'
        used.add(i); toc.append((i, strip_tags(inner)))
        return f"<h2{attrs}>{inner}</h2>"
    body = re.sub(r"<h2([^>]*)>(.*?)</h2>", rep, body, flags=re.S)
    return body, toc

def side_deals(tag):
    if not tag or tag.startswith("udbyder-"): tag = "fri-tale"
    ps = sorted(plans_for(tag), key=lambda p: p["price"])
    seen, out = set(), []
    for p in ps:
        if p["p"] in seen: continue
        seen.add(p["p"]); out.append(p)
        if len(out) == 4: break
    lis = "".join(f'<li><a href="{go(p["p"])}" rel="{"nofollow noopener" if PROV[p["p"]].get("noaffiliate") else "sponsored nofollow noopener"}" target="_blank">{E(PROV[p["p"]]["name"])} · {gbtxt(p)}</a><b>{p["price"]} kr.</b></li>' for p in out)
    return (f'<div class="side-deal"><div class="lbl">Billigst lige nu · {E(TABLE_TITLES.get(tag or "billig", "")).split(" ")[0] if False else ""}{dk_short(CHECKED)}</div><ol>{lis}</ol>'
            f'<button class="btn btn-go" type="button" data-quiz>Find mit abonnement</button></div>')

def related_html(rel):
    if not rel: return ""
    items = []
    for s in rel:
        p = PAGES.get(s)
        if p: items.append(f'<a href="/{s}/">{E(p["_h1"])}<small>{E(strip_tags(p["_lead"])[:90].rsplit(" ", 1)[0])}…</small></a>')
    if not items: return ""
    return f'<section aria-labelledby="rel-h"><h2 id="rel-h">Læs også</h2><div class="related">{"".join(items)}</div></section>'

def head(page, url):
    css = CSS
    return (f'<!doctype html><html lang="da" class="no-js"><head><meta charset="utf-8"><script>document.documentElement.className="js"</script><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{E(page["_title"])}</title><meta name="description" content="{E(page["_desc"])}"><link rel="canonical" href="{url}">'
            f'<meta name="robots" content="{"noindex,follow" if page.get("noindex") else "index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1"}">'
            f'<meta name="author" content="Emil Rostgaard Clausen"><meta name="theme-color" content="#0A1628">'
            f'<meta property="og:type" content="{"website" if page["slug"]=="" else "article"}"><meta property="og:locale" content="da_DK"><meta property="og:site_name" content="{BRAND}">'
            f'<meta property="og:title" content="{E(page["_title"])}"><meta property="og:description" content="{E(page["_desc"])}"><meta property="og:url" content="{url}">'
            f'<meta property="og:image" content="{page["_og"]}"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">'
            f'<meta property="article:modified_time" content="{MODIFIED.isoformat()}"><meta name="twitter:card" content="summary_large_image">'
            f'<link rel="icon" href="/favicon.ico" sizes="32x32"><link rel="icon" href="/favicon.svg" type="image/svg+xml"><link rel="apple-touch-icon" href="/apple-touch-icon.png"><link rel="manifest" href="/site.webmanifest">'
            f'<style>{css}</style><script type="application/ld+json">{page["_schema"]}</script></head>')

def tail():
    return (f'<button class="helper" type="button" data-quiz aria-label="Find dit abonnement med Simo"><span class="hd">{simo_svg(40, wave=False, title=False)}</span><span class="t">Find billigste<small>Svar på 3 spørgsmål</small></span></button>'
            '<dialog class="quiz" id="quiz-dlg" aria-labelledby="qz-title"><div class="qz"></div></dialog>'
            f'<template id="simo-tpl">{simo_svg(54, wave=True, title=False)}</template>'
            f'<script type="application/json" id="pdata">{PDATA}</script><script src="/assets/app.js?v={JSV}" defer></script></body></html>')

# ---------- build page ----------
def crumbs_for(page):
    c = [("Forside", "/")]
    s, sec = page["slug"], page.get("section")
    if sec == "udbydere" and s != "udbydere": c.append(("Udbydere", "/udbydere/"))
    if sec == "guides" and s != "guides": c.append(("Guides", "/guides/"))
    if sec == "typer": c.append(("Abonnementer", "/abonnementer/"))
    if s.startswith("forfatter/"): c.append(("Om os", "/om-os/"))
    if s: c.append((page.get("crumb") or page["_h1"], f"/{s}/"))
    return c

def prep(page):
    for k in ("title", "desc", "h1", "kicker", "answer", "lead"):
        page["_" + k] = ph(page.get(k, ""))
    page["faq"] = [[ph(q), ph(a)] for q, a in page["faq"]]
    if not page["_kicker"]: page["_kicker"] = f"Opdateret {MAANED}"
    page["_tags"] = re.findall(r"\[\[(?:tabel|top3):([a-z0-9\-]+)", page["body"])[:1]
    page["_wc"] = words(re.sub(r"\[\[.*?\]\]", "", ph(page["body"]), flags=re.S)) + sum(words(q) + words(a) for q, a in page["faq"])
    url = SITE + (f'/{page["slug"]}/' if page["slug"] else "/")
    page["_url"] = url
    page["_og"] = f'{SITE}/img/og/{(page["slug"] or "forside").replace("/", "-")}.jpg'

def render(page):
    url = page["_url"]
    body = ph(page["body"])
    body = re.sub(r"<table(?![^>]*class=\"plans\")([^>]*)>", r'<div class="tbl"><table\1>', body)
    body = re.sub(r"</table>", "</table></div>", body)
    body = render_shortcodes(body, page)
    body = body.replace('</table></div></div><div class="cmp-foot">', '</table></div><div class="cmp-foot">')  # safety
    body = re.sub(r'(<blockquote class="expert">.*?<cite>)', lambda m: m.group(1) + '<img src="/img/emil-rostgaard-clausen.webp" alt="" width="36" height="36" loading="lazy">', body, flags=re.S)
    body = re.sub(r'<a href="(https?://(?!telefonabonnementer\.dk)[^"]+)"(?![^>]*rel=)', r'<a href="\1" rel="noopener" target="_blank"', body)
    body = fix_h4(body)
    body, toc = add_ids(body)
    crumbs = crumbs_for(page)
    faq_html = ""
    if page["faq"]:
        toc.append(("faq", "Ofte stillede spørgsmål"))
        faq_html = '<h2 id="faq">Ofte stillede spørgsmål</h2><div class="faq">' + "".join(
            f'<details{" open" if i == 0 else ""}><summary>{E(q) if "<" not in q else q}</summary><div class="a"><p>{a}</p></div></details>' for i, (q, a) in enumerate(page["faq"])) + "</div>"
    src_html = ""
    if page["src"]:
        toc.append(("kilder", "Kilder"))
        src_html = '<section class="sources"><h2 id="kilder">Kilder</h2><ol>' + "".join(
            f'<li id="kilde-{i+1}">{E(t)}. <a href="{E(u)}" rel="noopener" target="_blank">{E(re.sub(r"^https?://(www\\.)?", "", u)[:70])}</a></li>' for i, (t, u) in enumerate(page["src"])) + f'</ol><p style="font-size:.82rem;color:var(--muted)">Alle kilder tilgået {dk_date(CHECKED)}.</p></section>'
    page["_schema"] = schema(page, url, crumbs)
    toc_li = "".join(f'<li><a href="#{i}">{E(t)}</a></li>' for i, t in toc)
    is_about = page.get("section") == "om"
    aside = "" if is_about and len(toc) < 4 else (f'<aside class="aside" aria-label="Indhold"><div class="aside-in"><nav class="toc" aria-label="Indholdsfortegnelse"><div class="lbl">Indhold</div><ol>{toc_li}</ol></nav>'
                                                 + side_deals(page["_tags"][0] if page["_tags"] else None) + "</div></aside>")
    toc_m = f'<details class="toc-m"><summary>Indhold på siden ({len(toc)})</summary><ol>{toc_li}</ol></details>' if len(toc) >= 4 else ""
    disc = ('<p class="disclosure"><strong>Annoncøroplysning:</strong> Telefonabonnementer.dk er gratis at bruge. Når du klikker på "Se tilbud" og køber et abonnement, kan vi modtage en provision fra udbyderen. '
            'Det koster ikke dig noget ekstra og påvirker hverken rækkefølgen i tabellerne (sorteret efter pris) eller vores karakterer. <a href="/annoncoeroplysning/">Læs annoncøroplysningen</a>.</p>')
    main = (f'<div class="wrap layout{" full" if not aside else ""}"><article class="content">{toc_m}{body}{faq_html}{author_box() if not page["slug"].startswith("forfatter") else ""}{src_html}'
            f'{related_html(page["related"])}{disc if not is_about else ""}</article>{aside}</div>')
    return (head(page, url) + '<body><a class="skip" href="#main">Spring til indhold</a>' + ticker() + header()
            + f'<main id="main">{hero(page, crumbs)}{answer_box(page)}{main}</main>' + footer() + tail())

# ---------- home ----------
def render_home(page):
    url = SITE + "/"
    crumbs = [("Forside", "/")]
    adult = [p for p in PLANS if not is_kid(p) and "streaming" not in p["tags"]]
    fri = [p for p in adult if p["talk"] == "fri"]
    pk1 = min((p for p in fri if gbv(p) >= 20), key=lambda p: (p["price"], -gbv(p)))
    fd = [p for p in adult if p["gb"] is None]
    pk2 = min(fd, key=lambda p: (not p["g5"], -PROV[p["p"]]["score"], p["price"]))
    big = [p for p in fri if (p["gb"] or 0) >= 100 and p["id"] not in (pk1["id"], pk2["id"])]
    pk3 = min(big, key=lambda p: (p.get("intro") or p["price"]) / p["gb"])
    tdc = [p for p in fri if PROV[p["p"]]["network"] == "TDC NET" and gbv(p) >= 30]
    pk4 = min(tdc, key=lambda p: p.get("intro") or p["price"])
    picks = [("Billigst med fri tale", pk1, ""), ("Bedst i test " + str(TODAY.year), pk2, " win"), ("Mest data for pengene", pk3, ""), ("Bedste dækning", pk4, "")]
    cards = "".join(card(b, p, c) for b, p, c in picks)
    pgrid = "".join(f'<a href="/udbydere/{PSLUG[k]}/" class="rv">{logo(k, 26)}<span class="sc">{str(PROV[k]["score"]).replace(".", ",")}/10</span><b>fra {fra("udbyder-"+k)} kr.</b><small>{E(PROV[k]["short"])}</small></a>' for k in sorted(PSLUG, key=lambda k: -PROV[k]["score"]))
    tgrid = "".join(f'<a href="/{u}/"><span class="ic" aria-hidden="true">{TYPE_ICON[u]}</span><span><strong>{E(t)}</strong>{(f"<em>fra {fra(tag)} kr./md.</em>") if tag else "<small>Guide og sammenligning</small>"}</span></a>' for u, t, tag in TYPES)
    logos = "".join(f'<a href="/udbydere/{PSLUG[k]}/" title="{E(PROV[k]["name"])} anmeldelse">{logo(k, 28)}</a>' for k in PSLUG)
    body = ph(page["body"])
    body = re.sub(r"<table(?![^>]*class=\"plans\")([^>]*)>", r'<div class="tbl"><table\1>', body); body = body.replace("</table>", "</table></div>")
    body = render_shortcodes(body, page)
    body = re.sub(r'(<blockquote class="expert">.*?<cite>)', lambda m: m.group(1) + '<img src="/img/emil-rostgaard-clausen.webp" alt="" width="36" height="36" loading="lazy">', body, flags=re.S)
    body = re.sub(r'<a href="(https?://(?!telefonabonnementer\.dk)[^"]+)"(?![^>]*rel=)', r'<a href="\1" rel="noopener" target="_blank"', body)
    body = fix_h4(body)
    body, toc = add_ids(body)
    faq_html = '<h2 id="faq">Ofte stillede spørgsmål om telefonabonnementer</h2><div class="faq">' + "".join(
        f'<details{" open" if i == 0 else ""}><summary>{E(q)}</summary><div class="a"><p>{a}</p></div></details>' for i, (q, a) in enumerate(page["faq"])) + "</div>"
    toc.append(("faq", "Ofte stillede spørgsmål")); toc.append(("kilder", "Kilder"))
    src_html = '<section class="sources"><h2 id="kilder">Kilder</h2><ol>' + "".join(f'<li id="kilde-{i+1}">{E(t)}. <a href="{E(u)}" rel="noopener" target="_blank">{E(re.sub(r"^https?://(www\\.)?", "", u)[:70])}</a></li>' for i, (t, u) in enumerate(page["src"])) + "</ol></section>"
    page["_schema"] = schema(page, url, crumbs)
    toc_li = "".join(f'<li><a href="#{i}">{E(t)}</a></li>' for i, t in toc)
    aside = (f'<aside class="aside" aria-label="Indhold"><div class="aside-in"><nav class="toc" aria-label="Indholdsfortegnelse"><div class="lbl">Indhold</div><ol>{toc_li}</ol></nav>{side_deals("fri-tale")}</div></aside>')
    sections = (f'<section class="logos" aria-label="Udbydere vi sammenligner"><div class="wrap"><span class="lbl">Vi sammenligner priser fra</span>{logos}</div></section>'
                f'<section class="sec" aria-labelledby="picks-h"><div class="wrap"><div class="sec-h"><h2 id="picks-h">Bedste telefonabonnementer i {MAANED}</h2><p>Vores fire anbefalinger efter at have sammenlignet {len(PLANS)} abonnementer på pris, data, net og vilkår. Alle er uden binding.</p></div>'
                f'<div class="top3" style="grid-template-columns:repeat(auto-fit,minmax(240px,1fr))">{cards}</div></div></section>'
                f'<section class="sec soft" aria-labelledby="all-h"><div class="wrap"><div class="sec-h"><h2 id="all-h">Sammenlign alle telefonabonnementer</h2><p>Filtrér på pris, datamængde, mobilnet og 5G. Tabellen er sorteret efter normalpris – grønne priser er introtilbud.</p></div>{sc_tool("filter", {})}</div></section>'
                f'<section class="sec" aria-labelledby="types-h"><div class="wrap"><div class="sec-h"><h2 id="types-h">Find telefonabonnement efter behov</h2><p>Hver side har sin egen sammenligning, regneeksempler og en guide til netop din situation.</p></div><div class="tgrid">{tgrid}</div></div></section>'
                f'<section class="sec soft" aria-labelledby="prov-h"><div class="wrap"><div class="sec-h"><h2 id="prov-h">Mobilselskaberne bedømt</h2><p>Karakter fra 1-10 efter <a href="/metode/">vores metode</a>: pris 40 %, net 25 %, vilkår 20 % og service 15 %.</p></div><div class="pgrid">{pgrid}</div></div></section>')
    main = (f'<div class="wrap layout"><article class="content">{body}{faq_html}{author_box()}{src_html}'
            '<p class="disclosure"><strong>Annoncøroplysning:</strong> Telefonabonnementer.dk er gratis at bruge. Vi kan modtage provision, når du køber via vores links. Det påvirker hverken rækkefølgen (sorteret efter pris) eller vores karakterer. <a href="/annoncoeroplysning/">Læs mere</a>.</p>'
            f'</article>{aside}</div>')
    return (head(page, url) + '<body><a class="skip" href="#main">Spring til indhold</a>' + ticker() + header()
            + f'<main id="main">{hero(page, crumbs, home=True)}{answer_box(page, True)}{sections}{main}</main>' + footer() + tail())

# ---------- hub: abonnementer ----------
def abonnementer_page():
    rows = "".join(f'<tr><td><a href="/{u}/">{E(t)}</a></td><td>{(kr(fra(tag))+"/md.") if tag else "Se guide"}</td><td>{E(PAGES[u]["_answer"][:150].rsplit(" ",1)[0]) if u in PAGES else ""}…</td></tr>' for u, t, tag in TYPES)
    tg = "".join(f'<a href="/{u}/"><span class="ic" aria-hidden="true">{TYPE_ICON[u]}</span><span><strong>{E(t)}</strong>{(f"<em>fra {fra(tag)} kr./md.</em>") if tag else "<small>Guide og sammenligning</small>"}</span></a>' for u, t, tag in TYPES)
    body = (f'<p>Et telefonabonnement er ikke bare et telefonabonnement. Børn har brug for lav pris og spærringer, pensionister for fri tale og god service, unge for masser af data, og rejsende for EU-data og dækning uden for Europa. Derfor har vi lavet en selvstændig sammenligning for hver type – med egne tabeller, regneeksempler og råd.</p>'
            f'<p>Alle sider bygger på de samme {len(PLANS)} abonnementer fra {len(PROV)} selskaber, som vi har tjekket hos udbyderne den {dk_date(CHECKED)}. Priserne er normalpriser pr. måned inkl. moms, og introtilbud står separat, så du kan se den reelle pris efter kampagnen.</p>'
            f'<h2>Alle abonnementstyper</h2><div class="tgrid" style="margin:1.4em 0 2em">{tg}</div>'
            f'<h2>Laveste pris pr. abonnementstype</h2><div class="tbl"><table><thead><tr><th>Type</th><th>Laveste pris</th><th>Kort svar</th></tr></thead><tbody>{rows}</tbody></table></div>'
            '<h2>Sådan finder du den rigtige type</h2><ol class="steps"><li><strong>Tjek dit forbrug.</strong> Se i telefonens indstillinger, hvor meget data du har brugt de seneste 30 dage. Danskerne bruger i gennemsnit 26,9 GB om måneden.</li>'
            '<li><strong>Vælg tale.</strong> Ringer du mere end 4-5 timer om måneden, så vælg fri tale – det koster sjældent mere end 10-20 kr. ekstra.</li>'
            '<li><strong>Tjek dækningen.</strong> Slå din adresse op på tjekditnet.dk og vælg et selskab på det net, der dækker bedst hos dig.</li>'
            '<li><strong>Sammenlign normalprisen.</strong> Et introtilbud er godt, men det er prisen efter kampagnen, der afgør, hvad du betaler på et år.</li></ol>'
            '[[vaerktoej:quiz]]')
    return {"slug": "abonnementer", "title": "Typer af mobilabonnementer → Find din type ({maaned})", "desc": f"Find det rigtige mobilabonnement: billigste, fri data, 5G, børn, unge, pensionister, udlandet og mere. {len(PLANS)} abonnementer sammenlignet – priser fra 19 kr./md.",
            "h1": "Alle typer mobilabonnementer", "kicker": "Opdateret {maaned}", "answer": f"Vi sammenligner {len(TYPES)} typer mobilabonnementer. Billigst er abonnementer med lidt data fra 19 kr./md., fri tale fås fra 49 kr./md. og fri data fra 149 kr./md. (129 kr. første år hos Flexii).",
            "lead": "Vælg den type, der passer til dit behov – hver side har sin egen sammenligning, tabeller og guide.", "crumb": "Abonnementer", "section": "hub",
            "body": body, "faq": [], "src": [("Telestatistik – Hovedresultater 2. halvår 2024, Digitaliseringsstyrelsen", "https://digst.dk/media/vt2epygl/hovedresultater-2h24.pdf")],
            "related": ["billigste-mobilabonnement", "udbydere", "guides"]}

# ---------- assets ----------
def minify_css(s):
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"\s*([{}:;,>])\s*", r"\1", s)
    s = s.replace(";}", "}")
    return s.strip()

def minify_js(s):
    out = []
    for line in s.splitlines():
        l = line.strip()
        if l.startswith("/*") and l.endswith("*/"): continue
        if l: out.append(l)
    return "\n".join(out)

def build_images():
    from PIL import Image, ImageDraw, ImageFont, ImageChops
    os.makedirs(f"{ROOT}/img/logos", exist_ok=True); os.makedirs(f"{ROOT}/img/og", exist_ok=True)
    up = f"{B}/assets/img"
    for f in glob.glob(f"{up}/logos/*.webp"):
        im = Image.open(f).convert("RGBA")
        bgc = Image.new("RGBA", im.size, (255, 255, 255, 0))
        # trim transparent/white borders
        if im.getchannel("A").getextrema()[0] < 200:
            box = im.getchannel("A").point(lambda v: 255 if v > 12 else 0).getbbox()
        else:
            rgb = im.convert("RGB"); bg = Image.new("RGB", im.size, rgb.getpixel((0, 0)))
            box = ImageChops.difference(rgb, bg).point(lambda v: 255 if v > 18 else 0).getbbox()
        if box:
            pad = 2; box = (max(0, box[0]-pad), max(0, box[1]-pad), min(im.width, box[2]+pad), min(im.height, box[3]+pad)); im = im.crop(box)
        h = 64; w = round(im.width * h / im.height)
        if im.height > h: im = im.resize((w, h), Image.LANCZOS)
        name = os.path.basename(f)[:-5]
        im.save(f"{ROOT}/img/logos/{name}.webp", "WEBP", quality=90, method=6)
        LOGO_SIZE[name] = im.size
    ph_ = Image.open(f"{up}/emil.jpg").convert("RGB")
    s = min(ph_.size); ph_ = ph_.crop(((ph_.width - s)//2, 0, (ph_.width - s)//2 + s, s))
    ph_.resize((192, 192), Image.LANCZOS).save(f"{ROOT}/img/emil-rostgaard-clausen.webp", "WEBP", quality=82, method=6)
    ph_.resize((400, 400), Image.LANCZOS).save(f"{ROOT}/img/emil-rostgaard-clausen-400.webp", "WEBP", quality=82, method=6)
    # icons
    def icon(sz):
        im = Image.new("RGBA", (sz, sz), (0, 0, 0, 0)); d = ImageDraw.Draw(im); k = sz / 40
        d.rounded_rectangle([0, 0, sz-1, sz-1], radius=int(11*k), fill="#0A1628")
        for x, y, hh in ((9, 23, 8), (17.5, 17, 14), (26, 10, 21)):
            d.rounded_rectangle([x*k, y*k, (x+5)*k, (y+hh)*k], radius=max(1, int(1.5*k)), fill="#C6F04B")
        return im
    icon(512).save(f"{ROOT}/img/logo-512.png"); icon(192).save(f"{ROOT}/img/icon-192.png"); icon(180).convert("RGB").save(f"{ROOT}/apple-touch-icon.png")
    icon(48).save(f"{ROOT}/favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)])
    open(f"{ROOT}/favicon.svg", "w").write(ICON_SVG.replace('<svg viewBox', '<svg xmlns="http://www.w3.org/2000/svg" viewBox').replace(' aria-hidden="true"', ''))

def og_image(page):
    from PIL import Image, ImageDraw, ImageFont
    W_, H_ = 1200, 630
    im = Image.new("RGB", (W_, H_), "#0A1628"); d = ImageDraw.Draw(im)
    for x in range(0, W_, 44): d.line([(x, 0), (x, H_)], fill="#111F35")
    for y in range(0, H_, 44): d.line([(0, y), (W_, y)], fill="#111F35")
    d.ellipse([820, -260, 1460, 380], fill="#13307F")
    fb = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"; fr = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    big = ImageFont.truetype(fb, 74); mid = ImageFont.truetype(fb, 34); sm = ImageFont.truetype(fr, 28)
    d.rounded_rectangle([70, 70, 130, 130], radius=16, fill="#C6F04B")
    for x, y, hh in ((83, 108, 12), (96, 98, 22), (109, 86, 34)): d.rounded_rectangle([x, y, x+8, y+hh], radius=2, fill="#0A1628")
    d.text((150, 80), "telefonabonnementer.dk", font=mid, fill="#FFFFFF")
    words_ = page["_h1"].split(); lines, cur = [], ""
    for w in words_:
        t = (cur + " " + w).strip()
        if d.textlength(t, font=big) > 1000: lines.append(cur); cur = w
        else: cur = t
    lines.append(cur)
    y = 230
    for l in lines[:3]: d.text((70, y), l, font=big, fill="#FFFFFF"); y += 90
    tag = page["_tags"][0] if page.get("_tags") else ("udbyder-" + page["provider"] if page.get("provider") else None)
    pill = f"Priser fra {fra(tag)} kr./md." if tag else f"{len(PLANS)} abonnementer sammenlignet"
    tw = d.textlength(pill, font=mid)
    d.rounded_rectangle([70, 500, 70 + tw + 50, 560], radius=30, fill="#C6F04B"); d.text((95, 511), pill, font=mid, fill="#0A1628")
    d.text((70 + tw + 80, 517), f"Opdateret {MAANED} · Uafhængig", font=sm, fill="#9FB0C7")
    im.save(f'{ROOT}/img/og/{(page["slug"] or "forside").replace("/", "-")}.jpg', "JPEG", quality=80, optimize=True, progressive=True)

def write(path, s):
    full = os.path.join(ROOT, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    open(full, "w", encoding="utf-8").write(s)

# ---------- main ----------
PAGES = {}
def main():
    global CSS, PDATA, JSV
    if os.path.isdir(ROOT): shutil.rmtree(ROOT)
    os.makedirs(ROOT)
    build_images()
    CSS = minify_css(open(f"{B}/assets/style.css", encoding="utf-8").read())
    js = minify_js(open(f"{B}/assets/app.js", encoding="utf-8").read())
    JSV = hashlib.md5(js.encode()).hexdigest()[:8]
    write("assets/app.js", js)
    PDATA = json.dumps({"checked": dk_date(CHECKED), "plans": [{k: p.get(k) for k in ("id", "p", "name", "price", "intro_txt", "gb", "eu", "talk", "g5", "tags")} for p in PLANS],
                        "prov": {k: {"name": v["name"], "logo": v["logo"], "net": v["scores"]["net"], "netk": netkey(k), "netn": netshort(k)} for k, v in PROV.items()}},
                       ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    for f in sorted(glob.glob(f"{B}/content/*.txt")):
        pg = parse(f); pg["slug"] = pg.get("slug", "").strip("/")
        if pg["slug"] == "home": pg["slug"] = ""
        if pg.get("provider") == "lyca-mobile": pg["provider"] = "lyca"
        prep(pg); PAGES[pg["slug"]] = pg
    hub = abonnementer_page(); prep(hub); PAGES["abonnementer"] = hub
    report = []
    for s, pg in PAGES.items():
        html_ = render_home(pg) if s == "" else render(pg)
        write(f"{s}/index.html" if s else "index.html", html_)
        og_image(pg)
        report.append((s or "/", pg["_wc"], len(pg["_title"]), len(pg["_desc"])))
    # 404
    nf = {"slug": "404", "_title": "Siden findes ikke · Telefonabonnementer.dk", "_desc": "Siden blev ikke fundet.", "_h1": "Ups – siden findes ikke", "noindex": True,
          "_og": f"{SITE}/img/og/forside.jpg", "_schema": "{}", "faq": [], "src": []}
    links = "".join(f'<a class="chip" href="/{u}/">{TYPE_ICON[u]} {E(t)}</a>' for u, t, _ in TYPES[:8])
    write("404.html", head(nf, SITE + "/404.html") + '<body>' + header() + f'<main id="main"><section class="hero"><div class="wrap" style="padding:70px 20px 90px;display:grid;grid-template-columns:1fr 220px;gap:30px;align-items:center"><div><div class="kicker">Fejl 404</div><h1>Ups – Simo kan ikke finde siden</h1><p class="lead">Siden er flyttet eller findes ikke længere. Prøv en af de mest populære sammenligninger:</p><div class="chips" style="margin-top:20px">{links}</div><p style="margin-top:26px"><a class="btn btn-go" href="/">Til forsiden</a></p></div>{simo_svg(200)}</div></section></main>' + footer() + tail())
    # go-redirects
    ht_redirects = []
    for k, v in PROV.items():
        write(f"go/{k}/index.html", f'<!doctype html><html lang="da" class="no-js"><head><meta charset="utf-8"><script>document.documentElement.className="js"</script><meta name="robots" content="noindex,nofollow"><title>Videresender til {E(v["name"])}…</title><meta http-equiv="refresh" content="0;url={E(v["url"])}"><link rel="canonical" href="{SITE}/udbydere/{PSLUG[k]}/"></head><body><p>Videresender til <a href="{E(v["url"])}" rel="sponsored nofollow">{E(v["name"])}</a>…</p><script>location.replace({json.dumps(v["url"])})</script></body></html>')
        ht_redirects.append(f"RewriteRule ^go/{k}/?$ {v['url'].replace(' ', '%20')} [R=302,L,NE]")
    # sitemap
    urls = "".join(f'<url><loc>{SITE}/{(s + "/") if s else ""}</loc><lastmod>{MODIFIED.isoformat()}</lastmod><image:image><image:loc>{PAGES[s]["_og"]}</image:loc></image:image></url>' for s in PAGES)
    write("sitemap.xml", f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">{urls}</urlset>')
    write("robots.txt", f"User-agent: *\nAllow: /\nDisallow: /go/\nDisallow: /_build/\n\n# AI-søgemaskiner er velkomne\nUser-agent: GPTBot\nAllow: /\nUser-agent: OAI-SearchBot\nAllow: /\nUser-agent: PerplexityBot\nAllow: /\nUser-agent: ClaudeBot\nAllow: /\nUser-agent: Google-Extended\nAllow: /\n\nSitemap: {SITE}/sitemap.xml\n")
    # llms.txt (GEO)
    def ln(s): pg = PAGES[s]; return f"- [{pg['_h1']}]({SITE}/{s + '/' if s else ''}): {strip_tags(pg['_answer'])}"
    llms = (f"# {BRAND}\n\n> Uafhængig dansk sammenligning af {len(PLANS)} telefonabonnementer (mobilabonnementer) fra {len(PROV)} selskaber: {', '.join(v['name'] for v in PROV.values())}. Priser tjekket {dk_date(CHECKED)} på udbydernes egne sider. Udgivet af Emro Media (CVR 46727533), redaktør Emil Rostgaard Clausen.\n\n"
            "## Hurtige fakta (normalpris pr. måned inkl. moms, uden binding)\n" + "\n".join(f"- {PROV[p['p']]['name']} {p['name']}: {p['price']} kr./md. ({gbtxt(p)}, EU {p['eu'] or '–'} GB, {talktxt(p)}, {'5G' if p['g5'] else '4G'}, net: {PROV[p['p']]['network']}){' – ' + p['intro_txt'] if p.get('intro_txt') else ''} – {SITE}/udbydere/{PSLUG[p['p']]}/" for p in sorted(PLANS, key=lambda p: p['price']))
            + "\n\n## Abonnementstyper\n" + "\n".join(ln(u) for u, _, _ in TYPES if u in PAGES)
            + "\n\n## Udbydere\n" + "\n".join(ln(f"udbydere/{PSLUG[k]}") for k in PSLUG if f"udbydere/{PSLUG[k]}" in PAGES)
            + "\n\n## Guides\n" + "\n".join(ln(u) for u, _ in GUIDES if u in PAGES)
            + f"\n\n## Om\n- [Metode]({SITE}/metode/)\n- [Om os]({SITE}/om-os/)\n- [Forfatter]({AUTHOR_URL})\n")
    write("llms.txt", llms)
    write("site.webmanifest", json.dumps({"name": BRAND, "short_name": "Telefonabonnementer", "start_url": "/", "display": "browser", "background_color": "#ffffff", "theme_color": "#0A1628",
                                          "icons": [{"src": "/img/icon-192.png", "sizes": "192x192", "type": "image/png"}, {"src": "/img/logo-512.png", "sizes": "512x512", "type": "image/png"}]}))
    write(".htaccess", HTACCESS.replace("#GO_RULES#", "\n".join(ht_redirects)))
    print(f"Byggede {len(PAGES)} sider · {TODAY}")
    for r in sorted(report, key=lambda r: r[1]): print(f"  {r[0]:45s} ord={r[1]:5d} title={r[2]:3d} desc={r[3]:3d}")

HTACCESS = r"""# telefonabonnementer.dk – Apache/LiteSpeed (Simply.com)
Options -Indexes
DirectoryIndex index.html
ErrorDocument 404 /404.html
AddDefaultCharset UTF-8
AddType image/webp .webp
AddType application/manifest+json .webmanifest

<IfModule mod_rewrite.c>
RewriteEngine On
# HTTPS + uden www
RewriteCond %{HTTPS} off [OR]
RewriteCond %{HTTP_HOST} ^www\. [NC]
RewriteRule ^(.*)$ https://telefonabonnementer.dk/$1 [R=301,L]
# Affiliate-redirects (/go/udbyder/) – før trailing-slash-reglen
#GO_RULES#
# Bloker kildekode
RewriteRule ^_build(/|$) - [F,L]
RewriteRule ^\.github(/|$) - [F,L]
RewriteRule ^README\.md$ - [F,L]
# Fjern index.html fra URL
RewriteCond %{THE_REQUEST} \s/+(.*/)?index\.html[\s?] [NC]
RewriteRule ^(.*/)?index\.html$ /%1 [R=301,L]
# Tilføj afsluttende skråstreg
RewriteCond %{REQUEST_FILENAME} !-f
RewriteCond %{REQUEST_URI} !(\.[a-z0-9]{2,5}|/)$ [NC]
RewriteRule ^(.*)$ /$1/ [R=301,L]
</IfModule>
<FilesMatch "\.(md|py|yml|txt\.bak)$">
Require all denied
</FilesMatch>

<IfModule mod_headers.c>
Header always set X-Content-Type-Options "nosniff"
Header always set Referrer-Policy "strict-origin-when-cross-origin"
Header always set X-Frame-Options "SAMEORIGIN"
Header always set Permissions-Policy "camera=(), microphone=(), geolocation=()"
Header always set Strict-Transport-Security "max-age=31536000; includeSubDomains"
<FilesMatch "\.(js|css)$">
Header set Cache-Control "public, max-age=31536000, immutable"
</FilesMatch>
<FilesMatch "\.(webp|png|jpg|ico|svg|webmanifest)$">
Header set Cache-Control "public, max-age=2592000"
</FilesMatch>
<FilesMatch "\.(html|xml|txt)$">
Header set Cache-Control "public, max-age=600, must-revalidate"
</FilesMatch>
</IfModule>

<IfModule mod_deflate.c>
AddOutputFilterByType DEFLATE text/html text/css application/javascript application/json image/svg+xml text/xml application/xml text/plain application/manifest+json
</IfModule>
"""

if __name__ == "__main__":
    main()
