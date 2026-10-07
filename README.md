# telefonabonnementer.dk

Statisk, lynhurtig hjemmeside (ingen WordPress, ingen database). Alt indhold og al kode ligger i `_build/` – GitHub bygger det færdige site og lægger det på Simply.

## Sådan virker det
GitHub bygger sitet ud fra `_build/` og uploader det færdige site (mappen `public/`) til Simply via FTP – ved hvert push og hver nat. Om natten hentes nye priser fra Adtraction-feedet først, så tabeller, priser i teksten, kampagner og "billigst"-anbefalinger altid er aktuelle.

## Opsætning (én gang)
1. Upload mappen `_build` og filen `.github/workflows/deploy.yml` til repoet `emilrostgaard2/telefonabonnementer`.
2. Opret secrets under **Settings → Secrets and variables → Actions**:
   | Secret | Værdi |
   |---|---|
   | `FTP_SERVER` | FTP-server fra Simply |
   | `FTP_USERNAME` | FTP-brugernavn |
   | `FTP_PASSWORD` | FTP-adgangskode |
   | `FEED_URL` | URL'en til Adtraction-feedet (JSON) |
   | `FTP_DIR` | *(valgfri)* standard er `public_html/` |
3. **Actions → Byg og deploy til Simply → Run workflow.**
4. Indsend `https://telefonabonnementer.dk/sitemap.xml` i Google Search Console.

## Priser og affiliate-links
- Alle abonnementer, priser, kampagner, EU-data, 5G, net **og affiliate-links** kommer fra Adtraction-feedet (`update_prices.py`). Uden `FEED_URL` bruges den gemte kopi `_build/data/adtraction-feed.json`.
- Udbydere i feedet, som sitet ikke har en side for endnu (CBB, eesy), springes over. De kan tilføjes i `providers.json` + logo i `_build/assets/img/logos/`.
- I teksterne bruges pladsholdere som `{pris:lb-70}`, `{introtekst:tm-50}`, `{gb:dk-1000}`, `{fra:fri-data}` og `{antal}`, så brødteksten også opdateres automatisk. Fjerner en udbyder et abonnement fra feedet, melder `qa.py` fejl på den side, så du ser det i GitHub Actions.

## Redigér indhold
- Tekster: `_build/content/*.txt` (front matter + HTML + `===FAQ===` + `===KILDER===`). Se `_build/SPEC.md`.
- Priser/abonnementer: `_build/data/plans.json` · Udbydere, karakterer, fordele/ulemper: `_build/data/providers.json`.
- Byg lokalt: `python3 _build/update_prices.py && python3 _build/build.py && python3 _build/qa.py` (kræver Python 3 + Pillow). Resultatet ligger i `public/`.
- Placeholders i titler/tekst: `{maaned}` (fx "oktober 2026"), `{aar}`, `{fra:fri-data}` (laveste pris i kategori).

## Ting du bør verificere/udskifte løbende (E-E-A-T)
- Bio på `/forfatter/emil-rostgaard-clausen/` er formuleret generelt – tilføj gerne konkret erfaring og flere profiler (sameAs i `build.py → person()`).
- Kontakt-mail er `kontakt@forsikringspakken.dk` – overvej en `@telefonabonnementer.dk`-adresse.
