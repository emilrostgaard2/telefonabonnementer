# telefonabonnementer.dk

Statisk, lynhurtig hjemmeside (ingen WordPress, ingen database). Alt indhold ligger i `_build/`, og den færdige side ligger i roden af repoet.

## Kom online på Simply – via GitHub (anbefalet)

1. Opret et nyt **privat** repo på GitHub og upload hele indholdet af zip-filen (inkl. de skjulte mapper `.github` og filen `.htaccess`).
2. Gå til repoet → **Settings → Secrets and variables → Actions → New repository secret** og opret:
   | Secret | Værdi |
   |---|---|
   | `FTP_SERVER` | FTP-server fra din Simply-velkomstmail / kontrolpanel (fx `linuxXX.unoeuro.com`) |
   | `FTP_USERNAME` | FTP-brugernavn (typisk `telefonabonnementer.dk`) |
   | `FTP_PASSWORD` | FTP-adgangskode |
   | `FTP_DIR` | *(valgfri)* mappen sitet skal ligge i. Standard er `public_html/` |
3. Gå til **Actions → "Byg og deploy til Simply" → Run workflow**. Herefter deployer den automatisk ved hvert push **og hver nat** (så datoer og "opdateret"-stempler altid er friske).
4. Tilmeld domænet i **Google Search Console** og indsend `https://telefonabonnementer.dk/sitemap.xml`.

**Uden GitHub:** Upload alt *undtagen* `_build/`, `.github/` og `README.md` til `public_html` via Simplys filhåndtering eller FTP. Det virker med det samme.

## Affiliate-links
Alle "Se tilbud"-knapper går via `/go/<udbyder>/` (styres af `.htaccess` + fallback-side). Linkene ændres ét sted: `_build/data/providers.json` → `"url"`.

⚠️ **Tjek disse 4** – jeg kunne ikke se, hvilket brand de ukendte Adtraction-links hører til, så de er gættet (markeret `"verify": true`):
- Lebara → `go.adt228.com … a=1873806342`
- Flexii → `go.adt256.com … a=1751759538`
- Oister → `go.adt256.com … a=1667317668`
- Greentel → `go.adt284.net … a=1666103641`
- YouSee har intet affiliate-link (linker direkte, `nofollow`).

Klik selv på hvert link (eller se i Adtraction under *Programmer → Links*), ret i `providers.json` og push.

## Automatisk opdatering af priser (Adtraction-feed)
1. Log ind på Adtraction → **Annoncører/Programmer** → vælg programmet (fx Telmore) → fanen **Produktfeed** (hedder også *Product feeds* under *Værktøjer*). Vælg din kanal (telefonabonnementer.dk) og format XML eller CSV, og kopiér feed-URL'en. Bemærk: ikke alle teleselskaber udbyder feeds – findes fanen ikke, så spørg din kontaktperson i Adtraction.
2. Kør lokalt for at se produkterne: lav `_build/data/feeds.json` med `{"feeds": {"telmore": "FEED-URL"}, "map": {}}` og kør `python3 _build/update_prices.py --list`.
3. Udfyld `"map"` (abonnements-id fra `plans.json` → `{"sku": "..."}` eller `{"name": ["45 GB", "fri tale"]}`).
4. Læg hele JSON'en som GitHub-secret `FEEDS_JSON` (så feed-URL'erne ikke ligger i repoet). Workflowet opdaterer så priserne hver nat og bygger sitet igen.

## Redigér indhold
- Tekster: `_build/content/*.txt` (front matter + HTML + `===FAQ===` + `===KILDER===`). Se `_build/SPEC.md`.
- Priser/abonnementer: `_build/data/plans.json` · Udbydere, karakterer, fordele/ulemper: `_build/data/providers.json`.
- Byg lokalt: `python3 _build/build.py` og tjek med `python3 _build/qa.py` (kræver Python 3 + Pillow).
- Placeholders i titler/tekst: `{maaned}` (fx "oktober 2026"), `{aar}`, `{fra:fri-data}` (laveste pris i kategori).

## Ting du bør verificere/udskifte løbende (E-E-A-T)
- Bio på `/forfatter/emil-rostgaard-clausen/` er formuleret generelt – tilføj gerne konkret erfaring, uddannelse og flere profiler (sameAs i `build.py → person()`).
- Kontakt-mail er `kontakt@forsikringspakken.dk` som angivet – overvej en `@telefonabonnementer.dk`-adresse.
- Lyca Mobiles net: kilderne er uenige (Mobilsiden 2026: TDC NET; én prisoversigt: TT-netværket).
- Lebara- og Lyca-priser er hentet via mobilabonnementer.dk (deres egne sider viste ikke priserne ved tjek).
