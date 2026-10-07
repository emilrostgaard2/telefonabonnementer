#!/usr/bin/env python3
"""Opdaterer priser i data/plans.json fra Adtraction-produktfeeds.

Brug:
  python3 _build/update_prices.py --list      # vis alle produkter i feeds (til at lave mapping)
  python3 _build/update_prices.py             # opdater priser og skriv plans.json

Opsætning: _build/data/feeds.json
{
  "feeds": {"telmore": "https://adtraction.com/productfeed.htm?...", "duka": "..."},
  "map": {"tm-45": {"sku": "ABC123"}, "dk-30": {"name": ["30 GB", "fri tale"]}}
}
- "sku": matcher feedets SKU/ID præcist.
- "name": alle ord skal indgå i produktnavnet (store/små bogstaver ignoreres).
Feed-URL'er kan også gives som miljøvariabel FEEDS_JSON (GitHub-secret) med samme JSON.
"""
import json, os, sys, csv, io, re, datetime, urllib.request
import xml.etree.ElementTree as ET

B = os.path.dirname(os.path.abspath(__file__))
PLANS = f"{B}/data/plans.json"
CFG = f"{B}/data/feeds.json"

def load_cfg():
    if os.environ.get("FEEDS_JSON"):
        return json.loads(os.environ["FEEDS_JSON"])
    if os.path.exists(CFG):
        return json.load(open(CFG, encoding="utf-8"))
    return {"feeds": {}, "map": {}}

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "telefonabonnementer.dk price-sync"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8", "replace")

def num(s):
    s = str(s or "").replace("DKK", "").replace("kr", "").strip()
    s = s.replace(".", "").replace(",", ".") if re.search(r",\d{1,2}$", s) else s.replace(",", "")
    try: return round(float(re.sub(r"[^\d.]", "", s)))
    except ValueError: return None

def parse(text):
    """Returnerer liste af dicts med sku, name, price, url. Understøtter XML og CSV/TSV."""
    items = []
    t = text.lstrip()
    if t.startswith("<"):
        root = ET.fromstring(t)
        for el in root.iter():
            kids = {c.tag.split("}")[-1].lower(): (c.text or "").strip() for c in el}
            if not kids or not any(k in kids for k in ("name", "productname", "title")): continue
            items.append({"sku": kids.get("sku") or kids.get("id") or kids.get("productid") or "",
                          "name": kids.get("name") or kids.get("productname") or kids.get("title") or "",
                          "price": num(kids.get("price") or kids.get("saleprice") or kids.get("currentprice")),
                          "url": kids.get("trackingurl") or kids.get("producturl") or kids.get("url") or ""})
    else:
        dialect = "excel-tab" if t.split("\n", 1)[0].count("\t") > t.split("\n", 1)[0].count(",") else "excel"
        for row in csv.DictReader(io.StringIO(t), dialect=dialect):
            r = {k.lower().strip(): (v or "").strip() for k, v in row.items() if k}
            items.append({"sku": r.get("sku") or r.get("id") or "", "name": r.get("name") or r.get("productname") or r.get("title") or "",
                          "price": num(r.get("price") or r.get("saleprice")), "url": r.get("trackingurl") or r.get("producturl") or ""})
    return [i for i in items if i["name"] and i["price"]]

def main():
    cfg = load_cfg()
    if not cfg.get("feeds"):
        print("Ingen feeds konfigureret – springer prisopdatering over."); return 0
    data = json.load(open(PLANS, encoding="utf-8"))
    by_prov = {}
    for prov, url in cfg["feeds"].items():
        try:
            by_prov[prov] = parse(fetch(url)); print(f"{prov}: {len(by_prov[prov])} produkter")
        except Exception as e:
            print(f"ADVARSEL: kunne ikke hente feed for {prov}: {e}")
    if "--list" in sys.argv:
        for prov, items in by_prov.items():
            print(f"\n== {prov} ==")
            for i in items: print(f"  sku={i['sku']!r:20} pris={i['price']:>5}  {i['name']}")
        return 0
    changed = matched = 0
    for p in data["plans"]:
        rule = cfg.get("map", {}).get(p["id"])
        if not rule or p["p"] not in by_prov: continue
        hit = None
        for it in by_prov[p["p"]]:
            if rule.get("sku") and it["sku"] == rule["sku"]: hit = it; break
            if rule.get("name") and all(w.lower() in it["name"].lower() for w in rule["name"]): hit = it; break
        if not hit:
            print(f"  ikke fundet i feed: {p['id']}"); continue
        matched += 1
        if hit["price"] != p["price"] and 5 <= hit["price"] <= 1500:
            print(f"  {p['id']}: {p['price']} -> {hit['price']} kr.")
            p["price"] = hit["price"]; changed += 1
    if matched:
        data["checked"] = datetime.date.today().isoformat()
        json.dump(data, open(PLANS, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{changed} priser opdateret")
    return 0

if __name__ == "__main__":
    sys.exit(main())
