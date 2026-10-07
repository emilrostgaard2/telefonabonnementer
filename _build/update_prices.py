#!/usr/bin/env python3
"""Henter Adtraction-sammenligningsfeedet (mobilabonnementer) og opdaterer
data/plans.json + affiliate-links/net i data/providers.json.

Kilde (i prioriteret rækkefølge):
  1. Miljøvariabel FEED_URL  (GitHub-secret med feed-URL'en fra Adtraction)
  2. Lokal fil _build/data/adtraction-feed.json

Kør:  python3 _build/update_prices.py
Udbydere der ikke findes i providers.json (fx CBB, eesy) springes over.
"""
import json, os, re, sys, datetime, urllib.request

B = os.path.dirname(os.path.abspath(__file__))
PLANS = f"{B}/data/plans.json"
PROVS = f"{B}/data/providers.json"
LOCAL = f"{B}/data/adtraction-feed.json"

UNIT_MAP = {"lebara": "lebara", "lyca mobile": "lyca", "lycamobile": "lyca", "oister": "oister", "yousee": "yousee",
            "flexii": "flexii", "greentel": "greentel", "duka": "duka", "telmore": "telmore", "cbb": "cbb", "eesy": "eesy"}
ABBR = {"lebara": "lb", "lyca": "ly", "oister": "oi", "yousee": "ys", "flexii": "fx", "greentel": "gt", "duka": "dk", "telmore": "tm", "cbb": "cb", "eesy": "ee"}
NET = {"tdc": "TDC NET", "3": "3 (Hi3G)", "telenor": "TT-netværket (Telenor/Norlys)", "norlys/telenor": "TT-netværket (Telenor/Norlys)", "norlys": "TT-netværket (Norlys/Telenor)"}

def load_feed():
    url = os.environ.get("FEED_URL", "").strip()
    if url:
        req = urllib.request.Request(url, headers={"User-Agent": "telefonabonnementer.dk feed-sync"})
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = r.read().decode("utf-8", "replace")
        data = json.loads(raw)
        with open(LOCAL, "w", encoding="utf-8") as f: f.write(raw)  # gem seneste kopi
        print(f"Feed hentet fra FEED_URL ({len(data.get('units', []))} abonnementer)")
        return data
    if os.path.exists(LOCAL):
        data = json.load(open(LOCAL, encoding="utf-8"))
        print(f"Bruger lokal feed-fil ({len(data.get('units', []))} abonnementer)")
        return data
    return None

def usp(u): return " ".join(str(u.get(k, "")) for k in ("usp1", "usp2", "usp3"))

def has_5g(u):
    if "5g" in u: return bool(u["5g"])
    t = usp(u).lower()
    return "5g" in t and "4g" not in t

DMY = re.compile(r"(\d{1,2})\.(\d{1,2})\.(\d{4})")
def parse_ends(txt):
    m = DMY.search(txt or "")
    if not m: return None
    d, mth, y = map(int, m.groups())
    try: return datetime.date(y, mth, d).isoformat()
    except ValueError: return None

def intro_text(u, price):
    promo = (u.get("promotionText") or "").strip()
    disc = u.get("discountPrice")
    if disc is None or disc >= price: return None, None
    if disc == 0 and "gratis" not in promo.lower(): return None, None
    low = promo.lower()
    head = "Gratis" if disc == 0 else f"{disc} kr./md."
    end = parse_ends(promo)
    if end:
        d = datetime.date.fromisoformat(end); return disc, f"{head} til {d.day}.{d.month}.{d.year}"
    if re.search(r"første\s+år", low): return disc, f"{head} første år"
    if re.search(r"første\s+(md|måned)\b", low) or re.search(r"første md\.", low): return disc, f"{disc} kr. første måned"
    m = re.search(r"(\d+)\s*(mdr|måneder|md)", low)
    if m: return disc, f"{head} i {m.group(1)} mdr."
    return disc, f"{head} i en periode"

def build_plan(u, prov):
    fri_data = bool(u.get("unlimitedDataDK"))
    gb = None if fri_data else u.get("dataDK")
    if gb is not None: gb = int(gb) if float(gb).is_integer() else gb
    fri_tale = bool(u.get("unlimitedHoursDK"))
    talk = "fri" if fri_tale else f'{u.get("hoursIncludedDK", 0)} t'
    eu = u.get("dataEU")
    eu = None if not eu or eu < 1 else (int(eu) if float(eu).is_integer() else eu)
    price = int(round(u["monthlyPrice"]))
    g5 = has_5g(u)
    disc, itxt = intro_text(u, price)
    gbt = "fri data" if gb is None else f"{gb} GB"
    stream = bool(u.get("streaming"))
    if stream:
        m = re.search(r"(\d+)\s+(valgfrie\s+)?streaming", usp(u), re.I)
        mix = "CBB Mix" in usp(u)
        name = f"Fri tale + {gbt} + " + (f"{m.group(1)} streamingtjenester" if m else ("streaming (CBB Mix)" if mix else "streaming"))
    elif fri_tale:
        name = f"Fri tale + {gbt}"
    else:
        h = u.get("hoursIncludedDK", 0)
        name = f"{gbt} + {h} {'time' if h == 1 else 'timer'}"
    if prov == "flexii": name += " (5G)" if g5 else " (4G)"
    p = {"p": prov, "name": name, "price": price, "gb": gb, "eu": eu, "talk": talk, "g5": g5, "feed_id": str(u.get("uniqueId"))}
    if disc is not None:
        p["intro"] = disc; p["intro_txt"] = itxt
        e = parse_ends(u.get("promotionText"))
        if e: p["ends"] = e
    extras = [x for x in (u.get("usp1"), u.get("usp2"), u.get("usp3")) if x and re.search(r"^ring |timer til|world|usa", x, re.I)]
    if extras: p["extra"] = extras[0]
    if (u.get("promotionText") or "").lower() == "dobbelt data": p["extra"] = "Dobbelt data"
    if u.get("hoursIncludedEU") and not u.get("unlimitedHoursEU") and not fri_tale: pass
    # tags
    t = set()
    if fri_tale: t.add("fri-tale")
    if gb is None: t.add("fri-data")
    if gb is None or gb >= 100: t.add("store-data")
    if price <= 59: t.add("billig")
    if not fri_tale and (gb or 0) <= 12: t.add("kun-tale")
    if (gb or 999) <= 15 and price <= 70: t.add("senior")
    if ((gb or 999) <= 12 and price <= 69) or "yngste" in (u.get("promotionText") or "").lower(): t.add("boern")
    if fri_tale and gb is not None and 40 <= gb <= 200 and price <= 120: t.add("unge")
    if (eu or 0) >= 30 or p.get("extra"): t.add("udland")
    if disc is not None: t.add("tilbud")
    if stream or u.get("music"): t.add("streaming") if stream else None
    if prov == "lyca": t.add("forudbetalt")
    p["tags"] = sorted(t)
    return p

def main():
    feed = load_feed()
    if not feed:
        print("Intet feed – springer over."); return 0
    plans_doc = json.load(open(PLANS, encoding="utf-8"))
    provs = json.load(open(PROVS, encoding="utf-8"))
    old = plans_doc["plans"]
    new, seen_key, links, nets = [], {}, {}, {}
    for u in feed.get("units", []):
        prov = UNIT_MAP.get(u.get("unitName", "").strip().lower())
        if not prov or prov not in provs: continue
        try: p = build_plan(u, prov)
        except Exception as e:
            print("  sprang over:", u.get("uniqueId"), e); continue
        key = (prov, p["gb"], p["talk"], p["g5"], p["price"], p["name"])
        if key in seen_key:  # dublet i feedet – behold den med mest EU-data
            if (p["eu"] or 0) > (seen_key[key]["eu"] or 0): seen_key[key].update(p)
            continue
        seen_key[key] = p; new.append(p)
        base = re.sub(r"&url=.*$", "", u.get("trackingURL", ""))
        if base: links.setdefault(prov, base)
        n = NET.get((u.get("operatorNetwork") or "").strip().lower())
        if n: nets.setdefault(prov, n)
    if len(new) < 15:
        print(f"ADVARSEL: kun {len(new)} abonnementer i feedet – beholder eksisterende data."); return 0
    # genbrug stabile id'er
    used = set()
    def match(p):
        for o in old:
            if o["id"] in used or o["p"] != p["p"]: continue
            if o["gb"] == p["gb"] and (o["talk"] == "fri") == (p["talk"] == "fri") and o["g5"] == p["g5"] and ("streaming" in o.get("tags", [])) == ("streaming" in p["tags"]):
                return o
        return None
    for p in new:
        o = match(p)
        if o:
            p["id"] = o["id"]
        else:
            base = f'{ABBR[p["p"]]}-{p["gb"] if p["gb"] is not None else "fri"}' + ("" if p["g5"] or p["p"] != "flexii" else "-4g")
            i, cand = 2, base
            while cand in used or any(x.get("id") == cand for x in new if x is not p): cand = f"{base}-{i}"; i += 1
            p["id"] = cand
        used.add(p["id"])
    # rapport
    oldm = {o["id"]: o for o in old}
    for p in new:
        o = oldm.get(p["id"])
        if not o: print(f"  NY: {p['id']} {p['name']} {p['price']} kr.")
        elif o["price"] != p["price"] or o.get("intro") != p.get("intro"):
            print(f"  ÆNDRET: {p['id']} {o['price']}→{p['price']} kr. intro {o.get('intro')}→{p.get('intro')}")
    gone = [o["id"] for o in old if o["id"] not in used and o["p"] in links]
    if gone: print("  FJERNET (ikke længere i feed):", ", ".join(gone))
    # behold manuelle abonnementer for udbydere der ikke er i feedet
    keep = [o for o in old if o["p"] not in links]
    plans_doc["plans"] = keep + new
    lu = (feed.get("lastUpdated") or "")[:10]
    plans_doc["checked"] = lu if re.match(r"\d{4}-\d\d-\d\d", lu) else datetime.date.today().isoformat()
    plans_doc["_note"] = "Genereret automatisk fra Adtraction-feedet af update_prices.py. Ret ikke manuelt for udbydere i feedet."
    json.dump(plans_doc, open(PLANS, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for k, url in links.items():
        if not provs[k].get("url_locked"):
            provs[k]["url"] = url; provs[k]["verify"] = False; provs[k].pop("noaffiliate", None)
    for k, n in nets.items(): provs[k]["network"] = n
    json.dump(provs, open(PROVS, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{len(new)} abonnementer fra feedet · priser tjekket {plans_doc['checked']}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
